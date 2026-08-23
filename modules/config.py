"""
Configuration and Session Management for Data Studio
"""

import os
import streamlit as st

# Application Metadata
APP_NAME = "Data Studio"
APP_TAGLINE = "Exploratory Data Analysis"
APP_VERSION = "0.2.0"
APP_ICON = "activity"

# Navigation Options
NAV_OVERVIEW = "Overview"
NAV_DATASET = "Dataset"
NAV_DATA_PREPARATION = "Data Preparation"
NAV_AI_ANALYST = "AI Analyst"
NAV_VISUALIZATION = "Visualization"
NAV_DASHBOARD = NAV_VISUALIZATION
NAV_SETTINGS = "Settings"

NAV_OPTIONS = [
    NAV_OVERVIEW,
    NAV_DATASET,
    NAV_DATA_PREPARATION,
    NAV_AI_ANALYST,
    NAV_VISUALIZATION,
    NAV_SETTINGS,
]

NAV_ICONS = {
    NAV_OVERVIEW: "activity",
    NAV_DATASET: "database",
    NAV_DATA_PREPARATION: "sliders",
    NAV_AI_ANALYST: "cpu",
    NAV_VISUALIZATION: "bar-chart-2",
    NAV_DASHBOARD: "bar-chart-2",
    "Dashboard": "bar-chart-2",
    NAV_SETTINGS: "settings",
}

# Path Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CSS_FILE = os.path.join(ASSETS_DIR, "css", "style.css")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")


