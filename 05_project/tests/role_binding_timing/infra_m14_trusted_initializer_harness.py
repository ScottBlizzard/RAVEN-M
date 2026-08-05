"""Frozen pytest-only trusted-initializer harness for INFRA-M14.

Importing this plugin does not import the M14 implementation.  The one session
fixture lazily invokes M14's private DEV bootstrap only when its factory is
first called.  This is an offline engineering harness, not a production or
live bootstrap authority.
"""

from __future__ import annotations

import importlib
import secrets
import threading
import weakref

import pytest


M14_MODULE = "raven_m.role_binding_timing.infra_m14_authority_context_attestation"
HARNESS_CONTRACT_VERSION = "role_binding_timing.infra_m14.trusted_initializer_harness.v1"
CONFIG_SHA256 = "8421E4985DEF834F84D5B22FFC0B2D22FF2A063473861213A64C4990C694C661"
INPUT_LOCK_SHA256 = "11BA21E3DAF4D8ED4BD0D2633E5D2EE9FD9583FB7060169FC3950AE777ADF4A6"
EXACT_CONTROLLED_PORTS = (5037, 5038, 5554, 5555, 8554)
_CAPABILITY_CREATE_TOKEN = object()
_RECEIPT_CREATE_TOKEN = object()
_FACTORY_CREATE_TOKEN = object()
_STATE_LOCK = threading.RLock()
_CAPABILITY_STATES: dict[int, dict] = {}
_REGISTERED_CAPABILITY_ID: int | None = None
_FACTORY_CREATED = False


class HarnessContractError(RuntimeError):
    """Fail-closed harness boundary error with a stable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _reject_copy_or_pickle(name: str):
    raise TypeError(f"{name} is process-local and non-copyable")


class _TrustedInitializerHarnessCapability:
    __slots__ = ("_nonce", "__weakref__")

    def __new__(cls, token):
        if token is not _CAPABILITY_CREATE_TOKEN:
            raise HarnessContractError("HARNESS_CAPABILITY_CONSTRUCTOR_FORBIDDEN")
        return super().__new__(cls)

    def __init__(self, token):
        del token
        object.__setattr__(self, "_nonce", secrets.token_bytes(32))

    def __copy__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __deepcopy__(self, memo):
        del memo
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce_ex__(self, protocol):
        del protocol
        return _reject_copy_or_pickle(type(self).__name__)


class _HarnessRegistrationReceipt:
    __slots__ = ("_capability_id", "_nonce_digest", "__weakref__")

    def __new__(cls, token, capability_id: int, nonce_digest: bytes):
        if token is not _RECEIPT_CREATE_TOKEN:
            raise HarnessContractError("HARNESS_RECEIPT_CONSTRUCTOR_FORBIDDEN")
        return super().__new__(cls)

    def __init__(self, token, capability_id: int, nonce_digest: bytes):
        del token
        object.__setattr__(self, "_capability_id", capability_id)
        object.__setattr__(self, "_nonce_digest", nonce_digest)

    def __copy__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __deepcopy__(self, memo):
        del memo
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce_ex__(self, protocol):
        del protocol
        return _reject_copy_or_pickle(type(self).__name__)


def _capability_nonce_digest(capability: _TrustedInitializerHarnessCapability) -> bytes:
    import hashlib

    return hashlib.sha256(capability._nonce).digest()


def _issue_capability_for_fixture() -> _TrustedInitializerHarnessCapability:
    capability = _TrustedInitializerHarnessCapability(_CAPABILITY_CREATE_TOKEN)
    capability_id = id(capability)

    def _retire(_reference):
        with _STATE_LOCK:
            _CAPABILITY_STATES.pop(capability_id, None)

    with _STATE_LOCK:
        _CAPABILITY_STATES[capability_id] = {
            "reference": weakref.ref(capability, _retire),
            "claimed": False,
            "receipt_reference": None,
        }
    return capability


def _exact_capability_state(capability):
    if type(capability) is not _TrustedInitializerHarnessCapability:
        raise HarnessContractError("HARNESS_CAPABILITY_REQUIRED")
    state = _CAPABILITY_STATES.get(id(capability))
    if state is None or state["reference"]() is not capability:
        raise HarnessContractError("HARNESS_CAPABILITY_NOT_ISSUED_HERE")
    return state


def _claim_capability_for_m14_private_bootstrap(capability):
    """One-time callback used only by M14's future private DEV entry."""

    global _REGISTERED_CAPABILITY_ID
    with _STATE_LOCK:
        state = _exact_capability_state(capability)
        if state["claimed"] or _REGISTERED_CAPABILITY_ID is not None:
            raise HarnessContractError("SECOND_HARNESS_REGISTRATION_REJECTED")
        receipt = _HarnessRegistrationReceipt(
            _RECEIPT_CREATE_TOKEN,
            id(capability),
            _capability_nonce_digest(capability),
        )
        state["claimed"] = True
        state["receipt_reference"] = weakref.ref(receipt)
        _REGISTERED_CAPABILITY_ID = id(capability)
        return receipt


