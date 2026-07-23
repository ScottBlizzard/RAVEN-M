import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.history.summary_schema import parse_summary_response


def test_summary_schema_accepts_strict_contract() -> None:
    parsed = parse_summary_response(
        '{"summary":"Opened the app.","completed":[],"pending":["Save."]}'
    )
    assert parsed.value["pending"] == ["Save."]


def test_summary_schema_rejects_extra_fields() -> None:
    with pytest.raises(ActionValidationError):
        parse_summary_response(
            '{"summary":"x","completed":[],"pending":[],"hidden":"no"}'
        )
