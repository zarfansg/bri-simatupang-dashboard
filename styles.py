"""
UI Styling, CSS injection, and formatting components for BRI KC TB Simatupang Dashboard.
Reflects modern banking visual direction: BRI Blue, Orange, White, elegant KPI cards.
"""

import streamlit as st

BRI_BLUE = "#00529C"
BRI_BLUE_DARK = "#003b70"
BRI_BLUE_LIGHT = "#e6f0fa"
BRI_ORANGE = "#F37021"
BRI_ORANGE_LIGHT = "#fff2eb"
TEXT_DARK = "#1E293B"
TEXT_MUTED = "#64748B"
BORDER_COLOR = "#E2E8F0"
CARD_BG = "#FFFFFF"

CUSTOM_CSS = f"""
<style>
    /* Global Fonts & Reset */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {TEXT_DARK};
    }}
    
    /* Top Bar Header */
    .bri-header {{
        background: linear-gradient(135deg, {BRI_BLUE} 0%, {BRI_BLUE_DARK} 100%);
        padding: 24px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 82, 156, 0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .bri-header h1 {{
        margin: 0;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: white !important;
    }}
    .bri-header p {{
        margin: 4px 0 0 0;
        font-size: 13px;
        opacity: 0.9;
        color: #E2E8F0;
    }}
    .bri-badge {{
        background: {BRI_ORANGE};
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(243, 112, 33, 0.3);
    }}
    
    /* KPI Card Component */
    .kpi-card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
        padding: 20px 22px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
        border-color: {BRI_BLUE};
    }}
    .kpi-card-strip {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }}
    .strip-blue {{ background-color: {BRI_BLUE}; }}
    .strip-orange {{ background-color: {BRI_ORANGE}; }}
    .strip-green {{ background-color: #10B981; }}
    .strip-purple {{ background-color: #8B5CF6; }}
    
    .kpi-label {{
        font-size: 13px;
        font-weight: 600;
        color: {TEXT_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 26px;
        font-weight: 700;
        color: {BRI_BLUE};
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }}
    .kpi-subtext {{
        font-size: 12px;
        color: {TEXT_MUTED};
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    /* Data table header */
    .stDataFrame {{
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
    }}
    
    /* Filter container */
    .filter-box {{
        background: {BRI_BLUE_LIGHT};
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }}
    
    /* Custom Alert */
    .info-card {{
        background-color: #F8FAFC;
        border-left: 4px solid {BRI_BLUE};
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
        font-size: 13px;
    }}
    .warning-card {{
        background-color: #FFFBEB;
        border-left: 4px solid {BRI_ORANGE};
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
        font-size: 13px;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: #F8FAFC !important;
        border-right: 1px solid {BORDER_COLOR};
    }}
    
    /* Streamlit tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
        color: {TEXT_MUTED};
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {BRI_BLUE_LIGHT} !important;
        color: {BRI_BLUE} !important;
    }}
</style>
"""

def inject_styles():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_kpi_card(label, compact_value, full_value, sub_text="", strip_color="strip-blue"):
    """Render a styled KPI Card."""
    card_html = f"""
    <div class="kpi-card">
        <div class="kpi-card-strip {strip_color}"></div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{compact_value}</div>
        <div class="kpi-subtext">
            <span>{full_value}</span>
            <span>{sub_text}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
