from unittest.mock import MagicMock

import dm_env
import numpy as np

from android_world.env.interface import AsyncAndroidEnv


def test_androidworld_reset_clears_answer_three_consecutive_times() -> None:
    controller = MagicMock()
    controller.reset.return_value = dm_env.restart(
        {
            "pixels": np.zeros((4, 4, 3), dtype=np.uint8),
            "forest": None,
            "ui_elements": [],
        }
    )
    env = AsyncAndroidEnv(controller)
    for cycle in range(3):
        env.interaction_cache = f"answer-{cycle}"
        env.reset(go_home=False)
        assert env.interaction_cache == ""
