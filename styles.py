"""
UI Styling, CSS injection, and formatting components for BRI KC TB Simatupang Dashboard.
Reflects modern banking visual direction:
- Sidebar (Menu Kiri): Signature Bank BRI Blue (#0857C3) with high-contrast white text, clear active indicators, and crisp widgets.
- Main Screen (Layar Kanan): Pure White (#FFFFFF) with dark, legible typography, crisp cards, and clean borders.
"""

import streamlit as st
import plotly.io as pio

# Enforce clean white template for all Plotly visualizations
pio.templates.default = "plotly_white"

# Primary Brand Colors (Extracted directly from BRI brand assets)
BRI_BLUE = "#0857C3"          # Signature Bank BRI Royal Blue
BRI_BLUE_DARK = "#06449A"     # Deep Blue accent
BRI_BLUE_LIGHT = "#EBF4FC"    # Soft blue tint for highlights
BRI_BLUE_HOVER = "#0A66E4"    # Lighter blue on hover
BRI_ORANGE = "#F37021"        # Signature BRI Orange
BRI_ORANGE_HOVER = "#E05D0E"  # Darker orange on hover
TEXT_DARK = "#0F172A"         # High-contrast Slate-900 for main text
TEXT_MUTED = "#475569"        # Slate-600 for subtext and captions
TEXT_LIGHT = "#FFFFFF"        # Pure white for sidebar text
BORDER_COLOR = "#E2E8F0"      # Light grey border for cards on white bg
CARD_BG = "#FFFFFF"           # White card background

