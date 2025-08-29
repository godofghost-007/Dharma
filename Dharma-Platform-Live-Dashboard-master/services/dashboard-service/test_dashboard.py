"""
Test Dashboard Service
Basic tests for dashboard functionality
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from app.core.config import DashboardConfig
from app.core.api_client import APIClient
from app.core.session_manager import SessionManager
from app.accessibility.wcag_compliance import WCAGCompliance
from app.i18n.translator import Translator, t

class TestDashboardConfig:
    """Test dashboard configuration"""
    
    def test_config_initialization(self):
        """Test config initialization with defaults"""
        config = DashboardConfig()
        
        assert config.api_gateway_url == "http://localhost:8000"
        assert config.refresh_interval == 30
        assert config.default_language == "en"
        assert "en" in config.supported_languages
        assert "hi" in config.supported_languages

class TestAPIClient:
    """Test API client functionality"""
    
    def test_api_client_initialization(self):
        """Test API client initialization"""
        client = APIClient("http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client._token is None
    
    def test_set_token(self):
        """Test setting authentication token"""
        client = APIClient("http://localhost:8000")
        client.set_token("test_token")
        
        assert client._token == "test_token"
        assert "Authorization" in client.client.headers
        assert client.client.headers["Authorization"] == "Bearer test_token"
    
    def test_mock_metrics_data(self):
        """Test mock metrics data generation"""
        client = APIClient("http://localhost:8000")
        metrics = client._get_mock_metrics()
        
        assert "active_alerts" in metrics
        assert "posts_analyzed_today" in metrics
        assert "bot_accounts_detected" in metrics
        assert "active_campaigns" in metrics
        assert isinstance(metrics["active_alerts"], int)

class TestSessionManager:
    """Test session management"""
    
    def test_session_manager_initialization(self):
        """Test session manager initialization"""
        # Mock streamlit session state
        with patch('streamlit.session_state', {}):
            session_manager = SessionManager()
            assert hasattr(session_manager, '_init_session_state')
    
    def test_login_logout(self):
        """Test login and logout functionality"""
        with patch('streamlit.session_state', {}) as mock_session:
            session_manager = SessionManager()
            
            # Test login
            user_data = {'username': 'test_user', 'role': 'analyst', 'token': 'test_token'}
            result = session_manager.login(user_data)
            
            assert result == True
            assert mock_session.get('authenticated') == True
            assert mock_session.get('user') == user_data
            
            # Test logout
            session_manager.logout()
            assert mock_session.get('authenticated') == False
            assert mock_session.get('user') is None

class TestWCAGCompliance:
    """Test WCAG compliance features"""
    
    def test_wcag_initialization(self):
        """Test WCAG compliance initialization"""
        wcag = WCAGCompliance()
        
        assert hasattr(wcag, 'high_contrast_colors')
        assert hasattr(wcag, 'normal_colors')
        assert '#000000' in wcag.high_contrast_colors.values()
        assert '#FFFFFF' in wcag.high_contrast_colors.values()
    
    def test_color_schemes(self):
        """Test color scheme definitions"""
        wcag = WCAGCompliance()
        
        # Test high contrast colors
        assert wcag.high_contrast_colors['background'] == '#000000'
        assert wcag.high_contrast_colors['text'] == '#FFFFFF'
        
        # Test normal colors
        assert wcag.normal_colors['background'] == '#FFFFFF'
        assert wcag.normal_colors['text'] == '#000000'

class TestTranslator:
    """Test internationalization features"""
    
    def test_translator_initialization(self):
        """Test translator initialization"""
        translator = Translator()
        
        assert hasattr(translator, 'supported_languages')
        assert 'en' in translator.supported_languages
        assert 'hi' in translator.supported_languages
        assert 'bn' in translator.supported_languages
        assert translator.current_language == 'en'
    
    def test_language_support(self):
        """Test supported languages"""
        translator = Translator()
        
        expected_languages = ['en', 'hi', 'bn', 'ta', 'ur', 'te', 'mr', 'gu']
        for lang in expected_languages:
            assert lang in translator.supported_languages
    
    def test_translation_function(self):
        """Test translation functionality"""
        translator = Translator()
        
        # Test English (default)
        result = translator.translate('dashboard.title')
        assert isinstance(result, str)
        
        # Test with default value
        result = translator.translate('nonexistent.key', 'Default Value')
        assert result == 'Default Value'
    
    def test_rtl_languages(self):
        """Test RTL language detection"""
        translator = Translator()
        
        rtl_languages = translator.get_rtl_languages()
        assert 'ur' in rtl_languages
        assert translator.is_rtl_language('ur') == True
        assert translator.is_rtl_language('en') == False
    
    def test_number_formatting(self):
        """Test localized number formatting"""
        translator = Translator()
        
        # Test Indian number system
        result = translator.format_number_localized(1500000, 'hi')
        assert 'L' in result or 'लाख' in result
        
        # Test Western number system
        result = translator.format_number_localized(1500000, 'en')
        assert 'M' in result

class TestIntegration:
    """Test integration between components"""
    
    def test_config_api_client_integration(self):
        """Test config and API client integration"""
        config = DashboardConfig()
        client = APIClient(config.api_gateway_url)
        
        assert client.base_url == config.api_gateway_url
    
    def test_translator_shorthand_function(self):
        """Test translator shorthand function"""
        result = t('dashboard.title', 'Default Title')
        assert isinstance(result, str)
        assert len(result) > 0

def test_dashboard_imports():
    """Test that all dashboard modules can be imported"""
    try:
        from app.pages.overview import OverviewPage
        from app.pages.campaign_analysis import CampaignAnalysisPage
        from app.pages.alert_management import AlertManagementPage
        from app.components.charts import ChartGenerator
        from app.components.metrics_cards import MetricsCards
        from app.utils.formatters import format_number, format_percentage
        
        assert True  # All imports successful
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_chart_generator():
    """Test chart generation functionality"""
    from app.components.charts import ChartGenerator
    
    chart_gen = ChartGenerator()
    assert hasattr(chart_gen, 'color_palette')
    assert 'pro_india' in chart_gen.color_palette
    assert 'anti_india' in chart_gen.color_palette

def test_formatters():
    """Test utility formatters"""
    from app.utils.formatters import format_number, format_percentage, format_time_ago
    
    # Test number formatting
    assert format_number(1500) == "1.5K"
    assert format_number(1500000) == "1.5M"
    assert format_number(1500000000) == "1.5B"
    
    # Test percentage formatting
    assert format_percentage(45.67) == "45.7%"
    assert format_percentage(100) == "100.0%"

if __name__ == "__main__":
    # Run basic tests
    print("Running dashboard tests...")
    
    # Test configuration
    config = DashboardConfig()
    print(f"✓ Config loaded: API Gateway URL = {config.api_gateway_url}")
    
    # Test API client
    client = APIClient(config.api_gateway_url)
    metrics = client._get_mock_metrics()
    print(f"✓ API Client working: {len(metrics)} metrics available")
    
    # Test translator
    translator = Translator()
    title = translator.translate('dashboard.title', 'Project Dharma')
    print(f"✓ Translator working: Title = {title}")
    
    # Test WCAG
    wcag = WCAGCompliance()
    print(f"✓ WCAG compliance initialized: {len(wcag.high_contrast_colors)} color schemes")
    
    print("All basic tests passed! ✅")