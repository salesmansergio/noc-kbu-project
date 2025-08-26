"""Tests for configuration settings."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch
from noc_kbu.config.settings import IntercomSettings, ZendeskSettings, ProcessingSettings, PathSettings, NOCKBUSettings


class TestIntercomSettings:
    """Test Intercom settings configuration."""
    
    def test_intercom_settings_from_env(self):
        """Test Intercom settings loaded from environment variables."""
        with patch.dict(os.environ, {
            'INTERCOM_ACCESS_TOKEN': 'test_token_123',
            'INTERCOM_API_BASE_URL': 'https://custom.intercom.io'
        }):
            settings = IntercomSettings()
            assert settings.access_token == 'test_token_123'
            assert settings.base_url == 'https://custom.intercom.io'
    
    def test_intercom_settings_defaults(self):
        """Test Intercom settings with default values."""
        with patch.dict(os.environ, {'INTERCOM_ACCESS_TOKEN': 'test_token'}):
            settings = IntercomSettings()
            assert settings.access_token == 'test_token'
            assert settings.base_url == 'https://api.intercom.io'


class TestZendeskSettings:
    """Test Zendesk settings configuration."""
    
    def test_zendesk_settings_from_env(self):
        """Test Zendesk settings loaded from environment variables."""
        with patch.dict(os.environ, {
            'ZENDESK_SUBDOMAIN': 'mycompany',
            'ZENDESK_EMAIL': 'admin@mycompany.com',
            'ZENDESK_API_TOKEN': 'zendesk_token_123'
        }):
            settings = ZendeskSettings()
            assert settings.subdomain == 'mycompany'
            assert settings.email == 'admin@mycompany.com'
            assert settings.api_token == 'zendesk_token_123'
    
    def test_zendesk_full_base_url(self):
        """Test Zendesk full base URL generation."""
        with patch.dict(os.environ, {
            'ZENDESK_SUBDOMAIN': 'testcompany',
            'ZENDESK_EMAIL': 'test@test.com',
            'ZENDESK_API_TOKEN': 'token'
        }):
            settings = ZendeskSettings()
            expected_url = 'https://testcompany.zendesk.com/api/v2'
            assert settings.full_base_url == expected_url
    
    def test_zendesk_custom_base_url(self):
        """Test Zendesk with custom base URL."""
        with patch.dict(os.environ, {
            'ZENDESK_SUBDOMAIN': 'testcompany',
            'ZENDESK_EMAIL': 'test@test.com',
            'ZENDESK_API_TOKEN': 'token',
            'ZENDESK_API_BASE_URL': 'https://custom.zendesk.io/api/v2'
        }):
            settings = ZendeskSettings()
            assert settings.full_base_url == 'https://custom.zendesk.io/api/v2'


class TestProcessingSettings:
    """Test processing settings configuration."""
    
    def test_processing_settings_defaults(self):
        """Test processing settings with default values."""
        settings = ProcessingSettings()
        assert settings.batch_size == 10
        assert settings.similarity_threshold == 0.85
        assert settings.quality_threshold == 0.7
        assert settings.max_retries == 3
        assert settings.request_delay == 1.0
        assert settings.min_content_length == 50
        assert settings.max_content_age_days == 365
    
    def test_processing_settings_from_env(self):
        """Test processing settings from environment variables."""
        with patch.dict(os.environ, {
            'BATCH_SIZE': '20',
            'SIMILARITY_THRESHOLD': '0.9',
            'QUALITY_SCORE_THRESHOLD': '0.8'
        }):
            settings = ProcessingSettings()
            assert settings.batch_size == 20
            assert settings.similarity_threshold == 0.9
            assert settings.quality_threshold == 0.8


class TestPathSettings:
    """Test path settings configuration."""
    
    def test_path_settings_defaults(self):
        """Test path settings with default values."""
        settings = PathSettings()
        assert settings.raw_data_path == Path("data/raw")
        assert settings.processed_data_path == Path("data/processed")
        assert settings.approved_data_path == Path("data/approved")
        assert settings.reports_path == Path("reports")
    
    def test_path_settings_from_env(self):
        """Test path settings from environment variables."""
        with patch.dict(os.environ, {
            'RAW_DATA_PATH': 'custom/raw',
            'PROCESSED_DATA_PATH': 'custom/processed'
        }):
            settings = PathSettings()
            assert settings.raw_data_path == Path("custom/raw")
            assert settings.processed_data_path == Path("custom/processed")
    
    @patch('pathlib.Path.mkdir')
    def test_ensure_directories(self, mock_mkdir):
        """Test directory creation."""
        settings = PathSettings()
        settings.ensure_directories()
        
        # Should call mkdir for each directory
        expected_calls = len([
            settings.raw_data_path,
            settings.processed_data_path,
            settings.approved_data_path,
            settings.reports_path
        ])
        assert mock_mkdir.call_count == expected_calls


class TestNOCKBUSettings:
    """Test main NOC KBU settings."""
    
    @patch.dict(os.environ, {
        'INTERCOM_ACCESS_TOKEN': 'test_token',
        'ZENDESK_SUBDOMAIN': 'test',
        'ZENDESK_EMAIL': 'test@test.com',
        'ZENDESK_API_TOKEN': 'test_token',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG'
    })
    @patch('noc_kbu.config.settings.PathSettings.ensure_directories')
    def test_nockbu_settings_initialization(self, mock_ensure_dirs):
        """Test NOC KBU settings initialization."""
        settings = NOCKBUSettings()
        
        # Check that sub-settings are initialized
        assert hasattr(settings, 'intercom')
        assert hasattr(settings, 'zendesk')
        assert hasattr(settings, 'processing')
        assert hasattr(settings, 'paths')
        
        # Check main settings
        assert settings.debug is True
        assert settings.log_level == 'DEBUG'
        
        # Check that directories are ensured
        mock_ensure_dirs.assert_called_once()
    
    @patch.dict(os.environ, {
        'INTERCOM_ACCESS_TOKEN': 'test_token',
        'ZENDESK_SUBDOMAIN': 'test',
        'ZENDESK_EMAIL': 'test@test.com',
        'ZENDESK_API_TOKEN': 'test_token'
    })
    @patch('noc_kbu.config.settings.PathSettings.ensure_directories')
    def test_settings_defaults(self, mock_ensure_dirs):
        """Test default values for main settings."""
        settings = NOCKBUSettings()
        assert settings.debug is False
        assert settings.log_level == 'INFO'


@pytest.fixture
def temp_env_vars():
    """Fixture to provide temporary environment variables for testing."""
    env_vars = {
        'INTERCOM_ACCESS_TOKEN': 'test_intercom_token',
        'ZENDESK_SUBDOMAIN': 'testcompany',
        'ZENDESK_EMAIL': 'test@testcompany.com',
        'ZENDESK_API_TOKEN': 'test_zendesk_token'
    }
    return env_vars


def test_settings_integration(temp_env_vars):
    """Integration test for all settings together."""
    with patch.dict(os.environ, temp_env_vars), \
         patch('noc_kbu.config.settings.PathSettings.ensure_directories'):
        
        settings = NOCKBUSettings()
        
        # Test that all components are properly initialized
        assert settings.intercom.access_token == 'test_intercom_token'
        assert settings.zendesk.subdomain == 'testcompany'
        assert settings.zendesk.email == 'test@testcompany.com'
        assert settings.processing.batch_size == 10
        assert settings.paths.raw_data_path == Path("data/raw")