"""Guest-reachable, explicit-port AndroidEnv sidecar runtime for B2.10 DEV only."""

from __future__ import annotations

from concurrent import futures
from typing import Any

import grpc
import portpicker

from android_env import loader
from android_env.components import config_classes
from android_env.proto import adb_pb2
from android_env.proto.a11y import a11y_pb2_grpc
from android_env.wrappers import a11y_grpc_wrapper
from android_world.env import android_world_controller, interface


FORWARDER_PACKAGE = "com.google.androidenv.accessibilityforwarder"
FORWARDER_COMPONENT = (
    "com.google.androidenv.accessibilityforwarder/"
    "com.google.androidenv.accessibilityforwarder.AccessibilityForwarder"
)
FORWARDER_RECEIVER = (
    "com.google.androidenv.accessibilityforwarder/"
    "com.google.androidenv.accessibilityforwarder.FlagsBroadcastReceiver"
)
SET_GRPC = "accessibility_forwarder.intent.action.SET_GRPC"
ENABLE_GRPC = "accessibility_forwarder.intent.action.ENABLE_GRPC"
ENABLE_TREE = "accessibility_forwarder.intent.action.ENABLE_ACCESSIBILITY_TREE_LOGS"


def explicit_forwarder_broadcast_args(port: int) -> tuple[tuple[str, ...], ...]:
    """Return argv-safe, explicit-component lifecycle broadcasts."""
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError(f"INVALID_SIDECAR_PORT:{port!r}")
    return (
        (
            "shell", "am", "broadcast", "-a", SET_GRPC,
            "--ei", "port", str(port), "-n", FORWARDER_RECEIVER,
        ),
        ("shell", "am", "broadcast", "-a", ENABLE_GRPC, "-n", FORWARDER_RECEIVER),
        ("shell", "am", "broadcast", "-a", ENABLE_TREE, "-n", FORWARDER_RECEIVER),
    )


def parse_accessibility_service_state(raw: str, component: str = FORWARDER_COMPONENT) -> dict[str, bool]:
    """Parse only the service-membership summary lines from dumpsys accessibility."""
    fields = {
        "enabled": "Enabled services:",
        "binding": "Binding services:",
        "bound": "Bound services:",
        "crashed": "Crashed services:",
    }
    result: dict[str, bool] = {}
    for name, prefix in fields.items():
        matching = [line.strip() for line in raw.splitlines() if line.strip().startswith(prefix)]
        result[name] = len(matching) == 1 and component in matching[0]
    result["qualified_bound"] = result["enabled"] and result["bound"] and not result["crashed"]
    return result


def lifecycle_identity_issues(
    *, before: dict[str, Any], after: dict[str, Any], expected_adb_pid: int,
    expected_emulator_grpc_pid: int, expected_forwarder_pid: str,
) -> list[str]:
    issues: list[str] = []
    for label, record in (("before", before), ("after", after)):
        if record.get("adb_pid") != expected_adb_pid:
            issues.append(f"{label}:ADB_PID")
        if record.get("emulator_grpc_pid") != expected_emulator_grpc_pid:
            issues.append(f"{label}:EMULATOR_GRPC_PID")
        if record.get("forwarder_pid") != expected_forwarder_pid:
            issues.append(f"{label}:FORWARDER_PID")
        if record.get("fallback_5037_listener_pids"):
            issues.append(f"{label}:FORBIDDEN_5037")
        if not record.get("service_state", {}).get("qualified_bound"):
            issues.append(f"{label}:SERVICE_NOT_BOUND")
        if not record.get("sidecar_host_listener_owned"):
            issues.append(f"{label}:SIDECAR_LISTENER")
    return issues


class GuestReachableA11yGrpcWrapper(a11y_grpc_wrapper.A11yGrpcWrapper):
    """Replace local-only host credentials before the device endpoint is configured."""

    def __init__(self, env: Any, **kwargs: Any) -> None:
        super().__init__(env, **kwargs)
        old_port = int(self._port)  # noqa: SLF001
        stopped = self._server.stop(grace=0)  # noqa: SLF001
        if not stopped.wait(timeout=5.0):
            raise RuntimeError("LOCAL_CREDENTIAL_SERVER_STOP_TIMEOUT")
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))  # noqa: SLF001
        a11y_pb2_grpc.add_A11yServiceServicer_to_server(self._servicer, self._server)  # noqa: SLF001
        self._port = portpicker.pick_unused_port()  # noqa: SLF001
        bound_port = self._server.add_insecure_port(f"[::]:{self._port}")  # noqa: SLF001
        if bound_port != self._port:  # noqa: SLF001
            raise RuntimeError(f"INSECURE_SIDECAR_BIND_FAILED:{self._port}:{bound_port}")  # noqa: SLF001
        self._server.start()  # noqa: SLF001
        self._b2_10_transport = {
            "mode": "emulator_guest_plaintext_insecure_server",
            "replaced_local_credentials_port": old_port,
            "host_port": int(self._port),  # noqa: SLF001
            "bind_address": f"[::]:{self._port}",  # noqa: SLF001
        }
        self._b2_10_broadcasts: list[dict[str, Any]] = []

    def _configure_grpc(self) -> None:
        super()._configure_grpc()
        records = []
        for args in explicit_forwarder_broadcast_args(int(self._port)):  # noqa: SLF001
            response = self.execute_adb_call(
                adb_pb2.AdbRequest(generic=adb_pb2.AdbRequest.GenericRequest(args=list(args)))
            )
            record = {
                "args": list(args),
                "status": int(response.status),
                "error_message": response.error_message,
            }
            records.append(record)
            if response.status != adb_pb2.AdbResponse.Status.OK:
                self._b2_10_broadcasts = records
                raise RuntimeError(f"EXPLICIT_FORWARDER_BROADCAST_FAILED:{record}")
        self._b2_10_broadcasts = records


class FailClosedGuestSidecarController(android_world_controller.AndroidWorldController):
    """AndroidWorld controller that never performs the unsafe implicit refresh."""

    def __init__(self, env: Any) -> None:
        self._original_env = env
        self._env = GuestReachableA11yGrpcWrapper(
            env,
            install_a11y_forwarding=False,
            start_a11y_service=True,
            enable_a11y_tree_info=True,
            latest_a11y_info_only=True,
        )
        self._env.reset()
        self._a11y_method = android_world_controller.A11yMethod.A11Y_FORWARDER_APP

    def refresh_env(self) -> None:
        raise RuntimeError("IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN")

    def get_a11y_forest(self):
        return self._get_a11y_forest()  # noqa: SLF001


def load_explicit_guest_sidecar_env(
    *, adb_path: str, adb_server_port: int, console_port: int, grpc_port: int,
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
    return interface.AsyncAndroidEnv(FailClosedGuestSidecarController(instance))


def sidecar_runtime_identity(env: interface.AsyncAndroidEnv) -> dict[str, Any]:
    wrapper = env.controller.env
    if not isinstance(wrapper, GuestReachableA11yGrpcWrapper):
        raise RuntimeError("B2_10_GUEST_SIDECAR_WRAPPER_MISSING")
    return {
        "sidecar_host_port": int(wrapper.get_port()),
        "sidecar_wrapper_id": id(wrapper),
        "sidecar_wrapper_class": f"{type(wrapper).__module__}.{type(wrapper).__qualname__}",
        "controller_class": f"{type(env.controller).__module__}.{type(env.controller).__qualname__}",
        "transport": dict(wrapper._b2_10_transport),  # noqa: SLF001
        "broadcasts": list(wrapper._b2_10_broadcasts),  # noqa: SLF001
    }
