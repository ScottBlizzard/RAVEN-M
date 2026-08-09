from raven_m.public_frameworks.mobileuse.action_adapter import MobileUseActionAdapter


def test_single_call_validator_rejects_zero_and_two_calls():
    for value in ("no call", '"name":"mobile_use" "name":"mobile_use"'):
        try:
            MobileUseActionAdapter.assert_single_action_output(value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid call count was accepted")