CUSTOM_CSS = f"""
<style>
    /* Global Fonts & Reset */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {TEXT_DARK};
    }}
    
    /* =========================================================================
       1. MAIN SCREEN (LAYAR KANAN) - PURE WHITE BACKGROUND & HIGH CONTRAST
       ========================================================================= */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    .main .block-container,
    header[data-testid="stHeader"] {{
        background-color: #FFFFFF !important;
        color: {TEXT_DARK} !important;
    }}
    
    /* Top Header Bar inside Main View */
    header[data-testid="stHeader"] {{
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #F1F5F9 !important;
    }}
    
    /* Main Content Typography */
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {{
        color: {TEXT_DARK} !important;
        font-weight: 700 !important;
    }}
    .main p, .main span, .main div, .main label {{
        color: #1E293B;
    }}
    .main .stCaption, 
    .main [data-testid="stCaptionContainer"] p {{
        color: {TEXT_MUTED} !important;
        font-weight: 500 !important;
    }}
    .main hr {{
        border-color: {BORDER_COLOR} !important;
        opacity: 0.8;
    }}

    /* Top Bar Header Banner */
    .bri-header {{
        background: linear-gradient(135deg, {BRI_BLUE} 0%, {BRI_BLUE_DARK} 100%) !important;
        padding: 24px 30px;
        border-radius: 12px;
        color: #FFFFFF !important;
        margin-bottom: 20px;
        box-shadow: 0 4px 18px rgba(8, 87, 195, 0.18);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .bri-header h1 {{
        margin: 0;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF !important;
    }}
    .bri-header p {{
        margin: 6px 0 0 0;
        font-size: 13px;
        opacity: 0.95;
        color: #E2E8F0 !important;
    }}
    .bri-badge {{
        background: {BRI_ORANGE};
        color: #FFFFFF !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(243, 112, 33, 0.35);
    }}

    /* Main View Download Button (Top Toolbar) */
    .main .stDownloadButton > button {{
        background-color: {BRI_BLUE} !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        box-shadow: 0 2px 8px rgba(8, 87, 195, 0.25) !important;
        transition: all 0.2s ease !important;
    }}
    .main .stDownloadButton > button:hover {{
        background-color: {BRI_BLUE_DARK} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 87, 195, 0.35) !important;
    }}
    .main .stDownloadButton > button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* KPI Card Component on White Background */
    .kpi-card {{
        background-color: #FFFFFF !important;
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 12px;
        padding: 20px 22px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(8, 87, 195, 0.12) !important;
        border-color: {BRI_BLUE} !important;
    }}
    .kpi-card-strip {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }}
    .strip-blue {{ background-color: {BRI_BLUE} !important; }}
    .strip-orange {{ background-color: {BRI_ORANGE} !important; }}
    .strip-green {{ background-color: #10B981 !important; }}
    .strip-purple {{ background-color: #8B5CF6 !important; }}
    
    .kpi-label {{
        font-size: 12px;
        font-weight: 700;
        color: {TEXT_MUTED} !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 26px;
        font-weight: 800;
        color: {BRI_BLUE} !important;
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }}
    .kpi-subtext {{
        font-size: 12px;
        color: {TEXT_MUTED} !important;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 500;
    }}
    
    /* Tables & Dataframes */
    [data-testid="stDataFrame"] {{
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }}
    
    /* Filter container on Main Screen */
    .filter-box {{
        background: #F8FAFC !important;
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }}
    
    /* Info & Alert Cards */
    .info-card {{
        background-color: #F0F7FF !important;
        border-left: 4px solid {BRI_BLUE} !important;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
        font-size: 13px;
        color: {TEXT_DARK} !important;
    }}
    .warning-card {{
        background-color: #FFFBEB !important;
        border-left: 4px solid {BRI_ORANGE} !important;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
        font-size: 13px;
        color: #78350F !important;
    }}
    
    /* Streamlit Alert Boxes */
    .stAlert {{
        border-radius: 8px !important;
    }}
    .stAlert p, .stAlert span {{
        color: {TEXT_DARK} !important;
    }}
    
    /* Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 2px solid {BORDER_COLOR};
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: {TEXT_MUTED} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {BRI_BLUE_LIGHT} !important;
        color: {BRI_BLUE} !important;
        border-bottom: 3px solid {BRI_BLUE} !important;
    }}
    
    /* Inputs in Main Screen */
    .main input,
    .main textarea,
    .main select {{
        color: {TEXT_DARK} !important;
        background-color: #FFFFFF !important;
        border-color: #CBD5E1 !important;
    }}


    /* =========================================================================
       2. SIDEBAR (MENU KIRI) - BANK BRI BLUE (#0857C3) & ZERO CONTRAST COLLISION
       ========================================================================= */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebarContent"] {{
        background-color: {BRI_BLUE} !important;
        background: linear-gradient(180deg, {BRI_BLUE} 0%, {BRI_BLUE_DARK} 100%) !important;
        color: #FFFFFF !important;
        border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}
    
    /* Sidebar Headers, Markdown & Text */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {{
        color: #FFFFFF !important;
    }}
    
    section[data-testid="stSidebar"] hr {{
        border-color: rgba(255, 255, 255, 0.25) !important;
    }}
    
    /* Sidebar Radio Navigation */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 8px;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 10px 14px;
        border-radius: 8px;
        color: #FFFFFF !important;
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
        background: rgba(255, 255, 255, 0.22) !important;
        border-color: rgba(255, 255, 255, 0.45) !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label p,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label span,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label [data-testid="stMarkdownContainer"] p {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
    }}
    
    /* Active / Selected Radio Item: Crisp White Card with Blue Text */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
        background: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2) !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) span,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) [data-testid="stMarkdownContainer"] p {{
        color: {BRI_BLUE} !important;
        font-weight: 800 !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] div[data-baseweb="radio"] > div {{
        border-color: rgba(255, 255, 255, 0.7) !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) div[data-baseweb="radio"] > div {{
        border-color: {BRI_BLUE} !important;
        background-color: {BRI_BLUE} !important;
    }}
    
    /* Sidebar Selectbox */
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 13px !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        color: {TEXT_DARK} !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        font-weight: 600 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] * {{
        color: {TEXT_DARK} !important;
        font-weight: 600 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {{
        fill: {TEXT_DARK} !important;
    }}
    
    /* Sidebar Posisi Data Laporan Card */
    .sidebar-info-card {{
        background-color: #FFFFFF !important;
        border-radius: 10px !important;
        padding: 14px 16px !important;
        margin-top: 15px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }}
    .sidebar-info-card .card-badge {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: {BRI_BLUE} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    .sidebar-info-card .card-date {{
        font-size: 15px !important;
        font-weight: 800 !important;
        color: {TEXT_DARK} !important;
        margin-top: 2px !important;
    }}
    .sidebar-info-card .card-source {{
        font-size: 11px !important;
        color: {TEXT_MUTED} !important;
        margin-top: 4px !important;
    }}

    /* Sidebar Expander */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {{
        background-color: rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary {{
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary svg {{
        fill: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details > div:last-child {{
        background-color: #FFFFFF !important;
        border-radius: 0 0 8px 8px !important;
        padding: 14px !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details > div:last-child * {{
        color: {TEXT_DARK} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stExpander"] details > div:last-child .stCaption p {{
        color: {TEXT_MUTED} !important;
    }}

    /* Sidebar Buttons */
    section[data-testid="stSidebar"] .stButton > button {{
        background-color: #FFFFFF !important;
        color: {BRI_BLUE} !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.2s ease !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background-color: #F1F5F9 !important;
        color: {BRI_BLUE_DARK} !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.22) !important;
    }}
    section[data-testid="stSidebar"] .stButton > button p {{
        color: {BRI_BLUE} !important;
        font-weight: 700 !important;
    }}

    section[data-testid="stSidebar"] .stDownloadButton > button {{
        background-color: {BRI_ORANGE} !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        box-shadow: 0 4px 12px rgba(243, 112, 33, 0.4) !important;
        transition: all 0.2s ease !important;
    }}
    section[data-testid="stSidebar"] .stDownloadButton > button:hover {{
        background-color: {BRI_ORANGE_HOVER} !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(243, 112, 33, 0.55) !important;
    }}
    section[data-testid="stSidebar"] .stDownloadButton > button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* =========================================================================
       3. GLOBAL DROPDOWN / POPOVER LISTBOX (FIXES OPEN SELECTBOX OPTIONS)
       ========================================================================= */
    div[data-baseweb="popover"],
    ul[role="listbox"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15) !important;
        border-radius: 8px !important;
    }}
    ul[role="listbox"] li {{
        background-color: #FFFFFF !important;
        color: {TEXT_DARK} !important;
    }}
    ul[role="listbox"] li * {{
        color: {TEXT_DARK} !important;
        font-weight: 600 !important;
    }}
    ul[role="listbox"] li:hover,
    ul[role="listbox"] li[aria-selected="true"] {{
        background-color: {BRI_BLUE_LIGHT} !important;
    }}
    ul[role="listbox"] li:hover *,
    ul[role="listbox"] li[aria-selected="true"] * {{
        color: {BRI_BLUE} !important;
        font-weight: 700 !important;
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
