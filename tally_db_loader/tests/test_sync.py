"""
Integration tests for sync functionality.

Note: These tests require a running Tally instance and database.
Use pytest markers to skip when resources are unavailable.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
from tally_db_loader.config import TallyLoaderConfig
from tally_db_loader.sync import TallySync, run_sync


class TestTallySyncConfig:
    """Tests for configuration handling."""
    
    def test_config_from_env(self):
        """Test config loads from environment."""
        config = TallyLoaderConfig.from_env()
        assert config.tally_url is not None
        assert config.db_url is not None
    
    def test_config_validation(self):
        """Test config validation."""
        config = TallyLoaderConfig(tally_url="", db_url="")
        errors = config.validate()
        assert len(errors) > 0


class TestTallySyncUnit:
    """Unit tests for TallySync (mocked dependencies)."""
    
    @patch("tally_db_loader.sync.TallyLoaderClient")
    @patch("tally_db_loader.sync.MasterLoader")
    @patch("tally_db_loader.sync.TransactionLoader")
    def test_sync_master_calls_parser(self, mock_trn_loader, mock_mst_loader, mock_client):
        """Test that sync_master calls the correct parser."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.post_xml.return_value = """
            <ENVELOPE><BODY><DATA><COLLECTION></COLLECTION></DATA></BODY></ENVELOPE>
        """
        mock_client.return_value = mock_client_instance
        
        mock_loader_instance = Mock()
        mock_loader_instance.load_groups.return_value = 0
        mock_loader_instance.update_checkpoint = Mock()
        mock_mst_loader.return_value = mock_loader_instance
        
        # Create sync and run
        sync = TallySync()
        sync.sync_master("groups")
        
        # Verify client was called
        mock_client_instance.post_xml.assert_called_once()
        
        # Verify loader was called
        mock_loader_instance.load_groups.assert_called_once()


class TestTallySyncIntegration:
    """Integration tests (require running Tally and DB)."""
    
    @pytest.fixture
    def sync(self):
        """Create sync instance."""
        return TallySync()
    
    @pytest.mark.integration
    def test_connection(self, sync):
        """Test Tally connection."""
        result = sync.test_connection()
        assert result["status"] in ("connected", "connected_no_company")
    
    @pytest.mark.integration
    def test_initialize_schema(self, sync):
        """Test schema initialization."""
        sync.initialize_schema()
        # If no exception, success
    
    @pytest.mark.integration
    def test_sync_single_master(self, sync):
        """Test syncing a single master entity."""
        count = sync.sync_master("groups")
        assert count >= 0  # May be 0 if no groups in Tally


# Fixtures and test data
@pytest.fixture
def sample_xml():
    """Sample XML for testing."""
    return """
    <ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <STATUS>1</STATUS>
        </HEADER>
        <BODY>
            <DATA>
                <COLLECTION>
                    <GROUP NAME="Test Group" GUID="test-guid-123">
                        <ALTERID>1</ALTERID>
                        <PARENT>Primary</PARENT>
                    </GROUP>
                </COLLECTION>
            </DATA>
        </BODY>
    </ENVELOPE>
    """


# Custom markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Tally and DB)"
    )


# Run tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])