def _validate_active_capability_for_m14_private_bootstrap(capability, receipt):
    with _STATE_LOCK:
        state = _exact_capability_state(capability)
        if not state["claimed"] or _REGISTERED_CAPABILITY_ID != id(capability):
            raise HarnessContractError("HARNESS_CAPABILITY_NOT_REGISTERED")
        if type(receipt) is not _HarnessRegistrationReceipt:
            raise HarnessContractError("HARNESS_RECEIPT_REQUIRED")
        reference = state["receipt_reference"]
        if reference is None or reference() is not receipt:
            raise HarnessContractError("HARNESS_RECEIPT_MISMATCH")
        if receipt._capability_id != id(capability):
            raise HarnessContractError("HARNESS_RECEIPT_MISMATCH")
        if receipt._nonce_digest != _capability_nonce_digest(capability):
            raise HarnessContractError("HARNESS_RECEIPT_MISMATCH")
        return True


class _TrustedInitializerFactory:
    __slots__ = ("_capability", "_receipt", "_m14_module")

    def __new__(cls, token, capability):
        if token is not _FACTORY_CREATE_TOKEN:
            raise HarnessContractError("HARNESS_FACTORY_CONSTRUCTOR_FORBIDDEN")
        return super().__new__(cls)

    def __init__(self, token, capability):
        del token
        self._capability = capability
        self._receipt = None
        self._m14_module = None

    def __copy__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __deepcopy__(self, memo):
        del memo
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce__(self):
        return _reject_copy_or_pickle(type(self).__name__)

    def __reduce_ex__(self, protocol):
        del protocol
        return _reject_copy_or_pickle(type(self).__name__)

    def _ensure_registered(self):
        if self._receipt is not None:
            _validate_active_capability_for_m14_private_bootstrap(
                self._capability,
                self._receipt,
            )
            return self._m14_module
        module = importlib.import_module(M14_MODULE)
        register = getattr(module, "_dev_register_trusted_initializer_harness")
        receipt = register(
            harness_capability=self._capability,
            harness_contract_version=HARNESS_CONTRACT_VERSION,
            expected_config_sha256=CONFIG_SHA256,
            expected_input_lock_sha256=INPUT_LOCK_SHA256,
            expected_controlled_ports=EXACT_CONTROLLED_PORTS,
        )
        _validate_active_capability_for_m14_private_bootstrap(
            self._capability,
            receipt,
        )
        self._receipt = receipt
        self._m14_module = module
        return module

    def __call__(
        self,
        *,
        runner_record,
        known_paths,
        controlled_ports,
        config_sha256,
        input_lock_sha256,
        run_identity,
        session_identity,
        bootstrap_sample_identity,
        expected_runner_record_sha256,
    ):
        module = self._ensure_registered()
        create = getattr(module, "_dev_create_trusted_runner_initializer")
        result = create(
            harness_capability=self._capability,
            registration_receipt=self._receipt,
            harness_contract_version=HARNESS_CONTRACT_VERSION,
            expected_config_sha256=CONFIG_SHA256,
            expected_input_lock_sha256=INPUT_LOCK_SHA256,
            expected_controlled_ports=EXACT_CONTROLLED_PORTS,
            supplied_runner_record=runner_record,
            supplied_known_paths=known_paths,
            supplied_controlled_ports=controlled_ports,
            supplied_config_sha256=config_sha256,
            supplied_input_lock_sha256=input_lock_sha256,
            supplied_run_identity=run_identity,
            supplied_session_identity=session_identity,
            supplied_bootstrap_sample_identity=bootstrap_sample_identity,
            supplied_expected_runner_record_sha256=expected_runner_record_sha256,
        )
        if type(result).__name__ != "TrustedRunnerInitializer":
            raise HarnessContractError("INITIALIZER_ONLY_RETURN_TYPE_REQUIRED")
        return result


def _new_trusted_initializer_factory_for_pytest():
    global _FACTORY_CREATED
    with _STATE_LOCK:
        if _FACTORY_CREATED:
            raise HarnessContractError("SECOND_HARNESS_FACTORY_REJECTED")
        _FACTORY_CREATED = True
        capability = _issue_capability_for_fixture()
        return _TrustedInitializerFactory(_FACTORY_CREATE_TOKEN, capability)


@pytest.fixture(scope="session")
def trusted_initializer_factory():
    """Return the one offline-DEV initializer factory for frozen M14 tests."""

    return _new_trusted_initializer_factory_for_pytest()


__all__ = ["trusted_initializer_factory"]
