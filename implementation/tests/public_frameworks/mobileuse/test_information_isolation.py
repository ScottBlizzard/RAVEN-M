import inspect

from raven_m.public_frameworks.mobileuse.controller import AndroidWorldEnvironmentBridge


def test_bridge_exposes_no_evaluator_or_hidden_task_fields():
    signature = inspect.signature(AndroidWorldEnvironmentBridge.__init__)
    assert "evaluator" not in signature.parameters
    assert "task" not in signature.parameters
    source = inspect.getsource(AndroidWorldEnvironmentBridge.get_state)
    assert "a11y_tree=None" in source
    assert "reward" not in source
    assert "ground_truth" not in source