def load_custom_css():
    """Load and inject custom CSS with support for light and dark themes."""
    theme = st.session_state.get("theme", "light")
    if os.path.exists(CSS_FILE):
        with open(CSS_FILE, "r", encoding="utf-8") as f:
            css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    
    # Inject dark mode overrides if theme is set to dark
    if theme == "dark":
        dark_css = """
        :root {
            --bg-app: #0B0F17;
            --bg-surface: #111827;
            --bg-subtle: #1E293B;
            --border-subtle: #1E293B;
            --border-strong: #334155;
            --text-primary: #F8FAFC;
            --text-secondary: #CBD5E1;
            --text-muted: #94A3B8;
            --text-faint: #64748B;
        }

        .stApp, [data-testid="stAppViewContainer"], body, html {
            background-color: #0B0F17 !important;
            color: #F8FAFC !important;
        }

        /* Top Header in Dark Mode */
        header[data-testid="stHeader"], .stAppHeader {
            background-color: #0B0F17 !important;
            background: #0B0F17 !important;
            color: #F8FAFC !important;
            border-bottom: 1px solid #1E293B !important;
        }

        header[data-testid="stHeader"] button,
        .stAppHeader button {
            color: #94A3B8 !important;
        }

        header[data-testid="stHeader"] button:hover,
        .stAppHeader button:hover {
            color: #FFFFFF !important;
        }

        [data-testid="stSidebar"] {
            background-color: #0F172A !important;
            border-right: 1px solid #1E293B !important;
        }

        .sidebar-logo-icon {
            background: #1E293B !important;
            border-color: #334155 !important;
            color: #60A5FA !important;
        }

        .sidebar-app-name {
            color: #FFFFFF !important;
        }

        .sidebar-app-tagline {
            color: #94A3B8 !important;
        }

        .sidebar-divider, .section-divider, .app-footer {
            background: #1E293B !important;
            border-color: #1E293B !important;
        }

        .sidebar-status-card {
            background-color: #111827 !important;
            border-color: #1E293B !important;
        }

        /* High-Contrast Radio Navigation in Dark Mode */
        div[data-testid="stRadio"] label {
            background-color: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 6px !important;
            padding: 0.45rem 0.7rem !important;
        }

        div[data-testid="stRadio"] label,
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label span,
        div[data-testid="stRadio"] label div,
        div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
            color: #CBD5E1 !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
        }

        div[data-testid="stRadio"] label:hover {
            background-color: #1E293B !important;
        }

        div[data-testid="stRadio"] label:hover p,
        div[data-testid="stRadio"] label:hover span {
            color: #FFFFFF !important;
        }

        div[data-testid="stRadio"] label[data-checked="true"],
        div[data-testid="stRadio"] label:has(input:checked) {
            background-color: rgba(37, 99, 235, 0.15) !important;
            border: 1px solid rgba(59, 130, 246, 0.35) !important;
        }

        div[data-testid="stRadio"] label[data-checked="true"] p,
        div[data-testid="stRadio"] label:has(input:checked) p,
        div[data-testid="stRadio"] label[data-checked="true"] span,
        div[data-testid="stRadio"] label:has(input:checked) span {
            color: #60A5FA !important;
            font-weight: 600 !important;
        }

        .page-header-container, .feature-card, .dataset-kpi-card, .table-info-bar, .empty-upload-card {
            background-color: #111827 !important;
            border-color: #1E293B !important;
        }

        .page-header-badge {
            background-color: #1E293B !important;
            border-color: #334155 !important;
            color: #CBD5E1 !important;
        }

        .spec-chip {
            background-color: #1E293B !important;
            border-color: #334155 !important;
            color: #CBD5E1 !important;
        }

        div[data-testid="stRadio"] label,
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label span,
        div[data-testid="stRadio"] label div,
        div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
            color: #E2E8F0 !important;
            font-size: 0.94rem !important;
            font-weight: 500 !important;
        }

        div[data-testid="stRadio"] label:hover {
            background-color: #1E293B !important;
            border-color: #334155 !important;
        }

        div[data-testid="stRadio"] label:hover p,
        div[data-testid="stRadio"] label:hover span {
            color: #FFFFFF !important;
        }

        div[data-testid="stRadio"] label[data-checked="true"],
        div[data-testid="stRadio"] label:has(input:checked) {
            background: rgba(37, 99, 235, 0.22) !important;
            border: 1px solid #3B82F6 !important;
        }

        div[data-testid="stRadio"] label[data-checked="true"] p,
        div[data-testid="stRadio"] label:has(input:checked) p,
        div[data-testid="stRadio"] label[data-checked="true"] span,
        div[data-testid="stRadio"] label:has(input:checked) span {
            color: #60A5FA !important;
            font-weight: 700 !important;
        }

        /* Radio circle indicator */
        div[data-testid="stRadio"] label > div:first-child {
            background-color: #1E293B !important;
            border: 2px solid #64748B !important;
        }

        div[data-testid="stRadio"] label:has(input:checked) > div:first-child,
        div[data-testid="stRadio"] label[data-checked="true"] > div:first-child {
            background-color: #3B82F6 !important;
            border-color: #60A5FA !important;
        }

        .page-header-container, .feature-card, .step-card, .dataset-kpi-card, .empty-upload-card, .coming-soon-container, .roadmap-item {
            background-color: #111827 !important;
            border-color: #1F2937 !important;
            color: #F1F5F9 !important;
        }

        .page-header-title, .feature-title, .step-title, .dataset-kpi-val, .empty-upload-title, .coming-soon-title {
            color: #F8FAFC !important;
        }

        .page-header-subtitle, .feature-desc, .step-desc, .dataset-kpi-lbl, .empty-upload-desc, .coming-soon-desc, .roadmap-text {
            color: #94A3B8 !important;
        }

        .page-header-badge {
            background-color: rgba(59, 130, 246, 0.15) !important;
            border-color: rgba(59, 130, 246, 0.3) !important;
            color: #93C5FD !important;
        }

        .table-info-bar {
            background-color: #0B0F17 !important;
            border-color: #1F2937 !important;
            color: #94A3B8 !important;
        }

        .table-info-bar strong {
            color: #F8FAFC !important;
        }

        .spec-chip {
            background-color: #0B0F17 !important;
            border-color: #1F2937 !important;
            color: #CBD5E1 !important;
        }

        .blue-glow { background: rgba(59, 130, 246, 0.15) !important; border-color: rgba(59, 130, 246, 0.3) !important; }
        .purple-glow { background: rgba(139, 92, 246, 0.15) !important; border-color: rgba(139, 92, 246, 0.3) !important; }
        .emerald-glow { background: rgba(16, 185, 129, 0.15) !important; border-color: rgba(16, 185, 129, 0.3) !important; }
        .amber-glow { background: rgba(245, 158, 11, 0.15) !important; border-color: rgba(245, 158, 11, 0.3) !important; }

        .badge-info { background: rgba(59, 130, 246, 0.15) !important; color: #93C5FD !important; border-color: rgba(59, 130, 246, 0.3) !important; }
        .badge-purple { background: rgba(139, 92, 246, 0.15) !important; color: #C4B5FD !important; border-color: rgba(139, 92, 246, 0.3) !important; }
        .badge-emerald { background: rgba(16, 185, 129, 0.15) !important; color: #6EE7B7 !important; border-color: rgba(16, 185, 129, 0.3) !important; }
        .badge-amber { background: rgba(245, 158, 11, 0.15) !important; color: #FCD34D !important; border-color: rgba(245, 158, 11, 0.3) !important; }

        .alert-success { background: rgba(16, 185, 129, 0.12) !important; border-color: rgba(16, 185, 129, 0.35) !important; }
        .alert-error { background: rgba(239, 68, 68, 0.12) !important; border-color: rgba(239, 68, 68, 0.35) !important; }
        .alert-title { color: #F8FAFC !important; }
        .alert-message { color: #CBD5E1 !important; }

        [data-testid="stFileUploader"] section {
            background-color: #111827 !important;
            border-color: #374151 !important;
        }

        [data-testid="stFileUploader"] section span, [data-testid="stFileUploader"] section small {
            color: #94A3B8 !important;
        }

        .stButton button {
            background-color: #1E293B !important;
            color: #F1F5F9 !important;
            border: 1px solid #334155 !important;
        }
        .stButton button:hover {
            background-color: #334155 !important;
            border-color: #475569 !important;
            color: #FFFFFF !important;
        }

        [data-baseweb="tab-list"] {
            border-bottom-color: #1F2937 !important;
        }
        [data-baseweb="tab"] {
            color: #94A3B8 !important;
        }
        [data-baseweb="tab"][aria-selected="true"] {
            color: #60A5FA !important;
            border-bottom-color: #3B82F6 !important;
        }
        """
        st.markdown(f"<style>{dark_css}</style>", unsafe_allow_html=True)


