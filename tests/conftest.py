try:
    # Enable pytest-twisted only if available
    import pytest_twisted as _
    pytest_plugins = "pytest_twisted"
except ImportError:
    pass
