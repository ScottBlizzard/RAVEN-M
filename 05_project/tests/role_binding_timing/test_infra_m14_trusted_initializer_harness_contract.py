"""Frozen, NOT-RUN contract tests for the INFRA-M14 pytest harness."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import inspect
import pickle
import sys
import uuid
from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TEST_ROOT.parent
PLUGIN_PATH = TEST_ROOT / "role_binding_timing" / "infra_m14_trusted_initializer_harness.py"
CONFTEST_PATH = TEST_ROOT / "conftest.py"
M14_IMPLEMENTATION_PATH = (
    PROJECT_ROOT
    / "src"
    / "raven_m"
    / "role_binding_timing"
    / "infra_m14_authority_context_attestation.py"
)
M14_MODULE = "raven_m.role_binding_timing.infra_m14_authority_context_attestation"
CONFIG_SHA256 = "8421E4985DEF834F84D5B22FFC0B2D22FF2A063473861213A64C4990C694C661"
INPUT_LOCK_SHA256 = "11BA21E3DAF4D8ED4BD0D2633E5D2EE9FD9583FB7060169FC3950AE777ADF4A6"
EXACT_PORTS = (5037, 5038, 5554, 5555, 8554)
ORIGINAL_CONFTEST_SHA256 = "CDF5B6DF6F7605CA14D7C05613A2A5FD33FBA56681797EB20FB080FDEC3CD908"
FROZEN_CONFTEST_SHA256 = "D12C1BCE097AE8FA2EA641A493E6E9B8EE42853E7F5116B6834A6968E1AD754E"
REGISTRATION_BLOCK = (
    b'\npytest_plugins = ("role_binding_timing.'
    b'infra_m14_trusted_initializer_harness",)\n'
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _load_plugin():
    unique_name = f"infra_m14_harness_contract_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(unique_name, PLUGIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module


def _assert_harness_error(module, callable_, code):
    with pytest.raises(module.HarnessContractError) as caught:
        callable_()
    assert caught.value.code == code


def _factory_call(factory, **overrides):
    values = {
        "runner_record": {"pid": 14, "create_time": 14.0},
        "known_paths": [],
        "controlled_ports": list(EXACT_PORTS),
        "config_sha256": CONFIG_SHA256,
        "input_lock_sha256": INPUT_LOCK_SHA256,
        "run_identity": "infra-m14-harness-run",
        "session_identity": "infra-m14-harness-session",
        "bootstrap_sample_identity": "infra-m14-harness-bootstrap",
        "expected_runner_record_sha256": "A" * 64,
    }
    values.update(overrides)
    return factory(**values)


class _FakeM14:
    def __init__(self, plugin, output_type_name="TrustedRunnerInitializer"):
        self.plugin = plugin
        self.output_type_name = output_type_name
        self.register_kwargs = None
        self.create_kwargs = None

    def _dev_register_trusted_initializer_harness(self, **kwargs):
        self.register_kwargs = copy.deepcopy(
            {key: value for key, value in kwargs.items() if key != "harness_capability"}
        )
        return self.plugin._claim_capability_for_m14_private_bootstrap(
            kwargs["harness_capability"]
        )

    def _dev_create_trusted_runner_initializer(self, **kwargs):
        self.plugin._validate_active_capability_for_m14_private_bootstrap(
            kwargs["harness_capability"], kwargs["registration_receipt"]
        )
        self.create_kwargs = copy.deepcopy(
            {
                key: value
                for key, value in kwargs.items()
                if key not in {"harness_capability", "registration_receipt"}
            }
        )
        return type(self.output_type_name, (), {})()


def test_plugin_import_does_not_load_m14_implementation_module():
    previous = sys.modules.pop(M14_MODULE, None)
    try:
        _load_plugin()
        assert M14_MODULE not in sys.modules
    finally:
        if previous is not None:
            sys.modules[M14_MODULE] = previous


def test_plugin_ast_has_no_eager_m14_import_and_one_fixture_name():
    source = PLUGIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    fixtures = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "fixture"
                for decorator in node.decorator_list
            ):
                fixtures.append(node.name)
    assert M14_MODULE not in imported
    assert fixtures == ["trusted_initializer_factory"]


@pytest.mark.parametrize("forged", [{}, object(), ("lookalike",)])
def test_ordinary_dictionary_or_object_cannot_register(forged):
    module = _load_plugin()
    _assert_harness_error(
        module,
        lambda: module._claim_capability_for_m14_private_bootstrap(forged),
        "HARNESS_CAPABILITY_REQUIRED",
    )


def test_capability_from_another_plugin_instance_cannot_register():
    module_a = _load_plugin()
    module_b = _load_plugin()
    foreign = module_b._issue_capability_for_fixture()
    _assert_harness_error(
        module_a,
        lambda: module_a._claim_capability_for_m14_private_bootstrap(foreign),
        "HARNESS_CAPABILITY_REQUIRED",
    )


def test_second_registration_is_rejected():
    module = _load_plugin()
    capability = module._issue_capability_for_fixture()
    module._claim_capability_for_m14_private_bootstrap(capability)
    _assert_harness_error(
        module,
        lambda: module._claim_capability_for_m14_private_bootstrap(capability),
        "SECOND_HARNESS_REGISTRATION_REJECTED",
    )


def test_second_fixture_factory_is_rejected():
    module = _load_plugin()
    module._new_trusted_initializer_factory_for_pytest()
    _assert_harness_error(
        module,
        module._new_trusted_initializer_factory_for_pytest,
        "SECOND_HARNESS_FACTORY_REJECTED",
    )


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_capability_rejects_copy_and_pickle(operation):
    module = _load_plugin()
    capability = module._issue_capability_for_fixture()
    with pytest.raises(TypeError):
        operation(capability)


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_receipt_rejects_copy_and_pickle(operation):
    module = _load_plugin()
    capability = module._issue_capability_for_fixture()
    receipt = module._claim_capability_for_m14_private_bootstrap(capability)
    with pytest.raises(TypeError):
        operation(receipt)


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_factory_rejects_copy_and_pickle(operation):
    module = _load_plugin()
    factory = module._new_trusted_initializer_factory_for_pytest()
    with pytest.raises(TypeError):
        operation(factory)


def test_factory_keeps_expected_bindings_separate_from_malformed_supplied_values(monkeypatch):
    module = _load_plugin()
    fake = _FakeM14(module)
    monkeypatch.setattr(module.importlib, "import_module", lambda name: fake)
    factory = module._new_trusted_initializer_factory_for_pytest()
    result = _factory_call(
        factory,
        controlled_ports=[],
        config_sha256="0" * 64,
        input_lock_sha256="1" * 64,
    )
    assert type(result).__name__ == "TrustedRunnerInitializer"
    assert fake.register_kwargs == {
        "harness_contract_version": module.HARNESS_CONTRACT_VERSION,
        "expected_config_sha256": CONFIG_SHA256,
        "expected_input_lock_sha256": INPUT_LOCK_SHA256,
        "expected_controlled_ports": EXACT_PORTS,
    }
    assert fake.create_kwargs["expected_config_sha256"] == CONFIG_SHA256
    assert fake.create_kwargs["expected_input_lock_sha256"] == INPUT_LOCK_SHA256
    assert fake.create_kwargs["expected_controlled_ports"] == EXACT_PORTS
    assert fake.create_kwargs["supplied_config_sha256"] == "0" * 64
    assert fake.create_kwargs["supplied_input_lock_sha256"] == "1" * 64
    assert fake.create_kwargs["supplied_controlled_ports"] == []


@pytest.mark.parametrize(
    "forbidden_type",
    ["LockedAuthorityContext", "VerifiedSeal", "IssuerLedger", "TemporalAttestation", "dict"],
)
def test_factory_cannot_return_context_seal_ledger_or_attestation(
    monkeypatch, forbidden_type
):
    module = _load_plugin()
    fake = _FakeM14(module, output_type_name=forbidden_type)
    monkeypatch.setattr(module.importlib, "import_module", lambda name: fake)
    factory = module._new_trusted_initializer_factory_for_pytest()
    _assert_harness_error(
        module,
        lambda: _factory_call(factory),
        "INITIALIZER_ONLY_RETURN_TYPE_REQUIRED",
    )


def test_factory_signature_has_no_validation_bypass_or_direct_authority_parameter():
    module = _load_plugin()
    signature = inspect.signature(module._TrustedInitializerFactory.__call__)
    names = set(signature.parameters)
    assert not names.intersection(
        {
            "skip_validation",
            "validate",
            "authority_context",
            "verified_seal",
            "ledger_entry",
            "attestation",
            "expected_config_sha256",
            "expected_input_lock_sha256",
            "expected_controlled_ports",
        }
    )


def test_conftest_is_exact_minimal_plugin_registration():
    current = CONFTEST_PATH.read_bytes()
    assert _sha(current) == FROZEN_CONFTEST_SHA256
    assert current.count(REGISTRATION_BLOCK) == 1
    reconstructed_original = current.replace(REGISTRATION_BLOCK, b"", 1)
    assert _sha(reconstructed_original) == ORIGINAL_CONFTEST_SHA256


def test_m14_implementation_is_absent_at_harness_freeze():
    assert not M14_IMPLEMENTATION_PATH.exists()