# Firebase Configuration Defaults
DEFAULT_FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", "AIzaSyBHUSbQNWdUGfpRi1UrUeiffQBM8Zdp4RM"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "data-studio-analyst-79a.firebaseapp.com"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", "data-studio-analyst-79a"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "data-studio-analyst-79a.firebasestorage.app"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", "967565747127"),
    "appId": os.getenv("FIREBASE_APP_ID", "1:967565747127:web:0c7ddd5fda681d7d57fe32"),
}


def get_firebase_config() -> dict:
    """Retrieve Firebase config dictionary from session, secrets, or defaults."""
    if "firebase_config" in st.session_state and st.session_state.firebase_config:
        return st.session_state.firebase_config
    if hasattr(st, "secrets") and "firebase" in st.secrets:
        return dict(st.secrets["firebase"])
    return DEFAULT_FIREBASE_CONFIG


def login_user(user_data: dict):
    """Log in user with profile information."""
    st.session_state.is_authenticated = True
    st.session_state.user_info = user_data
    if "current_page" not in st.session_state or not st.session_state.current_page:
        st.session_state.current_page = NAV_OVERVIEW


def logout_user():
    """Log out current user and clear auth state."""
    st.session_state.is_authenticated = False
    st.session_state.user_info = None


def init_session_state():
    """Initialize Streamlit session state defaults."""
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False

    if "user_info" not in st.session_state:
        st.session_state.user_info = None

    if "firebase_config" not in st.session_state:
        st.session_state.firebase_config = DEFAULT_FIREBASE_CONFIG.copy()

    if "current_page" not in st.session_state:
        st.session_state.current_page = NAV_OVERVIEW

    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None

    if "dataset_loaded" not in st.session_state:
        st.session_state.dataset_loaded = False

    if "df" not in st.session_state:
        st.session_state.df = None

    # Dual dataset state architecture
    if "original_df" not in st.session_state:
        st.session_state.original_df = None

    if "working_df" not in st.session_state:
        st.session_state.working_df = None

    if "transformation_history" not in st.session_state:
        st.session_state.transformation_history = []

    if "undo_stack" not in st.session_state:
        st.session_state.undo_stack = []

    if "redo_stack" not in st.session_state:
        st.session_state.redo_stack = []

    if "active_filters" not in st.session_state:
        st.session_state.active_filters = []

    if "has_unsaved_changes" not in st.session_state:
        st.session_state.has_unsaved_changes = False

    if "file_size_bytes" not in st.session_state:
        st.session_state.file_size_bytes = None

    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []


def add_activity_log(icon: str, action: str, detail: str):
    """Record an action in the session activity log."""
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []
    
    # Avoid exact duplicate consecutive logs
    new_entry = {"icon": icon, "action": action, "detail": detail}
    if st.session_state.activity_log and st.session_state.activity_log[0] == new_entry:
        return
    st.session_state.activity_log.insert(0, new_entry)
    # Keep only the last 8 events
    st.session_state.activity_log = st.session_state.activity_log[:8]


def reset_dataset_state():
    """Reset dataset-related session state keys."""
    st.session_state.df = None
    st.session_state.original_df = None
    st.session_state.working_df = None
    st.session_state.uploaded_file_name = None
    st.session_state.dataset_loaded = False
    st.session_state.file_size_bytes = None
    st.session_state.transformation_history = []
    st.session_state.undo_stack = []
    st.session_state.redo_stack = []
    st.session_state.active_filters = []
    st.session_state.has_unsaved_changes = False

