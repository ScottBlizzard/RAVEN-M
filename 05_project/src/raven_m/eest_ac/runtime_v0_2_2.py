"""Port-explicit AndroidWorld runtime loader for EEST-AC v0.2.2."""

from __future__ import annotations

from android_env import loader
from android_env.components import config_classes
from android_world.env import android_world_controller, env_launcher, interface


def assert_frozen_adb_server_port(*, configured: int, supplied: int) -> None:
    """Reject port drift; there is deliberately no runtime fallback."""
    if not isinstance(configured, int) or not 1 <= configured <= 65535:
        raise ValueError("Configured ADB server port is invalid.")
    if supplied != configured:
        raise RuntimeError(
            f"ADB_SERVER_PORT_DRIFT:configured={configured};supplied={supplied};fallback=forbidden"
        )


def load_and_setup_env(
    *,
    console_port: int,
    emulator_setup: bool,
    freeze_datetime: bool,
    adb_path: str,
    adb_server_port: int,
    grpc_port: int,
) -> interface.AsyncEnv:
    """Connect through exactly one explicit official-ADB server port."""
    if not isinstance(adb_server_port, int) or not 1 <= adb_server_port <= 65535:
        raise ValueError("adb_server_port must be an explicit TCP port.")
    emulator_launcher = config_classes.EmulatorLauncherConfig(
        emulator_console_port=console_port,
        adb_port=console_port + 1,
        grpc_port=grpc_port,
    )
    if hasattr(emulator_launcher, "connect_to_existing"):
        setattr(emulator_launcher, "connect_to_existing", True)
    config = config_classes.AndroidEnvConfig(
        task=config_classes.FilesystemTaskConfig(
            path=android_world_controller._write_default_task_proto(),  # noqa: SLF001
        ),
        simulator=config_classes.EmulatorConfig(
            emulator_launcher=emulator_launcher,
            adb_controller=config_classes.AdbControllerConfig(
                adb_path=adb_path,
                adb_server_port=adb_server_port,
            ),
        ),
    )
    instance = loader.load(config)
    controller = android_world_controller.AndroidWorldController(instance)
    env = interface.AsyncAndroidEnv(controller)
    env_launcher.setup_env(env, emulator_setup=emulator_setup, freeze_datetime=freeze_datetime)
    return env
