"""Unit tests for configuration management."""
import pytest
from unittest.mock import patch


@pytest.mark.unit
def test_config_loads_from_environment():
    """Unit test: Configuration loads from environment."""
    from src.config import get_config
    config = get_config()
    assert config is not None


@pytest.mark.unit
def test_config_has_cors_origins():
    """Unit test: Configuration includes CORS origins."""
    from src.config import get_config
    config = get_config()
    assert hasattr(config, 'cors_origins')
    assert isinstance(config.cors_origins, list)


@pytest.mark.unit
def test_config_has_app_title():
    """Unit test: Configuration includes app title."""
    from src.config import get_config
    config = get_config()
    assert hasattr(config, 'app_title')
    assert config.app_title == "Detection to COP"


@pytest.mark.unit
def test_config_defaults_are_set():
    """Unit test: Configuration defaults are set."""
    from src.config import get_config
    config = get_config()
    assert config.app_title == "Detection to COP"
    assert len(config.cors_origins) > 0
