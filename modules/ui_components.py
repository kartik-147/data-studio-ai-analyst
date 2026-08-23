"""
Reusable UI Components for Data Studio
Linear / Notion / Mixpanel Polish:
- Crisp vector iconography (Lucide SVGs)
- Robust render_html without markdown code-block bugs
- Comprehensive EDA Workspace Tabs
"""

import os
import streamlit as st
import pandas as pd
import modules.config as config
from modules.config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    APP_ICON,
    NAV_OPTIONS,
    NAV_ICONS,
    NAV_OVERVIEW,
    NAV_DATASET,
    NAV_AI_ANALYST,
    NAV_DASHBOARD,
    NAV_SETTINGS,
    SAMPLE_DATA_DIR,
    reset_dataset_state,
    get_firebase_config,
    add_activity_log,
)
from modules.icons import icon_svg, icon_with_text
from modules.data_loader import (
    load_dataset,
    get_dataset_summary,
    get_data_quality_report,
    query_dataframe_with_pandas,
)
from modules.data_quality import render_data_quality_section
from modules.auth import (
    get_current_user,
    render_account_sidebar_widget,
)
from modules.eda_tools import (
    render_correlation_heatmap,
    render_distribution_plots,
    render_outlier_detection,
    render_column_deep_dive,
    render_skewness_kurtosis_table,
    render_pivot_table_builder,
    render_filter_query_builder,
    render_target_comparison_analysis,
    render_export_report_section,
)

# Safe fallback
NAV_VISUALIZATION = getattr(config, "NAV_VISUALIZATION", "Visualization")


def render_html(html_str: str):
    """Render HTML safely without Markdown treating indented lines as code blocks."""
    lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    cleaned = "".join(lines)
    st.markdown(cleaned, unsafe_allow_html=True)


def render_theme_toggle_button(key_suffix: str = "sidebar"):
    """Reusable theme switcher button with vector icon."""
    current_theme = st.session_state.get("theme", "light")
    is_dark = current_theme == "dark"
    theme_btn_label = "Light Mode" if is_dark else "Dark Mode"
    
    if st.button(theme_btn_label, key=f"theme_toggle_btn_{key_suffix}", use_container_width=True):
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()


def render_top_action_bar(key_suffix: str = "main"):
    """Render top right bar with theme switcher and user profile badge."""
    top_col, auth_col, theme_col = st.columns([3.8, 1.8, 1.4])
    
    user = get_current_user()
    with auth_col:
        if user:
            name = user.get("name", "User")
            render_html(
                f"""
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; height: 100%; padding-top: 4px;">
                    <div style="width: 26px; height: 26px; border-radius: 50%; background: #2563EB; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px;">{name[0].upper()}</div>
                    <span style="font-size: 0.82rem; font-weight: 600; color: var(--text-color, inherit);">{name}</span>
                </div>
                """
            )
        else:
            if st.button("Sign In", key=f"top_bar_auth_{key_suffix}", use_container_width=True):
                from modules.config import logout_user
                logout_user()
                st.rerun()
            
    with theme_col:
        render_theme_toggle_button(key_suffix=f"top_{key_suffix}")


def render_sidebar():
    """Renders the consistent, unified navigation sidebar."""
    with st.sidebar:
        # App Logo & Branding Header
        render_html(
            f"""
            <div class="sidebar-brand-container">
                <div class="sidebar-logo-icon">{icon_svg("activity", size=18, color="#2563EB")}</div>
                <div>
                    <h2 class="sidebar-app-name">{APP_NAME}</h2>
                    <p class="sidebar-app-tagline">{APP_TAGLINE}</p>
                </div>
            </div>
            """
        )

        render_html("<div class='sidebar-divider'></div>")

        # Account / Google Auth Section
        render_html("<p class='nav-section-title'>ACCOUNT</p>")
        render_account_sidebar_widget()

        render_html("<div class='sidebar-divider'></div>")

        # Quick Theme Switcher Button
        render_html("<p class='nav-section-title'>APPEARANCE</p>")
        render_theme_toggle_button(key_suffix="sidebar_top")

        render_html("<div class='sidebar-divider'></div>")

        # Navigation Menu
        render_html("<p class='nav-section-title'>NAVIGATION</p>")

        current_index = 0
        if st.session_state.current_page in NAV_OPTIONS:
            current_index = NAV_OPTIONS.index(st.session_state.current_page)

        selected_page = st.radio(
            label="Main Navigation",
            options=NAV_OPTIONS,
            index=current_index,
            label_visibility="collapsed",
            key="nav_selection_radio",
        )

        st.session_state.current_page = selected_page

        render_html("<div class='sidebar-divider'></div>")

        # Workspace Status Card
        dataset_name = st.session_state.uploaded_file_name if st.session_state.uploaded_file_name else "None"
        render_html(
            f"""
            <div class="sidebar-status-card">
                <div class="status-card-header">
                    <span class="status-indicator"></span>
                    <span class="status-title">Workspace</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Dataset:</span>
                    <span class="status-value" title="{dataset_name}">{dataset_name}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Mode:</span>
                    <span class="status-value">Local</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Version:</span>
                    <span class="status-value">v{APP_VERSION}</span>
                </div>
            </div>
            """
        )

        render_html(
            """
            <div class="sidebar-footer">
                <span>Data Studio &bull; Local Workspace</span>
            </div>
            """
        )


