import pytest
import sys
from pathlib import Path


class TestSetupValidation:
    """Validation tests to ensure the testing infrastructure is properly configured."""
    
    def test_python_version(self):
        """Verify Python version is 3.7 or higher."""
        assert sys.version_info >= (3, 7), "Python 3.7 or higher is required"
    
    def test_project_structure(self):
        """Verify the project structure is correct."""
        root_dir = Path(__file__).parent.parent
        
        # Check main package exists
        assert (root_dir / "miservice").is_dir()
        assert (root_dir / "miservice" / "__init__.py").is_file()
        
        # Check test directories exist
        assert (root_dir / "tests").is_dir()
        assert (root_dir / "tests" / "unit").is_dir()
        assert (root_dir / "tests" / "integration").is_dir()
        
        # Check configuration files exist
        assert (root_dir / "pyproject.toml").is_file()
    
    def test_imports(self):
        """Verify main package can be imported."""
        try:
            import miservice
            assert miservice is not None
        except ImportError:
            pytest.fail("Failed to import miservice package")
    
    @pytest.mark.unit
    def test_unit_marker(self):
        """Verify unit test marker works."""
        assert True
    
    @pytest.mark.integration
    def test_integration_marker(self):
        """Verify integration test marker works."""
        assert True
    
    @pytest.mark.slow
    def test_slow_marker(self):
        """Verify slow test marker works."""
        assert True
    
    def test_fixtures_available(self, temp_dir, mock_config, mock_session):
        """Verify pytest fixtures are available."""
        assert temp_dir.is_dir()
        assert isinstance(mock_config, dict)
        assert mock_config["user"] == "test_user@example.com"
        assert mock_session is not None
    
    def test_environment_reset(self):
        """Verify environment variables are reset between tests."""
        import os
        assert "MI_USER" not in os.environ
        assert "MI_PASS" not in os.environ
        assert "MI_DID" not in os.environ
    
    def test_environment_fixture(self, set_test_environment):
        """Verify environment fixture works correctly."""
        import os
        assert os.environ["MI_USER"] == "test_user@example.com"
        assert os.environ["MI_PASS"] == "test_password"
        assert os.environ["MI_DID"] == "test_device_123"