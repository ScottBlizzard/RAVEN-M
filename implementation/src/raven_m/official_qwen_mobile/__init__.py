"""Faithful adapter for Qwen3-VL's published Mobile Agent recipe."""

from .protocol import (
    OFFICIAL_QWEN_COMMIT,
    OFFICIAL_SYSTEM_PROMPT,
    SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT,
    TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT,
    OfficialMobileDecision,
    OfficialProtocolError,
    build_user_prompt,
    parse_official_response,
)
from .a10_obligation_branch_frontier import (
    EvidenceCalibratedObligationBranchFrontierMemory,
)

__all__ = [
    "OFFICIAL_QWEN_COMMIT",
    "OFFICIAL_SYSTEM_PROMPT",
    "SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT",
    "TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT",
    "OfficialMobileDecision",
    "OfficialProtocolError",
    "build_user_prompt",
    "parse_official_response",
    "EvidenceCalibratedObligationBranchFrontierMemory",
    "EvidenceMaturedObligationBranchFrontierMemory",
    "ConfirmedRouteContractionECOBFMemory",
    "MinimalActionDivergenceMemory",
]


def __getattr__(name: str):
    """Lazily expose prospective memories without coupling their modules."""
    if name == "EvidenceMaturedObligationBranchFrontierMemory":
        from .a10_v2_obligation_branch_frontier import (
            EvidenceMaturedObligationBranchFrontierMemory,
        )

        return EvidenceMaturedObligationBranchFrontierMemory
    if name == "ConfirmedRouteContractionECOBFMemory":
        from .a11_confirmed_route_contraction import (
            ConfirmedRouteContractionECOBFMemory,
        )

        return ConfirmedRouteContractionECOBFMemory
    if name == "MinimalActionDivergenceMemory":
        from .a12_minimal_action_divergence import MinimalActionDivergenceMemory

        return MinimalActionDivergenceMemory
    raise AttributeError(name)
