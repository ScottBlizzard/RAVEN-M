"""Explicit-port, fail-closed AndroidEnv loader for B2.8 only."""

from __future__ import annotations

from typing import Any

from android_env import loader
from android_env.components import config_classes
from android_env.wrappers import a11y_grpc_wrapper
from android_world.env import android_world_controller, interface


class FailClosedA11yController(android_world_controller.AndroidWorldController):
    """Forbid AndroidWorld's implicit refresh, which loses the 5038 setting."""

    def refresh_env(self) -> None:
        raise RuntimeError("IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN")

    def get_a11y_forest(self):  # type annotation follows the pinned upstream API
        return self._get_a11y_forest()  # noqa: SLF001


def load_explicit_sidecar_env(
    *, adb_path: str, adb_server_port: int, console_port: int, grpc_port: int
) -> interface.AsyncAndroidEnv:
    if adb_server_port != 5038:
        raise ValueError("ADB_PORT_NOT_FROZEN_5038")
    launcher = config_classes.EmulatorLauncherConfig(
        emulator_console_port=console_port,
        adb_port=console_port + 1,
        grpc_port=grpc_port,
    )
    if hasattr(launcher, "connect_to_existing"):
        setattr(launcher, "connect_to_existing", True)
    config = config_classes.AndroidEnvConfig(
        task=config_classes.FilesystemTaskConfig(
            path=android_world_controller._write_default_task_proto(),  # noqa: SLF001
        ),
        simulator=config_classes.EmulatorConfig(
            emulator_launcher=launcher,
            adb_controller=config_classes.AdbControllerConfig(
                adb_path=adb_path,
                adb_server_port=adb_server_port,
            ),
        ),
    )
    instance = loader.load(config)
    controller = FailClosedA11yController(instance, install_a11y_forwarding_app=False)
    return interface.AsyncAndroidEnv(controller)


def locate_sidecar_wrapper(env: interface.AsyncAndroidEnv) -> a11y_grpc_wrapper.A11yGrpcWrapper:
    current: Any = env.controller.env
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, a11y_grpc_wrapper.A11yGrpcWrapper):
            return current
        current = getattr(current, "_env", None)
    raise RuntimeError("A11Y_SIDECAR_WRAPPER_MISSING")


def sidecar_runtime_identity(env: interface.AsyncAndroidEnv) -> dict[str, Any]:
    wrapper = locate_sidecar_wrapper(env)
    return {
        "sidecar_host_port": int(wrapper.get_port()),
        "sidecar_wrapper_id": id(wrapper),
        "sidecar_wrapper_class": f"{type(wrapper).__module__}.{type(wrapper).__qualname__}",
        "controller_class": f"{type(env.controller).__module__}.{type(env.controller).__qualname__}",
    }
