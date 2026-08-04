from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.command_output_v0_2_9 import (
    decode_command_stream,
    qualify_framework_service_check,
)


ROOT = Path(__file__).resolve().parents[2]
FROZEN_V028_STDOUT = b"Service package: found\r\n"


def qualify(stdout: bytes, *, stderr: bytes = b"", returncode: int | None = 0, timed_out: bool = False):
    return qualify_framework_service_check(
        expected_service="package",
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
    )


def test_exact_frozen_v028_bytes_pass_with_auditable_policy() -> None:
    result = qualify(FROZEN_V028_STDOUT)
    assert result["passed"]
    assert result["stdout"]["encoding"] == "utf-8"
    assert result["stdout"]["error_policy"] == "strict"
    assert result["stdout"]["raw_bytes"] == 24
    assert result["stdout"]["raw_sha256"] == "6646a4c4c5f32c1b42a810b8ccca7d503c94367ea9293d9d57c9c434d4194bba"


@pytest.mark.parametrize(
    "value",
    [
        b"service PACKAGE: FOUND\n",
        b"  SeRvIcE   PaCkAgE:   FoUnD  \r\n",
    ],
)
def test_case_and_whitespace_variants_pass_without_bytes_casefold(value: bytes) -> None:
    assert qualify(value)["passed"]


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b"found",
        b"Service package found",
        b"Service package: not found\n",
        b"Service activity: found\n",
        b"Service package: found\nextra",
        b"\x00Service package: found\n",
    ],
)
def test_empty_and_malformed_outputs_fail_closed(value: bytes) -> None:
    assert not qualify(value)["passed"]


def test_non_utf8_and_non_bytes_fail_closed_without_ambiguity() -> None:
    assert not qualify(b"Service package: found\xff")["passed"]
    assert not qualify(FROZEN_V028_STDOUT, stderr=b"\xff")["passed"]
    with pytest.raises(TypeError, match="COMMAND_STREAM_TYPE"):
        decode_command_stream("Service package: found", stream_name="stdout")  # type: ignore[arg-type]
    class BytesSubclass(bytes):
        pass
    with pytest.raises(TypeError, match="COMMAND_STREAM_TYPE"):
        decode_command_stream(BytesSubclass(FROZEN_V028_STDOUT), stream_name="stdout")


def test_nonzero_timeout_and_nonempty_stderr_fail_closed() -> None:
    assert not qualify(FROZEN_V028_STDOUT, returncode=1)["passed"]
    assert not qualify(FROZEN_V028_STDOUT, timed_out=True)["passed"]
    assert not qualify(FROZEN_V028_STDOUT, stderr=b"warning")["passed"]


def test_b29_runner_uses_normalizer_and_has_no_raw_stream_casefold() -> None:
    source = (ROOT / "scripts/diagnose_role_binding_timing_b2_9_androidenv_sidecar.py").read_text(
        encoding="utf-8"
    )
    assert "qualify_framework_service_check" in source
    assert "stdout.casefold" not in source
    assert source.count("env.get_state(") == 1
    assert "uiautomator" not in source.casefold()
    assert "requests.post" not in source.casefold()


def test_b29_config_is_independent_and_zero_generation() -> None:
    config = json.loads(
        (ROOT / "configs/role_binding_timing/phase_b2_9_androidenv_sidecar_diagnosis.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["protocol_version"].endswith("v0.2.9")
    assert config["generation_calls_authorized"] == 0
    assert config["held_out_eligible"] is False
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["fallback_to_5037"] is False
    assert config["command_output_policy"] == {"encoding": "utf-8", "errors": "strict"}
    assert "phase_b2_9" in config["output_root"]
