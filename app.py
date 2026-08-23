"""
Data Studio - Main Application Entry Point
"""

import streamlit as st

from modules.config import (
    APP_NAME,
    APP_ICON,
    NAV_OVERVIEW,
    NAV_DATASET,
    NAV_DATA_PREPARATION,
    NAV_AI_ANALYST,
    NAV_VISUALIZATION,
    NAV_DASHBOARD,
    NAV_SETTINGS,
    load_custom_css,
    init_session_state,
)

from modules.ui_components import (
    render_sidebar,
    render_top_action_bar,
    render_overview_page,
    render_dataset_page,
    render_ai_query_workspace,
    render_coming_soon_page,
    render_settings_page,
    render_footer,
)
from modules.auth import handle_auth_callback, render_session_persistence_checker
from modules.login_page import render_login_page
from modules.visualization import render_visualization_page
from modules.data_prep import render_data_prep_page

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title=f"{APP_NAME} - EDA Workbench",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Initialize Session State & Inject Custom Styles
init_session_state()
handle_auth_callback()
render_session_persistence_checker()
load_custom_css()

# 3. Authentication Check
is_authenticated = st.session_state.get("is_authenticated", False)

if not is_authenticated:
    # Render Dedicated Clean Login Page
    render_login_page()
else:
    # 4. Render Navigation Sidebar for Authenticated Users
    render_sidebar()

    # 5. Main Page Routing Logic
    current_page = st.session_state.current_page

    if current_page == NAV_OVERVIEW:
        render_overview_page()

    elif current_page == NAV_DATASET:
        render_dataset_page()

    elif current_page == NAV_DATA_PREPARATION:
        render_data_prep_page()

    elif current_page == NAV_AI_ANALYST:
        render_top_action_bar(key_suffix="ai_analyst_page")
        st.markdown(
            """
            <div class="page-header-container">
                <div class="page-header-badge">AI Assistant</div>
                <h1 class="page-header-title">AI Query Workspace</h1>
                <p class="page-header-subtitle">
                    Ask questions, filter subsets, and run automated data exploration with AI.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.get("dataset_loaded") and st.session_state.get("df") is not None:
            render_ai_query_workspace(st.session_state.df)
        else:
            st.info("Please upload a CSV or Excel file on the **Dataset Explorer** page to query it with AI.")
            if st.button("Go to Dataset Workspace", key="nav_to_dataset_from_ai_btn"):
                st.session_state.current_page = NAV_DATASET
                st.rerun()

    elif current_page in (NAV_VISUALIZATION, NAV_DASHBOARD, "Visualization", "Dashboard"):
        render_visualization_page()

    elif current_page == NAV_SETTINGS:
        render_settings_page()

    # 6. Render Footer
    render_footer()