def render_overview_page():
    """Render the intelligent, dynamic Overview page."""
    from modules.overview import render_overview_page as _render_overview
    _render_overview()


def render_dataset_page():
    """Render the comprehensive Dataset Management and Standard EDA Workspace."""
    render_top_action_bar(key_suffix="dataset")

    # 1. Header Banner
    render_html(
        """
        <div class="page-header-container">
            <div class="page-header-badge">Dataset Workspace</div>
            <h1 class="page-header-title">Exploratory Data Analysis Toolkit</h1>
            <p class="page-header-subtitle">
                Schema profiling, correlation heatmaps, distribution grids, outlier detection, pivot aggregation, and AI querying.
            </p>
        </div>
        """
    )

    # 2. File Upload Section
    st.markdown("#### Upload Dataset")
    uploaded_file = st.file_uploader(
        label="Upload CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Supports .csv, .xlsx, and .xls formats.",
        key="dataset_file_uploader",
    )

    if uploaded_file is not None:
        last_name = st.session_state.get("uploaded_file_name")
        if last_name != uploaded_file.name or st.session_state.get("df") is None:
            with st.spinner(f"Loading '{uploaded_file.name}'..."):
                df, error = load_dataset(uploaded_file)
                if error:
                    st.session_state.last_upload_error = error
                    reset_dataset_state()
                else:
                    st.session_state.df = df.copy(deep=True)
                    st.session_state.original_df = df.copy(deep=True)
                    st.session_state.working_df = df.copy(deep=True)
                    st.session_state.transformation_history = []
                    st.session_state.undo_stack = []
                    st.session_state.redo_stack = []
                    st.session_state.active_filters = []
                    st.session_state.has_unsaved_changes = False
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.dataset_loaded = True
                    st.session_state.file_size_bytes = getattr(uploaded_file, "size", None)
                    st.session_state.last_upload_error = None
                    add_activity_log("database", "Uploaded dataset", uploaded_file.name)
                    st.rerun()

    if st.session_state.get("last_upload_error"):
        render_html(
            f"""
            <div class="alert-banner alert-error">
                <div class="alert-icon">{icon_svg("alert-triangle", size=18, color="#EF4444")}</div>
                <div class="alert-content">
                    <div class="alert-title">Load Error</div>
                    <div class="alert-message">{st.session_state.last_upload_error}</div>
                </div>
            </div>
            """
        )

    # 3. Active Dataset Workspace
    if st.session_state.get("dataset_loaded") and st.session_state.get("df") is not None:
        df = st.session_state.df
        filename = st.session_state.uploaded_file_name
        file_size_bytes = st.session_state.get("file_size_bytes", 0)
        
        summary = get_dataset_summary(df)
        quality_report = get_data_quality_report(df)
        
        total_rows = summary["total_rows"]
        total_cols = summary["total_columns"]
        mem_mb = summary["memory_usage_mb"]
        null_cells = summary["null_cells"]
        null_pct = summary["null_percentage"]
        duplicate_rows = summary["duplicate_rows"]
        duplicate_pct = round((duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 0.0
        num_cols = summary["numeric_columns"]
        cat_cols = summary["categorical_columns"]

        file_ext = filename.split(".")[-1].upper() if "." in filename else "FILE"
        file_size_str = f"{file_size_bytes / 1024:.1f} KB" if file_size_bytes and file_size_bytes < 1024 * 1024 else f"{file_size_bytes / (1024*1024):.2f} MB" if file_size_bytes else f"{mem_mb:.2f} MB"

        # Active Dataset Status Bar
        status_col, clear_col = st.columns([4, 1])
        with status_col:
            render_html(
                f"""
                <div class="alert-banner alert-success" style="margin-bottom: 0.8rem;">
                    <div class="alert-icon">{icon_svg("database", size=18, color="#059669")}</div>
                    <div class="alert-content">
                        <div class="alert-title">Active File: <strong>{filename}</strong> <span class="badge badge-info" style="margin-left: 6px;">{file_ext}</span> <span class="badge badge-purple">{file_size_str}</span></div>
                        <div class="alert-message">
                            <strong>{total_rows:,}</strong> rows &bull; <strong>{total_cols}</strong> columns &bull; <strong>{len(num_cols)}</strong> numeric &bull; <strong>{len(cat_cols)}</strong> categorical &bull; <strong>{duplicate_rows:,}</strong> duplicates ({duplicate_pct}%)
                        </div>
                    </div>
                </div>
                """
            )
        with clear_col:
            st.write("")
            if st.button("Clear Dataset", key="clear_active_dataset_btn", use_container_width=True):
                reset_dataset_state()
                st.session_state.last_upload_error = None
                st.rerun()

        st.write("")

        # 8 Clean EDA Workspace Tabs
        tab_overview, tab_preview, tab_relationships, tab_distributions, tab_deepdive, tab_pivot, tab_ai, tab_export = st.tabs([
            "Overview & Stats",
            "Data Preview & Filter",
            "Correlation & Target",
            "Distributions & Outliers",
            "Column Inspector",
            "Pivot & Aggregation",
            "AI Analyst",
            "Export Report",
        ])

        # -------------------------------------------------------------
        # TAB 1: OVERVIEW & STATISTICAL INDICATORS
        # -------------------------------------------------------------
        with tab_overview:
            st.markdown("#### Key Dataset Metrics")
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

            with kpi_col1:
                render_html(
                    f"""
                    <div class="dataset-kpi-card blue-kpi">
                        <div class="dataset-kpi-lbl">{icon_svg("table", size=12)} Total Rows</div>
                        <div class="dataset-kpi-val">{total_rows:,}</div>
                        <div class="dataset-kpi-badge"><span class="badge badge-info">Records</span></div>
                    </div>
                    """
                )

            with kpi_col2:
                render_html(
                    f"""
                    <div class="dataset-kpi-card emerald-kpi">
                        <div class="dataset-kpi-lbl">{icon_svg("layers", size=12)} Columns</div>
                        <div class="dataset-kpi-val">{total_cols:,}</div>
                        <div class="dataset-kpi-badge"><span class="badge badge-emerald">{len(num_cols)} Num / {len(cat_cols)} Cat</span></div>
                    </div>
                    """
                )

            with kpi_col3:
                render_html(
                    f"""
                    <div class="dataset-kpi-card purple-kpi">
                        <div class="dataset-kpi-lbl">{icon_svg("alert-triangle", size=12)} Missing Values</div>
                        <div class="dataset-kpi-val">{null_cells:,} <span style="font-size: 0.8rem; font-weight: 500; color: #94A3B8;">({null_pct}%)</span></div>
                        <div class="dataset-kpi-badge"><span class="badge badge-purple">Null Rate</span></div>
                    </div>
                    """
                )

            with kpi_col4:
                render_html(
                    f"""
                    <div class="dataset-kpi-card amber-kpi">
                        <div class="dataset-kpi-lbl">{icon_svg("copy", size=12)} Duplicate Rows</div>
                        <div class="dataset-kpi-val">{duplicate_rows:,} <span style="font-size: 0.8rem; font-weight: 500; color: #94A3B8;">({duplicate_pct}%)</span></div>
                        <div class="dataset-kpi-badge"><span class="badge badge-amber">{mem_mb:.2f} MB RAM</span></div>
                    </div>
                    """
                )

            st.write("")
            render_html("<div class='section-divider'></div>")
            
            st.markdown("#### Comprehensive Numeric Statistics (with Skewness & Kurtosis)")
            render_skewness_kurtosis_table(df)

            if cat_cols:
                st.write("")
                st.markdown("#### Categorical Columns Distribution")
                cat_summary = []
                for c in cat_cols:
                    u_count = df[c].nunique(dropna=False)
                    mode_val = df[c].mode()[0] if not df[c].empty else "-"
                    top_freq = int((df[c] == mode_val).sum()) if not df[c].empty else 0
                    top_freq_pct = round((top_freq / total_rows * 100), 1) if total_rows > 0 else 0
                    cat_summary.append({
                        "Column": c,
                        "Unique Values": u_count,
                        "Top Frequent Value": str(mode_val)[:30],
                        "Top Frequency": f"{top_freq:,} ({top_freq_pct}%)",
                    })
                st.dataframe(pd.DataFrame(cat_summary), use_container_width=True, hide_index=True)

        # -------------------------------------------------------------
        # TAB 2: DATA PREVIEW & VISUAL FILTER BUILDER
        # -------------------------------------------------------------
        with tab_preview:
            st.markdown("#### Visual Filter Builder")
            render_filter_query_builder(df)

        # -------------------------------------------------------------
        # TAB 3: CORRELATION & TARGET COMPARISON ANALYSIS
        # -------------------------------------------------------------
        with tab_relationships:
            sub1, sub2 = st.tabs(["Correlation Heatmap", "Target / Feature Relationship"])
            with sub1:
                render_correlation_heatmap(df)
            with sub2:
                render_target_comparison_analysis(df)

        # -------------------------------------------------------------
        # TAB 4: DISTRIBUTIONS & OUTLIER DETECTION
        # -------------------------------------------------------------
        with tab_distributions:
            d_sub1, d_sub2 = st.tabs(["Distribution Grids", "Outlier Detection (IQR & Z-Score)"])
            with d_sub1:
                render_distribution_plots(df)
            with d_sub2:
                render_outlier_detection(df)

        # -------------------------------------------------------------
        # TAB 5: COLUMN DEEP-DIVE INSPECTOR
        # -------------------------------------------------------------
        with tab_deepdive:
            st.markdown("#### Column Deep-Dive Inspector")
            render_column_deep_dive(df)

        # -------------------------------------------------------------
        # TAB 6: PIVOT TABLE & GROUP-BY BUILDER
        # -------------------------------------------------------------
        with tab_pivot:
            st.markdown("#### Pivot Table & Multi-Column Aggregator")
            render_pivot_table_builder(df)

        # -------------------------------------------------------------
        # TAB 7: AI ANALYST
        # -------------------------------------------------------------
        with tab_ai:
            render_ai_query_workspace(df)

        # -------------------------------------------------------------
        # TAB 8: EXPORT REPORT
        # -------------------------------------------------------------
        with tab_export:
            render_export_report_section(df, filename)

    elif not st.session_state.get("last_upload_error"):
        render_html(
            f"""
            <div class="empty-upload-card">
                <div class="empty-upload-icon">{icon_svg("upload-cloud", size=24, color="#2563EB")}</div>
                <div class="empty-upload-title">No Dataset Loaded</div>
                <div class="empty-upload-desc">
                    Upload a CSV or Excel file above, or load one of the sample datasets to begin exploration.
                </div>
                <div class="empty-upload-specs">
                    <div class="spec-chip">CSV (.csv)</div>
                    <div class="spec-chip">Excel (.xlsx, .xls)</div>
                </div>
            </div>
            """
        )

        st.write("")
        sample_col1, sample_col2, _ = st.columns([1.5, 1.5, 3])
        with sample_col1:
            if st.button("Load customer_demographics.csv", key="load_empty_csv_btn", use_container_width=True):
                sample_path = os.path.join(SAMPLE_DATA_DIR, "customer_demographics.csv")
                if os.path.exists(sample_path):
                    df, err = load_dataset(sample_path)
                    if not err and df is not None:
                        st.session_state.df = df.copy(deep=True)
                        st.session_state.original_df = df.copy(deep=True)
                        st.session_state.working_df = df.copy(deep=True)
                        st.session_state.transformation_history = []
                        st.session_state.undo_stack = []
                        st.session_state.redo_stack = []
                        st.session_state.active_filters = []
                        st.session_state.has_unsaved_changes = False
                        st.session_state.uploaded_file_name = "customer_demographics.csv"
                        st.session_state.dataset_loaded = True
                        st.session_state.file_size_bytes = os.path.getsize(sample_path)
                        st.session_state.last_upload_error = None
                        st.rerun()

        with sample_col2:
            if st.button("Load quarterly_financial_report.xlsx", key="load_empty_xlsx_btn", use_container_width=True):
                sample_path = os.path.join(SAMPLE_DATA_DIR, "quarterly_financial_report.xlsx")
                if os.path.exists(sample_path):
                    df, err = load_dataset(sample_path)
                    if not err and df is not None:
                        st.session_state.df = df.copy(deep=True)
                        st.session_state.original_df = df.copy(deep=True)
                        st.session_state.working_df = df.copy(deep=True)
                        st.session_state.transformation_history = []
                        st.session_state.undo_stack = []
                        st.session_state.redo_stack = []
                        st.session_state.active_filters = []
                        st.session_state.has_unsaved_changes = False
                        st.session_state.uploaded_file_name = "quarterly_financial_report.xlsx"
                        st.session_state.dataset_loaded = True
                        st.session_state.file_size_bytes = os.path.getsize(sample_path)
                        st.session_state.last_upload_error = None
                        st.rerun()


def render_ai_query_workspace(df: pd.DataFrame):
    """Render interactive AI Tabular Query & Analysis Workspace."""
    st.markdown("#### AI Tabular Query Workspace")
    st.caption("Ask questions, generate automated insights, or select from pre-built analytical operations:")

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # 1-Click Quick Query Recommendation Chips
    st.markdown("##### Quick Analytical Prompts")
    q_col1, q_col2, q_col3 = st.columns(3)
    
    selected_query_action = None
    with q_col1:
        if st.button("Numerical Distribution Summary", key="ai_q_describe_btn", use_container_width=True):
            selected_query_action = ("numerical_describe", None, 5)
        if st.button("Column Correlation Matrix", key="ai_q_corr_btn", use_container_width=True):
            selected_query_action = ("correlation", None, 5)

    with q_col2:
        top_num = num_cols[0] if num_cols else None
        if top_num and st.button(f"Top 5 Rows by '{top_num}'", key="ai_q_top_btn", use_container_width=True):
            selected_query_action = ("top_records", top_num, 5)
        if st.button("Missing Value Audit", key="ai_q_missing_btn", use_container_width=True):
            selected_query_action = ("missing_summary", None, 5)

    with q_col3:
        top_cat = cat_cols[0] if cat_cols else None
        if top_cat and st.button(f"Frequency Counts for '{top_cat}'", key="ai_q_cat_btn", use_container_width=True):
            selected_query_action = ("group_counts", top_cat, 5)
        if top_num and st.button(f"Lowest 5 Rows by '{top_num}'", key="ai_q_bottom_btn", use_container_width=True):
            selected_query_action = ("bottom_records", top_num, 5)

    st.write("")
    
    query_input = st.text_input(
        "Or ask a question about your dataset in natural language:",
        placeholder="e.g. show correlation, describe numerical columns, top 10 rows, etc.",
        key="ai_analyst_custom_input",
    )
    
    run_btn = st.button("Run AI Analysis", key="run_ai_analyst_btn")

    if run_btn and query_input.strip():
        q_lower = query_input.strip().lower()
        if "corr" in q_lower:
            selected_query_action = ("correlation", None, 5)
        elif "missing" in q_lower or "null" in q_lower:
            selected_query_action = ("missing_summary", None, 5)
        elif "describe" in q_lower or "distribut" in q_lower or "stats" in q_lower:
            selected_query_action = ("numerical_describe", None, 5)
        elif "top" in q_lower or "highest" in q_lower or "max" in q_lower:
            matched_col = next((c for c in num_cols if c.lower() in q_lower), (num_cols[0] if num_cols else None))
            selected_query_action = ("top_records", matched_col, 10 if "10" in q_lower else 5)
        elif "bottom" in q_lower or "lowest" in q_lower or "min" in q_lower:
            matched_col = next((c for c in num_cols if c.lower() in q_lower), (num_cols[0] if num_cols else None))
            selected_query_action = ("bottom_records", matched_col, 10 if "10" in q_lower else 5)
        elif "group" in q_lower or "count" in q_lower or "frequen" in q_lower:
            matched_col = next((c for c in cat_cols if c.lower() in q_lower), (cat_cols[0] if cat_cols else None))
            selected_query_action = ("group_counts", matched_col, 10)
        else:
            selected_query_action = ("numerical_describe", None, 5)

    if selected_query_action:
        q_type, col_arg, n_arg = selected_query_action
        with st.spinner("Analyzing dataset..."):
            res_df, code_str = query_dataframe_with_pandas(df, q_type, col_name=col_arg, top_n=n_arg)
            
            render_html("<div class='section-divider'></div>")
            st.markdown("##### Analysis Results")
            
            st.code(code_str, language="python")
            
            if res_df is not None and isinstance(res_df, pd.DataFrame):
                st.dataframe(res_df, use_container_width=True)
                
                csv_bytes = res_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Export Query Result as CSV",
                    data=csv_bytes,
                    file_name="ai_analysis_result.csv",
                    mime="text/csv",
                    key="ai_download_result_btn",
                )
            elif res_df is not None:
                st.write(res_df)
            else:
                st.warning(code_str)


def render_coming_soon_page(page_name: str, icon_name: str, description: str, upcoming_features: list):
    """Render a clean placeholder state for in-progress modules."""
    render_top_action_bar(key_suffix=f"coming_soon_{page_name.lower().replace(' ', '_')}")

    render_html(
        f"""
        <div class="coming-soon-container">
            <div class="coming-soon-icon">{icon_svg(icon_name, size=28, color="#2563EB")}</div>
            <div class="coming-soon-badge">In Development</div>
            <h2 class="coming-soon-title">{page_name}</h2>
            <p class="coming-soon-desc">{description}</p>
        </div>
        """
    )

    st.markdown("#### Planned Features")
    for feat in upcoming_features:
        render_html(
            f"""
            <div class="roadmap-item">
                <span class="roadmap-bullet">&bull;</span>
                <span class="roadmap-text">{feat}</span>
            </div>
            """
        )


def render_settings_page():
    """Render Settings, Theme, and Firebase Auth Configuration page."""
    render_top_action_bar(key_suffix="settings")

    render_html(
        """
        <div class="page-header-container">
            <div class="page-header-badge">Configuration</div>
            <h1 class="page-header-title">Settings</h1>
            <p class="page-header-subtitle">
                Manage account credentials, Firebase Auth, theme appearance, and workspace defaults.
            </p>
        </div>
        """
    )

    # 1. User Account & Security
    st.markdown("#### User Account & Security")
    user = get_current_user()
    
    auth_col1, auth_col2 = st.columns([2, 1])
    with auth_col1:
        if user:
            name = user.get("name", "User")
            email = user.get("email", "")
            uid = user.get("uid", "")
            photo_url = user.get("photo_url", "")
            provider = user.get("provider", "password")
            created_at = user.get("created_at", "")[:10] if user.get("created_at") else "Today"
            total_logins = user.get("total_logins", 1)
            
            badge_color = "#4285F4" if "google" in provider else ("#8B5CF6" if provider == "guest" else "#10B981")
            provider_label = "Google Verified" if "google" in provider else ("Guest Demo" if provider == "guest" else "Email Verified")
            
            avatar_html = f'<img src="{photo_url}" style="width: 44px; height: 44px; border-radius: 50%; border: 2px solid {badge_color};" />' if photo_url else f'<div style="width: 44px; height: 44px; border-radius: 50%; background: {badge_color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px;">{name[0].upper()}</div>'
            render_html(
                f"""
                <div class="feature-card" style="margin-bottom: 0.8rem; border-left: 3px solid {badge_color};">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        {avatar_html}
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 1.05rem; font-weight: 700; color: var(--text-color, inherit);">{name}</span>
                                <span style="background: {badge_color}22; color: {badge_color}; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600;">{provider_label}</span>
                            </div>
                            <div style="font-size: 0.84rem; color: #94A3B8; margin-top: 2px;">{email}</div>
                            <div style="display: flex; gap: 16px; margin-top: 6px; font-size: 0.72rem; color: #64748B; font-family: var(--font-mono);">
                                <span>Member Since: {created_at}</span>
                                <span>Total Sessions: {total_logins}</span>
                                <span>UID: {uid}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            )
        else:
            render_html(
                """
                <div class="feature-card" style="margin-bottom: 0.8rem;">
                    <div class="feature-title">Not Authenticated</div>
                    <p class="feature-desc">Sign in with your Google account or Email to secure your workspace.</p>
                </div>
                """
            )
            
    with auth_col2:
        st.write("")
        if user:
            from modules.auth import perform_sign_out
            if st.button("Sign Out Account", key="settings_signout_btn", use_container_width=True):
                perform_sign_out()
        else:
            if st.button("Go to Login", key="settings_goto_login_btn", use_container_width=True):
                from modules.config import logout_user
                logout_user()
                st.rerun()

    # User Persistent Activity History
    if user and user.get("email"):
        from modules.auth import get_user_history
        user_hist = get_user_history(user.get("email", ""))
        if user_hist:
            with st.expander(f"Account Activity History ({len(user_hist)} events)", expanded=False):
                st.caption("Audit trail of actions, dataset uploads, cleanings, and chart sessions.")
                for item in user_hist[:10]:
                    act = item.get("action", "Event")
                    det = item.get("detail", "")
                    tstamp = item.get("timestamp", "")
                    st.markdown(f"- **{act}** (`{tstamp}`): {det}")

    # Firebase Configuration Expander
    with st.expander("Firebase Project Configuration", expanded=False):
        st.caption("Customize your live Firebase Web App configuration keys (optional).")
        fb_config = get_firebase_config()
        
        cfg_col1, cfg_col2 = st.columns(2)
        with cfg_col1:
            api_key_val = st.text_input("API Key (apiKey)", value=fb_config.get("apiKey", ""), key="cfg_api_key")
            auth_domain_val = st.text_input("Auth Domain (authDomain)", value=fb_config.get("authDomain", ""), key="cfg_auth_domain")
            proj_id_val = st.text_input("Project ID (projectId)", value=fb_config.get("projectId", ""), key="cfg_proj_id")
        with cfg_col2:
            storage_val = st.text_input("Storage Bucket (storageBucket)", value=fb_config.get("storageBucket", ""), key="cfg_storage")
            app_id_val = st.text_input("App ID (appId)", value=fb_config.get("appId", ""), key="cfg_app_id")
            sender_id_val = st.text_input("Sender ID (messagingSenderId)", value=fb_config.get("messagingSenderId", ""), key="cfg_sender_id")

        if st.button("Save Firebase Configuration", key="save_fb_config_btn"):
            st.session_state.firebase_config = {
                "apiKey": api_key_val,
                "authDomain": auth_domain_val,
                "projectId": proj_id_val,
                "storageBucket": storage_val,
                "appId": app_id_val,
                "messagingSenderId": sender_id_val,
            }
            st.success("Firebase configuration saved in session!")
            st.rerun()

    st.write("")
    render_html("<div class='section-divider'></div>")

    # 2. Appearance
    st.markdown("#### Interface Appearance")
    current_theme = st.session_state.get("theme", "light")
    is_dark = current_theme == "dark"

    theme_col1, theme_col2 = st.columns([2, 1])
    with theme_col1:
        render_html(
            f"""
            <div class="feature-card" style="margin-bottom: 1rem;">
                <div class="feature-title">Current Theme: <strong>{'Dark Mode' if is_dark else 'Light Mode'}</strong></div>
                <p class="feature-desc">
                    Switch between crisp light theme and obsidian dark theme across the entire workbench.
                </p>
            </div>
            """
        )
    
    with theme_col2:
        st.write("")
        btn_text = "Switch to Light Mode" if is_dark else "Switch to Dark Mode"
        if st.button(btn_text, key="settings_page_theme_toggle_btn", use_container_width=True):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

    st.write("")
    render_html("<div class='section-divider'></div>")

    # 3. Defaults & Maintenance
    st.markdown("#### Workspace Maintenance")
    reset_col1, reset_col2 = st.columns([2, 1])
    with reset_col1:
        st.caption("Clear active dataset, loaded memory cache, and reset workspace state.")
    with reset_col2:
        if st.button("Clear Workspace Cache", key="settings_clear_cache_btn", use_container_width=True):
            reset_dataset_state()
            st.session_state.last_upload_error = None
            st.rerun()


def render_footer():
    """Render application bottom footer."""
    render_html(
        f"""
        <div class="app-footer">
            <p><strong>{APP_NAME}</strong> &bull; v{APP_VERSION} &bull; Local Workspace</p>
        </div>
        """
    )
