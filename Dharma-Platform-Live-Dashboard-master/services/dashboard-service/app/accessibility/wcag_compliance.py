"""
WCAG 2.1 Compliance Features
Implements accessibility features for dashboard components
"""

import streamlit as st
from typing import Dict, Any, Optional, List

class WCAGCompliance:
    """WCAG 2.1 compliance utilities and components"""
    
    def __init__(self):
        self.high_contrast_colors = {
            'background': '#000000',
            'text': '#FFFFFF',
            'primary': '#FFFF00',
            'secondary': '#00FFFF',
            'success': '#00FF00',
            'warning': '#FFA500',
            'danger': '#FF0000',
            'info': '#87CEEB'
        }
        
        self.normal_colors = {
            'background': '#FFFFFF',
            'text': '#000000',
            'primary': '#007bff',
            'secondary': '#6c757d',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8'
        }
    
    def apply_accessibility_settings(self):
        """Apply accessibility settings based on user preferences"""
        # Initialize accessibility settings in session state
        if 'accessibility_settings' not in st.session_state:
            st.session_state.accessibility_settings = {
                'high_contrast': False,
                'large_fonts': False,
                'screen_reader_mode': False,
                'keyboard_navigation': True,
                'reduced_motion': False
            }
        
        # Apply high contrast mode
        if st.session_state.accessibility_settings.get('high_contrast', False):
            self._apply_high_contrast_css()
        
        # Apply large font mode
        if st.session_state.accessibility_settings.get('large_fonts', False):
            self._apply_large_fonts_css()
        
        # Apply reduced motion
        if st.session_state.accessibility_settings.get('reduced_motion', False):
            self._apply_reduced_motion_css()
    
    def render_accessibility_controls(self):
        """Render accessibility control panel"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ♿ Accessibility")
        
        # High contrast toggle
        high_contrast = st.sidebar.checkbox(
            "High Contrast Mode",
            value=st.session_state.accessibility_settings.get('high_contrast', False),
            help="Enable high contrast colors for better visibility"
        )
        st.session_state.accessibility_settings['high_contrast'] = high_contrast
        
        # Large fonts toggle
        large_fonts = st.sidebar.checkbox(
            "Large Fonts",
            value=st.session_state.accessibility_settings.get('large_fonts', False),
            help="Increase font sizes for better readability"
        )
        st.session_state.accessibility_settings['large_fonts'] = large_fonts
        
        # Screen reader mode
        screen_reader = st.sidebar.checkbox(
            "Screen Reader Mode",
            value=st.session_state.accessibility_settings.get('screen_reader_mode', False),
            help="Optimize interface for screen readers"
        )
        st.session_state.accessibility_settings['screen_reader_mode'] = screen_reader
        
        # Reduced motion
        reduced_motion = st.sidebar.checkbox(
            "Reduce Motion",
            value=st.session_state.accessibility_settings.get('reduced_motion', False),
            help="Reduce animations and transitions"
        )
        st.session_state.accessibility_settings['reduced_motion'] = reduced_motion
        
        # Apply settings
        if st.sidebar.button("Apply Accessibility Settings"):
            self.apply_accessibility_settings()
            st.rerun()
    
    def _apply_high_contrast_css(self):
        """Apply high contrast CSS styles"""
        css = f"""
        <style>
        .stApp {{
            background-color: {self.high_contrast_colors['background']};
            color: {self.high_contrast_colors['text']};
        }}
        
        .stSidebar {{
            background-color: {self.high_contrast_colors['background']};
            color: {self.high_contrast_colors['text']};
        }}
        
        .stButton > button {{
            background-color: {self.high_contrast_colors['primary']};
            color: {self.high_contrast_colors['background']};
            border: 2px solid {self.high_contrast_colors['text']};
            font-weight: bold;
        }}
        
        .stSelectbox > div > div {{
            background-color: {self.high_contrast_colors['background']};
            color: {self.high_contrast_colors['text']};
            border: 2px solid {self.high_contrast_colors['text']};
        }}
        
        .stTextInput > div > div > input {{
            background-color: {self.high_contrast_colors['background']};
            color: {self.high_contrast_colors['text']};
            border: 2px solid {self.high_contrast_colors['text']};
        }}
        
        .stMetric {{
            background-color: {self.high_contrast_colors['background']};
            color: {self.high_contrast_colors['text']};
            border: 1px solid {self.high_contrast_colors['text']};
            padding: 10px;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    
    def _apply_large_fonts_css(self):
        """Apply large font CSS styles"""
        css = """
        <style>
        .stApp {
            font-size: 18px;
        }
        
        h1 {
            font-size: 3rem !important;
        }
        
        h2 {
            font-size: 2.5rem !important;
        }
        
        h3 {
            font-size: 2rem !important;
        }
        
        h4 {
            font-size: 1.5rem !important;
        }
        
        .stButton > button {
            font-size: 18px !important;
            padding: 12px 24px !important;
        }
        
        .stSelectbox > div > div {
            font-size: 18px !important;
        }
        
        .stTextInput > div > div > input {
            font-size: 18px !important;
        }
        
        .stMetric {
            font-size: 20px !important;
        }
        
        .stDataFrame {
            font-size: 16px !important;
        }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    
    def _apply_reduced_motion_css(self):
        """Apply reduced motion CSS styles"""
        css = """
        <style>
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
        
        .stSpinner > div {
            animation: none !important;
        }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    
    def create_accessible_button(
        self,
        label: str,
        key: str,
        help_text: Optional[str] = None,
        aria_label: Optional[str] = None,
        disabled: bool = False
    ) -> bool:
        """Create an accessible button with proper ARIA attributes"""
        
        # Use aria_label if provided, otherwise use label
        aria_label = aria_label or label
        
        # Create button with accessibility attributes
        button_html = f"""
        <button 
            id="{key}"
            aria-label="{aria_label}"
            title="{help_text or label}"
            {'disabled' if disabled else ''}
            style="
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #007bff;
                background-color: #007bff;
                color: white;
                border-radius: 4px;
                cursor: {'not-allowed' if disabled else 'pointer'};
                opacity: {'0.6' if disabled else '1'};
            "
            onkeydown="if(event.key === 'Enter' || event.key === ' ') this.click()"
        >
            {label}
        </button>
        """
        
        # Display the button
        st.markdown(button_html, unsafe_allow_html=True)
        
        # Return button state (simplified for demo)
        return st.button(label, key=key, help=help_text, disabled=disabled)
    
    def create_accessible_table(
        self,
        data: List[Dict[str, Any]],
        caption: str,
        headers: List[str],
        sortable: bool = True
    ):
        """Create an accessible data table with proper ARIA attributes"""
        
        if not data:
            st.info("No data available")
            return
        
        # Create accessible table HTML
        table_html = f"""
        <table role="table" aria-label="{caption}" style="width: 100%; border-collapse: collapse;">
            <caption style="font-weight: bold; margin-bottom: 10px;">{caption}</caption>
            <thead>
                <tr role="row">
        """
        
        # Add headers
        for header in headers:
            sort_attr = 'aria-sort="none"' if sortable else ''
            table_html += f'<th role="columnheader" {sort_attr} style="border: 1px solid #ddd; padding: 8px; background-color: #f8f9fa;">{header}</th>'
        
        table_html += """
                </tr>
            </thead>
            <tbody>
        """
        
        # Add data rows
        for i, row in enumerate(data):
            table_html += f'<tr role="row" style="{"background-color: #f8f9fa;" if i % 2 == 0 else ""}">'
            for header in headers:
                value = row.get(header.lower().replace(' ', '_'), '')
                table_html += f'<td role="cell" style="border: 1px solid #ddd; padding: 8px;">{value}</td>'
            table_html += '</tr>'
        
        table_html += """
            </tbody>
        </table>
        """
        
        st.markdown(table_html, unsafe_allow_html=True)
    
    def announce_to_screen_reader(self, message: str, priority: str = "polite"):
        """Announce message to screen readers using ARIA live regions"""
        aria_live = "assertive" if priority == "urgent" else "polite"
        
        announcement_html = f"""
        <div 
            aria-live="{aria_live}" 
            aria-atomic="true" 
            style="position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;"
        >
            {message}
        </div>
        """
        
        st.markdown(announcement_html, unsafe_allow_html=True)
    
    def create_skip_links(self):
        """Create skip navigation links for keyboard users"""
        skip_links_html = """
        <div id="skip-links" style="position: absolute; top: -40px; left: 6px; z-index: 1000;">
            <a href="#main-content" 
               style="
                   position: absolute;
                   left: -10000px;
                   top: auto;
                   width: 1px;
                   height: 1px;
                   overflow: hidden;
                   background: #000;
                   color: #fff;
                   padding: 8px 16px;
                   text-decoration: none;
                   border-radius: 4px;
               "
               onfocus="this.style.left='6px'; this.style.top='6px'; this.style.width='auto'; this.style.height='auto';"
               onblur="this.style.left='-10000px'; this.style.top='auto'; this.style.width='1px'; this.style.height='1px';"
            >
                Skip to main content
            </a>
        </div>
        """
        
        st.markdown(skip_links_html, unsafe_allow_html=True)
    
    def add_keyboard_navigation_support(self):
        """Add keyboard navigation support"""
        keyboard_js = """
        <script>
        document.addEventListener('keydown', function(event) {
            // Tab navigation enhancement
            if (event.key === 'Tab') {
                // Add visible focus indicators
                document.body.classList.add('keyboard-navigation');
            }
            
            // Escape key to close modals/dropdowns
            if (event.key === 'Escape') {
                // Close any open dropdowns or modals
                const dropdowns = document.querySelectorAll('.stSelectbox[aria-expanded="true"]');
                dropdowns.forEach(dropdown => {
                    dropdown.setAttribute('aria-expanded', 'false');
                });
            }
            
            // Arrow key navigation for lists
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                const focusedElement = document.activeElement;
                if (focusedElement.getAttribute('role') === 'option') {
                    event.preventDefault();
                    const options = Array.from(focusedElement.parentElement.children);
                    const currentIndex = options.indexOf(focusedElement);
                    let nextIndex;
                    
                    if (event.key === 'ArrowDown') {
                        nextIndex = (currentIndex + 1) % options.length;
                    } else {
                        nextIndex = (currentIndex - 1 + options.length) % options.length;
                    }
                    
                    options[nextIndex].focus();
                }
            }
        });
        
        // Remove keyboard navigation class on mouse use
        document.addEventListener('mousedown', function() {
            document.body.classList.remove('keyboard-navigation');
        });
        </script>
        
        <style>
        .keyboard-navigation *:focus {
            outline: 3px solid #005fcc !important;
            outline-offset: 2px !important;
        }
        </style>
        """
        
        st.markdown(keyboard_js, unsafe_allow_html=True)