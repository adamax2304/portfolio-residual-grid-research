from pathlib import Path

import pytest

from residual_grid_research.config import load_config


@pytest.fixture
def config():
    return load_config(Path(__file__).parents[1] / "config" / "default.yaml")

