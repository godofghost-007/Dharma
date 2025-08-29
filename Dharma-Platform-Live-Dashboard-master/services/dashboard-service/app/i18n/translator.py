"""
Internationalization (i18n) Support
Multi-language support for Indian languages and English
"""

import streamlit as st
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class Translator:
    """Multi-language translation support"""
    
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'hi': 'हिन्दी (Hindi)',
            'bn': 'বাংলা (Bengali)',
            'ta': 'தமிழ் (Tamil)',
            'ur': 'اردو (Urdu)',
            'te': 'తెలుగు (Telugu)',
            'mr': 'मराठी (Marathi)',
            'gu': 'ગુજરાતી (Gujarati)'
        }
        
        self.translations = {}
        self.current_language = 'en'
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files"""
        translations_dir = Path(__file__).parent / 'translations'
        
        # Create default translations if directory doesn't exist
        if not translations_dir.exists():
            translations_dir.mkdir(exist_ok=True)
            self._create_default_translations(translations_dir)
        
        # Load translation files
        for lang_code in self.supported_languages.keys():
            translation_file = translations_dir / f'{lang_code}.json'
            if translation_file.exists():
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
            else:
                self.translations[lang_code] = {}
    
    def _create_default_translations(self, translations_dir: Path):
        """Create default translation files"""
        
        # English (base language)
        en_translations = {
            "dashboard": {
                "title": "Project Dharma - Social Media Intelligence",
                "overview": "Dashboard Overview",
                "campaign_analysis": "Campaign Analysis",
                "alert_management": "Alert Management",
                "settings": "Settings"
            },
            "metrics": {
                "active_alerts": "Active Alerts",
                "posts_analyzed_today": "Posts Analyzed Today",
                "bot_accounts_detected": "Bot Accounts Detected",
                "active_campaigns": "Active Campaigns",
                "sentiment_distribution": "Sentiment Distribution",
                "platform_activity": "Platform Activity"
            },
            "sentiment": {
                "pro_india": "Pro-India",
                "neutral": "Neutral",
                "anti_india": "Anti-India",
                "positive": "Positive",
                "negative": "Negative"
            },
            "alerts": {
                "new": "New",
                "acknowledged": "Acknowledged",
                "in_progress": "In Progress",
                "resolved": "Resolved",
                "critical": "Critical",
                "high": "High",
                "medium": "Medium",
                "low": "Low"
            },
            "campaigns": {
                "coordination_score": "Coordination Score",
                "participants": "Participants",
                "detected": "Detected",
                "impact_score": "Impact Score",
                "network_graph": "Network Graph",
                "timeline_analysis": "Timeline Analysis"
            },
            "actions": {
                "login": "Login",
                "logout": "Logout",
                "refresh": "Refresh",
                "export": "Export",
                "acknowledge": "Acknowledge",
                "assign": "Assign",
                "search": "Search",
                "filter": "Filter",
                "sort": "Sort"
            },
            "navigation": {
                "skip_to_content": "Skip to main content",
                "main_menu": "Main Menu",
                "user_menu": "User Menu"
            },
            "accessibility": {
                "high_contrast": "High Contrast Mode",
                "large_fonts": "Large Fonts",
                "screen_reader": "Screen Reader Mode",
                "reduce_motion": "Reduce Motion",
                "keyboard_navigation": "Keyboard Navigation"
            }
        }
        
        # Hindi translations
        hi_translations = {
            "dashboard": {
                "title": "प्रोजेक्ट धर्म - सोशल मीडिया इंटेलिजेंस",
                "overview": "डैशबोर्ड अवलोकन",
                "campaign_analysis": "अभियान विश्लेषण",
                "alert_management": "अलर्ट प्रबंधन",
                "settings": "सेटिंग्स"
            },
            "metrics": {
                "active_alerts": "सक्रिय अलर्ट",
                "posts_analyzed_today": "आज विश्लेषित पोस्ट",
                "bot_accounts_detected": "बॉट खाते का पता लगाया गया",
                "active_campaigns": "सक्रिय अभियान",
                "sentiment_distribution": "भावना वितरण",
                "platform_activity": "प्लेटफॉर्म गतिविधि"
            },
            "sentiment": {
                "pro_india": "भारत समर्थक",
                "neutral": "तटस्थ",
                "anti_india": "भारत विरोधी",
                "positive": "सकारात्मक",
                "negative": "नकारात्मक"
            },
            "alerts": {
                "new": "नया",
                "acknowledged": "स्वीकृत",
                "in_progress": "प्रगति में",
                "resolved": "हल किया गया",
                "critical": "गंभीर",
                "high": "उच्च",
                "medium": "मध्यम",
                "low": "कम"
            }
        }
        
        # Bengali translations
        bn_translations = {
            "dashboard": {
                "title": "প্রজেক্ট ধর্ম - সোশ্যাল মিডিয়া ইন্টেলিজেন্স",
                "overview": "ড্যাশবোর্ড ওভারভিউ",
                "campaign_analysis": "ক্যাম্পেইন বিশ্লেষণ",
                "alert_management": "সতর্কতা ব্যবস্থাপনা",
                "settings": "সেটিংস"
            },
            "metrics": {
                "active_alerts": "সক্রিয় সতর্কতা",
                "posts_analyzed_today": "আজ বিশ্লেষিত পোস্ট",
                "bot_accounts_detected": "বট অ্যাকাউন্ট সনাক্ত",
                "active_campaigns": "সক্রিয় ক্যাম্পেইন"
            }
        }
        
        # Save translation files
        translations = {
            'en': en_translations,
            'hi': hi_translations,
            'bn': bn_translations
        }
        
        for lang_code, translation_data in translations.items():
            with open(translations_dir / f'{lang_code}.json', 'w', encoding='utf-8') as f:
                json.dump(translation_data, f, ensure_ascii=False, indent=2)
    
    def set_language(self, language_code: str):
        """Set the current language"""
        if language_code in self.supported_languages:
            self.current_language = language_code
            st.session_state.language = language_code
    
    def get_current_language(self) -> str:
        """Get the current language code"""
        return st.session_state.get('language', self.current_language)
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        """Translate a key to the current language"""
        current_lang = self.get_current_language()
        
        # Navigate through nested keys (e.g., "dashboard.title")
        keys = key.split('.')
        translation_dict = self.translations.get(current_lang, {})
        
        for k in keys:
            if isinstance(translation_dict, dict) and k in translation_dict:
                translation_dict = translation_dict[k]
            else:
                # Fallback to English if translation not found
                translation_dict = self.translations.get('en', {})
                for k in keys:
                    if isinstance(translation_dict, dict) and k in translation_dict:
                        translation_dict = translation_dict[k]
                    else:
                        return default or key
                break
        
        return translation_dict if isinstance(translation_dict, str) else (default or key)
    
    def render_language_selector(self):
        """Render language selection dropdown"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🌐 Language / भाषा")
        
        current_lang = self.get_current_language()
        
        # Language selection
        selected_lang = st.sidebar.selectbox(
            "Select Language",
            options=list(self.supported_languages.keys()),
            format_func=lambda x: self.supported_languages[x],
            index=list(self.supported_languages.keys()).index(current_lang),
            key="language_selector"
        )
        
        if selected_lang != current_lang:
            self.set_language(selected_lang)
            st.rerun()
    
    def get_rtl_languages(self) -> list:
        """Get list of right-to-left languages"""
        return ['ur', 'ar', 'fa']  # Urdu, Arabic, Persian
    
    def is_rtl_language(self, language_code: Optional[str] = None) -> bool:
        """Check if current or specified language is RTL"""
        lang = language_code or self.get_current_language()
        return lang in self.get_rtl_languages()
    
    def apply_rtl_css(self):
        """Apply RTL CSS for right-to-left languages"""
        if self.is_rtl_language():
            rtl_css = """
            <style>
            .stApp {
                direction: rtl;
                text-align: right;
            }
            
            .stSidebar {
                direction: rtl;
                text-align: right;
            }
            
            .stButton > button {
                direction: rtl;
            }
            
            .stSelectbox > div {
                direction: rtl;
            }
            
            .stTextInput > div {
                direction: rtl;
            }
            
            /* Flip icons for RTL */
            .stSidebar .stSelectbox > div > div > div {
                transform: scaleX(-1);
            }
            </style>
            """
            st.markdown(rtl_css, unsafe_allow_html=True)
    
    def format_number_localized(self, number: float, language_code: Optional[str] = None) -> str:
        """Format numbers according to locale"""
        lang = language_code or self.get_current_language()
        
        # Indian number system for Hindi and other Indian languages
        if lang in ['hi', 'bn', 'ta', 'te', 'mr', 'gu']:
            if number >= 10000000:  # 1 crore
                return f"{number / 10000000:.1f} करोड़" if lang == 'hi' else f"{number / 10000000:.1f}Cr"
            elif number >= 100000:  # 1 lakh
                return f"{number / 100000:.1f} लाख" if lang == 'hi' else f"{number / 100000:.1f}L"
            elif number >= 1000:
                return f"{number / 1000:.1f}K"
            else:
                return str(int(number))
        else:
            # Western number system
            if number >= 1000000000:
                return f"{number / 1000000000:.1f}B"
            elif number >= 1000000:
                return f"{number / 1000000:.1f}M"
            elif number >= 1000:
                return f"{number / 1000:.1f}K"
            else:
                return str(int(number))
    
    def get_date_format(self, language_code: Optional[str] = None) -> str:
        """Get date format for the specified language"""
        lang = language_code or self.get_current_language()
        
        date_formats = {
            'en': '%Y-%m-%d',
            'hi': '%d/%m/%Y',
            'bn': '%d/%m/%Y',
            'ta': '%d/%m/%Y',
            'ur': '%d/%m/%Y',
            'te': '%d/%m/%Y',
            'mr': '%d/%m/%Y',
            'gu': '%d/%m/%Y'
        }
        
        return date_formats.get(lang, '%Y-%m-%d')
    
    def get_time_format(self, language_code: Optional[str] = None) -> str:
        """Get time format for the specified language"""
        lang = language_code or self.get_current_language()
        
        time_formats = {
            'en': '%H:%M:%S',
            'hi': '%H:%M:%S',
            'bn': '%H:%M:%S',
            'ta': '%H:%M:%S',
            'ur': '%H:%M:%S',
            'te': '%H:%M:%S',
            'mr': '%H:%M:%S',
            'gu': '%H:%M:%S'
        }
        
        return time_formats.get(lang, '%H:%M:%S')

# Global translator instance
translator = Translator()

def t(key: str, default: Optional[str] = None) -> str:
    """Shorthand function for translation"""
    return translator.translate(key, default)