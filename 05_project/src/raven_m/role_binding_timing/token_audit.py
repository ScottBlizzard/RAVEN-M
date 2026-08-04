"""Locked-tokenizer matching for causal prompt blocks and transcripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class TokenAuditError(ValueError):
    """Raised when exact token matching cannot be certified."""


class TokenCounter(Protocol):
    def count_text(self, text: str) -> int: ...

    def count_messages(self, messages: list[dict[str, str]]) -> int: ...


@dataclass
class WhitespaceTokenCounter:
    """Small deterministic test double; never a live-token certificate."""

    def count_text(self, text: str) -> int:
        return len(text.split())

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        return sum(self.count_text(item["content"]) + 1 for item in messages)


class HuggingFaceChatTokenCounter:
    """Exact text counter for the frozen Qwen tokenizer/chat template."""

    def __init__(
        self,
        *,
        model: str,
        revision: str,
        cache_dir: Path,
        local_files_only: bool = False,
    ) -> None:
        from transformers import AutoTokenizer

        self.model = model
        self.revision = revision
        self.tokenizer = AutoTokenizer.from_pretrained(
            model,
            revision=revision,
            cache_dir=str(cache_dir),
            trust_remote_code=False,
            local_files_only=local_files_only,
        )

    def count_text(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        encoded = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
        )
        if hasattr(encoded, "get"):
            input_ids = encoded.get("input_ids")
            if input_ids is None:
                raise TokenAuditError("Chat template returned no input_ids.")
        else:
            input_ids = encoded
        if input_ids and isinstance(input_ids[0], list):
            if len(input_ids) != 1:
                raise TokenAuditError("Expected one tokenized conversation.")
            input_ids = input_ids[0]
        count = len(input_ids)
        if count <= len(messages):
            raise TokenAuditError(
                "Degenerate chat-template token count; container length was likely used."
            )
        return count


def build_exact_neutral_block(
    *,
    fact_block: str,
    counter: TokenCounter,
    forbidden: tuple[str, ...],
) -> str:
    """Build semantically inert text with exactly the fact block's token count."""

    target = counter.count_text(fact_block)
    # Mirror the fact block's JSON-like terminal boundary so exact block counts
    # remain exact when embedded between newlines in the chat template. The
    # bounded enumeration is deterministic and contains no task-derived text.
    suffixes = ('"}', '"}.', '"}\n', ' context"}', ' only"}', ' x"}')
    for repeats in range(target * 4 + 32):
        for suffix in suffixes:
            candidate = (
                'NEUTRAL_BLOCK={"calibration":"'
                + (" neutral" * repeats)
                + suffix
            )
            if counter.count_text(candidate) != target:
                continue
            folded = candidate.casefold()
            leaked = [
                value
                for value in forbidden
                if value and value.casefold() in folded
            ]
            if leaked:
                raise TokenAuditError(
                    f"Neutral block leaked task content: {leaked}"
                )
            return candidate
    raise TokenAuditError(
        f"Cannot exactly match a {target}-token fact block with safe filler."
    )


def assert_pair_token_match(
    *,
    early_call_1: list[dict[str, str]],
    early_call_2: list[dict[str, str]],
    late_call_1: list[dict[str, str]],
    late_call_2: list[dict[str, str]],
    counter: TokenCounter,
    tolerance: int = 0,
) -> dict[str, int]:
    counts = {
        "early_call_1": counter.count_messages(early_call_1),
        "early_call_2": counter.count_messages(early_call_2),
        "late_call_1": counter.count_messages(late_call_1),
        "late_call_2": counter.count_messages(late_call_2),
    }
    counts["early_total"] = counts["early_call_1"] + counts["early_call_2"]
    counts["late_total"] = counts["late_call_1"] + counts["late_call_2"]
    counts["absolute_total_difference"] = abs(
        counts["early_total"] - counts["late_total"]
    )
    if counts["absolute_total_difference"] > tolerance:
        raise TokenAuditError(f"Early/late token mismatch: {counts}")
    return counts
