"""Test path bootstrap for the project-local package."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

pytest_plugins = ("role_binding_timing.infra_m14_trusted_initializer_harness",)
