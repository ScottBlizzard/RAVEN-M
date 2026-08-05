"""Frozen v0.2 arm registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    system: str
    tier: str
    lane: str
    source_repo: str
    source_commit: str
    checkpoint_id: str
    checkpoint_revision: str
    reproduction_label: str
    stages: tuple[str, ...]
    observation_privileges: tuple[str, ...]
    external_family: str | None

    @property
    def pixel_only(self) -> bool:
        return "ui_tree" not in self.observation_privileges and "ui_elements" not in self.observation_privileges


QWEN_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
RAVEN_COMMIT = "08b21d06db165d1fb6908c457f955988061b10ca"


def _arm(arm_id: str, system: str, tier: str, lane: str, repo: str,
         commit: str, checkpoint: str, revision: str, label: str,
         stages: tuple[str, ...], privileges: tuple[str, ...],
         family: str | None) -> ArmSpec:
    return ArmSpec(arm_id, system, tier, lane, repo, commit, checkpoint,
                   revision, label, stages, privileges, family)


ARM_REGISTRY: dict[str, ArmSpec] = {
    arm.arm_id: arm for arm in (
        _arm("CB-PX-B3", "RAVEN-B3", "A", "CB-PX", "https://github.com/ScottBlizzard/RAVEN-M", RAVEN_COMMIT, "Qwen/Qwen3-VL-32B-Instruct", QWEN_REVISION, "COMMON_BACKBONE_ADAPTER_COMPARISON", ("S1", "S2", "S3"), ("screenshot",), None),
        _arm("CB-PX-M0", "RAVEN-M0", "A", "CB-PX", "https://github.com/ScottBlizzard/RAVEN-M", RAVEN_COMMIT, "Qwen/Qwen3-VL-32B-Instruct", QWEN_REVISION, "COMMON_BACKBONE_ADAPTER_COMPARISON", ("S1", "S2", "S3"), ("screenshot",), None),
        _arm("NS-PX-GO15", "GUI-Owl-1.5", "A", "NS-PX-XP", "https://github.com/X-PLUG/MobileAgent", "11cea575561fb7800b5fb6b6cafa56f7a91de11f", "mPLUG/GUI-Owl-1.5-8B-Think", "afe3707fc84caebc4d7046118b34493ecf8bb060", "CONFIGURATION_EQUIVALENT_REPRODUCTION", ("S1", "S2", "S3"), ("screenshot",), "XPLUG_GUIOWL8"),
        _arm("NS-PX-MA35", "Mobile-Agent-v3.5", "A", "NS-PX-XP", "https://github.com/X-PLUG/MobileAgent", "11cea575561fb7800b5fb6b6cafa56f7a91de11f", "mPLUG/GUI-Owl-1.5-8B-Think", "afe3707fc84caebc4d7046118b34493ecf8bb060", "CONFIGURATION_EQUIVALENT_REPRODUCTION", ("S1", "S2", "S3"), ("screenshot",), "XPLUG_GUIOWL8"),
        _arm("NS-PX-SCUA32", "ScaleCUA-32B", "A", "NS-PX", "https://github.com/OpenGVLab/ScaleCUA", "5d92feea9f1e14b8303ce37da45b286fb1f4d3aa", "OpenGVLab/ScaleCUA-32B", "9a91c80690b34f2a962203c5ed896ef845b6149c", "CONFIGURATION_EQUIVALENT_REPRODUCTION", ("S1", "S2", "S3"), ("screenshot",), "SCALECUA32"),
        _arm("NS-PX-UIV4", "UI-Voyager", "A", "NS-PX", "https://github.com/ui-voyager/UI-Voyager", "67b65e2be093753ecaa2964f48739339b870813e", "MarsXL/UI-Voyager", "c262b85f18f1c669b19bca544e0ee2eb71225ff3", "CONFIGURATION_EQUIVALENT_REPRODUCTION", ("S1", "S2", "S3"), ("screenshot",), "UIVOYAGER4"),
        _arm("CB-PX-B0", "RAVEN-B0", "B", "CB-PX", "https://github.com/ScottBlizzard/RAVEN-M", RAVEN_COMMIT, "Qwen/Qwen3-VL-32B-Instruct", QWEN_REVISION, "COMMON_BACKBONE_ADAPTER_COMPARISON", ("S1", "S2"), ("screenshot",), None),
        _arm("CB-ST-M3A", "AndroidWorld-M3A-Qwen", "B", "CB-ST", "https://github.com/google-research/android_world", "3e50888527ef9f29b9157ecd537e408008bb1c85", "Qwen/Qwen3-VL-32B-Instruct", QWEN_REVISION, "COMMON_BACKBONE_ADAPTER_COMPARISON", ("S1", "S2"), ("screenshot", "ui_elements"), "ANDROIDWORLD_M3A"),
        _arm("CB-PX-MU", "MobileUse-MultiAgent-Qwen", "B", "CB-PX", "https://github.com/MadeAgents/mobile-use", "babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347", "Qwen/Qwen3-VL-32B-Instruct", QWEN_REVISION, "COMMON_BACKBONE_ADAPTER_COMPARISON", ("S1", "S2"), ("screenshot",), "MOBILEUSE"),
    )
}


def get_arm(arm_id: str) -> ArmSpec:
    try:
        return ARM_REGISTRY[arm_id]
    except KeyError as exc:
        raise ValueError(f"Arm is not in frozen v0.2 registry: {arm_id}") from exc


def external_families(arm_ids: set[str]) -> set[str]:
    return {spec.external_family for arm_id, spec in ARM_REGISTRY.items()
            if arm_id in arm_ids and spec.external_family is not None}
