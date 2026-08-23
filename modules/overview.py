"""
Overview Module for Data Studio
- Intelligent Dashboard with Dataset at a Glance
- Dynamic Automated Quick Insights for Any Dataset
- Comprehensive Data Quality Scoring
- Dataset Summary & File Specifications
- Recommended Smart Next Actions
- Recent User Activity Log
- Clean Empty State for Upload Guidance
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
from modules.config import (
    NAV_DATASET,
    NAV_AI_ANALYST,
    NAV_VISUALIZATION,
    SAMPLE_DATA_DIR,
)
from modules.data_loader import load_dataset
from modules.ui_components import render_top_action_bar, render_html
from modules.icons import icon_svg, icon_with_text

try:
    from modules.config import add_activity_log
except ImportError:
    def add_activity_log(icon: str, action: str, detail: str):
        if "activity_log" not in st.session_state:
            st.session_state.activity_log = []
        new_entry = {"icon": icon, "action": action, "detail": detail}
        if st.session_state.activity_log and st.session_state.activity_log[0] == new_entry:
            return
        st.session_state.activity_log.insert(0, new_entry)
        st.session_state.activity_log = st.session_state.activity_log[:8]


def format_bytes(size_bytes: float) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if size_bytes is None or size_bytes <= 0:
        return "N/A"
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def calculate_data_quality_score(df: pd.DataFrame) -> dict:
    """
    Calculate comprehensive data quality score (0 to 100).
    Factors:
    - Missing cell ratio (up to -40 pts)
    - Duplicate rows ratio (up to -30 pts)
    - Empty/constant column penalties (up to -20 pts)
    - Single-type column cleanliness (+ bonus / penalty)
    """
    total_rows, total_cols = df.shape
    if total_rows == 0 or total_cols == 0:
        return {
            "score": 0,
            "status": "No Data",
            "badge_class": "badge-rose",
            "color": "#EF4444",
            "missing_pct": 0.0,
            "dup_pct": 0.0,
            "factors": ["Dataset contains zero rows or columns."],
        }

    total_cells = total_rows * total_cols
    missing_cells = int(df.isna().sum().sum())
    missing_pct = (missing_cells / total_cells) * 100.0

    duplicate_rows = int(df.duplicated().sum())
    dup_pct = (duplicate_rows / total_rows) * 100.0

    # Constant columns (only 1 unique value)
    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    constant_col_pct = (len(constant_cols) / total_cols) * 100.0

    # Calculate penalties
    missing_penalty = min(40.0, missing_pct * 1.5)
    dup_penalty = min(30.0, dup_pct * 2.0)
    constant_penalty = min(15.0, constant_col_pct * 0.75)

    raw_score = 100.0 - missing_penalty - dup_penalty - constant_penalty
    score = int(max(10, min(100, round(raw_score))))

    # Quality status
    if score >= 90:
        status = "Excellent"
        badge_class = "badge-emerald"
        color = "#10B981"
    elif score >= 75:
        status = "Good"
        badge_class = "badge-info"
        color = "#2563EB"
    elif score >= 60:
        status = "Fair"
        badge_class = "badge-amber"
        color = "#F59E0B"
    else:
        status = "Needs Attention"
        badge_class = "badge-rose"
        color = "#EF4444"

    # Explanation factors
    factors = []
    if missing_pct == 0.0:
        factors.append("100% data completeness (0 missing cells)")
    else:
        factors.append(f"{missing_pct:.1f}% missing values ({missing_cells:,} empty cells)")

    if duplicate_rows == 0:
        factors.append("100% row uniqueness (0 duplicates)")
    else:
        factors.append(f"{duplicate_rows:,} duplicate rows detected ({dup_pct:.1f}%)")

    if constant_cols:
        factors.append(f"{len(constant_cols)} constant/single-value column(s)")
    else:
        factors.append("Healthy column cardinality across all fields")

    return {
        "score": score,
        "status": status,
        "badge_class": badge_class,
        "color": color,
        "missing_pct": missing_pct,
        "dup_pct": dup_pct,
        "factors": factors,
    }


def generate_quick_insights(df: pd.DataFrame) -> list:
    """
    Generate dynamic, intelligent statistical insights adapted to any dataset.
    """
    insights = []
    total_rows, total_cols = df.shape

    if total_rows == 0 or total_cols == 0:
        return ["No rows or columns available to compute insights."]

    num_df = df.select_dtypes(include=["number"])
    num_cols = num_df.columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]

    # 1. Numerical Highlight: Peak, Average & Range
    if num_cols:
        best_num_col = None
        max_std = -1.0
        for col in num_cols:
            valid_series = df[col].dropna()
            if len(valid_series) > 1:
                std = valid_series.std()
                if std > max_std:
                    max_std = std
                    best_num_col = col

        if not best_num_col:
            best_num_col = num_cols[0]

        valid_s = df[best_num_col].dropna()
        if len(valid_s) > 0:
            c_max = valid_s.max()
            c_min = valid_s.min()
            c_mean = valid_s.mean()
            fmt_max = f"{c_max:,.2f}".rstrip("0").rstrip(".") if isinstance(c_max, (float, np.floating)) else f"{c_max:,}"
            fmt_mean = f"{c_mean:,.2f}".rstrip("0").rstrip(".") if isinstance(c_mean, (float, np.floating)) else f"{c_mean:,}"
            fmt_min = f"{c_min:,.2f}".rstrip("0").rstrip(".") if isinstance(c_min, (float, np.floating)) else f"{c_min:,}"

            insights.append(
                f"<strong>Numerical Distribution:</strong> In <code>{best_num_col}</code>, values peak at <strong>{fmt_max}</strong> with an average of <strong>{fmt_mean}</strong> (min: {fmt_min})."
            )

    # 2. Categorical Distribution & Dominant Segment
    if cat_cols:
        best_cat_col = None
        for col in cat_cols:
            n_uniq = df[col].nunique()
            if 1 < n_uniq <= 50:
                best_cat_col = col
                break
        if not best_cat_col and cat_cols:
            best_cat_col = cat_cols[0]

        top_val = df[best_cat_col].mode()
        if not top_val.empty:
            mode_val = top_val.iloc[0]
            val_count = (df[best_cat_col] == mode_val).sum()
            val_pct = (val_count / total_rows) * 100.0
            insights.append(
                f"<strong>Top Category:</strong> In <code>{best_cat_col}</code>, <strong>'{mode_val}'</strong> is dominant with <strong>{val_count:,}</strong> records (<strong>{val_pct:.1f}%</strong> of total)."
            )

    # 3. Correlation / Trend Pair (if 2+ numeric columns)
    if len(num_cols) >= 2:
        try:
            corr_matrix = num_df.corr().abs()
            np.fill_diagonal(corr_matrix.values, 0)
            max_corr = corr_matrix.max().max()
            if max_corr > 0.4 and not np.isnan(max_corr):
                col_a = corr_matrix.max().idxmax()
                col_b = corr_matrix[col_a].idxmax()
                actual_corr = num_df[col_a].corr(num_df[col_b])
                direction = "positive" if actual_corr > 0 else "negative"
                insights.append(
                    f"<strong>Correlated Features:</strong> Significant {direction} correlation between <code>{col_a}</code> and <code>{col_b}</code> (Pearson <em>r</em> = <strong>{actual_corr:+.2f}</strong>)."
                )
        except Exception:
            pass

    # 4. Data Completeness & Scale Summary
    missing_sum = df.isna().sum().sum()
    if missing_sum == 0:
        insights.append(
            f"<strong>Integrity Status:</strong> Complete dataset with <strong>0 missing values</strong> across all {total_cols} columns and {total_rows:,} records."
        )
    else:
        most_missing_col = df.isna().sum().idxmax()
        most_missing_count = df[most_missing_col].isna().sum()
        most_missing_pct = (most_missing_count / total_rows) * 100.0
        insights.append(
            f"<strong>Missing Cell Concentration:</strong> <code>{most_missing_col}</code> has highest null count with <strong>{most_missing_count:,}</strong> empty cells ({most_missing_pct:.1f}%)."
        )

    if len(insights) < 4:
        memory_usage = df.memory_usage(deep=True).sum()
        insights.append(
            f"<strong>Memory Footprint:</strong> Loaded at <strong>{format_bytes(memory_usage)}</strong> spanning <strong>{len(num_cols)} numeric</strong> and <strong>{len(cat_cols)} categorical</strong> attributes."
        )

    return insights


def render_overview_page():
    """
    Render the improved, intelligent Overview page.
    Automatically displays active dataset metrics, quality score, insights,
    summary, next actions, and recent activity when a dataset is present.
    Shows a clean onboarding empty state when no dataset is loaded.
    """
    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    # Top Action Bar
    render_top_action_bar(key_suffix="overview")

    df = st.session_state.get("df")
    filename = st.session_state.get("uploaded_file_name", "Dataset")

    # =========================================================================
    # EMPTY STATE (No Dataset Uploaded)
    # =========================================================================
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        render_html(
            f"""
            <div class="page-header-container">
                <div class="page-header-badge">Overview & Workspace</div>
                <h1 class="page-header-title">Welcome to Data Studio</h1>
                <p class="page-header-subtitle">
                    Automated data profiling, intelligent insights, AI querying, and interactive visualization in one clean workspace.
                </p>
            </div>
            """
        )

        render_html(
            f"""
            <div class="empty-upload-card">
                <div class="empty-upload-icon">
                    {icon_svg("upload-cloud", size=24, color="#3B82F6" if is_dark else "#2563EB")}
                </div>
                <div class="empty-upload-title">
                    No Active Dataset Uploaded
                </div>
                <p class="empty-upload-desc">
                    Upload your CSV or Excel file to get an automated health audit, dynamic data insights, schema profiling, and interactive chart building.
                </p>
                <div class="empty-upload-specs">
                    <span class="spec-chip">.CSV</span>
                    <span class="spec-chip">.XLSX</span>
                    <span class="spec-chip">.XLS</span>
                    <span class="spec-chip">UTF-8 & Latin-1</span>
                </div>
            </div>
            """
        )

        c_up1, c_up2, c_up3 = st.columns([1.5, 1.2, 1.2])

        with c_up1:
            if st.button("Upload CSV or Excel File", key="overview_empty_goto_upload", use_container_width=True):
                st.session_state.current_page = NAV_DATASET
                st.rerun()

        with c_up2:
            if st.button("Load Sample CSV", key="overview_empty_load_sample_csv", use_container_width=True):
                sample_path = os.path.join(SAMPLE_DATA_DIR, "customer_demographics.csv")
                sample_df, err = load_dataset(sample_path)
                if sample_df is not None:
                    st.session_state.df = sample_df
                    st.session_state.uploaded_file_name = "customer_demographics.csv"
                    st.session_state.dataset_loaded = True
                    st.session_state.file_size_bytes = os.path.getsize(sample_path) if os.path.exists(sample_path) else None
                    add_activity_log("database", "Loaded sample dataset", "customer_demographics.csv")
                    st.rerun()

        with c_up3:
            if st.button("Load Sample Excel", key="overview_empty_load_sample_xlsx", use_container_width=True):
                sample_path = os.path.join(SAMPLE_DATA_DIR, "quarterly_financial_report.xlsx")
                sample_df, err = load_dataset(sample_path)
                if sample_df is not None:
                    st.session_state.df = sample_df
                    st.session_state.uploaded_file_name = "quarterly_financial_report.xlsx"
                    st.session_state.dataset_loaded = True
                    st.session_state.file_size_bytes = os.path.getsize(sample_path) if os.path.exists(sample_path) else None
                    add_activity_log("database", "Loaded sample dataset", "quarterly_financial_report.xlsx")
                    st.rerun()

        render_html("<div class='section-divider'></div>")

        render_html("<h4 style='font-size: 0.95rem; font-weight: 700; margin-bottom: 0.85rem;'>Workspace Capabilities</h4>")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_html(
                f"""
                <div class="feature-card">
                    <div class="feature-icon-wrapper blue-glow">{icon_svg("database", size=16, color="#2563EB")}</div>
                    <div class="feature-title">Instant Profiling</div>
                    <p class="feature-desc">Automated null checking, data types, and schema inspection.</p>
                </div>
                """
            )
        with col2:
            render_html(
                f"""
                <div class="feature-card">
                    <div class="feature-icon-wrapper emerald-glow">{icon_svg("shield-check", size=16, color="#059669")}</div>
                    <div class="feature-title">Quality Scoring</div>
                    <p class="feature-desc">Health score calculated from completeness, duplicates, and cardinality.</p>
                </div>
                """
            )
        with col3:
            render_html(
                f"""
                <div class="feature-card">
                    <div class="feature-icon-wrapper purple-glow">{icon_svg("cpu", size=16, color="#4F46E5")}</div>
                    <div class="feature-title">AI Data Analyst</div>
                    <p class="feature-desc">Ask natural language questions to filter subsets and compute metrics.</p>
                </div>
                """
            )
        with col4:
            render_html(
                f"""
                <div class="feature-card">
                    <div class="feature-icon-wrapper amber-glow">{icon_svg("bar-chart-2", size=16, color="#D97706")}</div>
                    <div class="feature-title">Interactive Charts</div>
                    <p class="feature-desc">Plotly-powered bar, line, pie, scatter, box, and histogram charts.</p>
                </div>
                """
            )
        return

    # =========================================================================
    # ACTIVE DATASET OVERVIEW (When Dataset is Uploaded)
    # =========================================================================

    total_rows, total_cols = df.shape
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]
    missing_cells = int(df.isna().sum().sum())
    total_cells = total_rows * total_cols
    missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    duplicate_rows = int(df.duplicated().sum())
    dup_pct = (duplicate_rows / total_rows * 100.0) if total_rows > 0 else 0.0

    mem_bytes = df.memory_usage(deep=True).sum()
    file_size_val = st.session_state.get("file_size_bytes", mem_bytes)
    file_type_str = "Excel Workbook" if filename.lower().endswith((".xlsx", ".xls")) else "CSV Document"

    quality = calculate_data_quality_score(df)
    insights = generate_quick_insights(df)

    # 1. Header Banner
    render_html(
        f"""
        <div class="page-header-container">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem;">
                <div class="page-header-badge">Overview Dashboard</div>
                <div style="font-size: 0.8rem; font-weight: 600; color: {'#94A3B8' if is_dark else '#64748B'}; display: flex; align-items: center; gap: 6px;">
                    {icon_svg("database", size=14, color="currentColor")}
                    <strong>{filename}</strong>
                    <span style="color: {'#4B5563' if is_dark else '#CBD5E1'};">&bull;</span>
                    <span>{total_rows:,} rows &times; {total_cols} cols</span>
                </div>
            </div>
            <h1 class="page-header-title">Intelligent Dataset Overview</h1>
            <p class="page-header-subtitle">
                Real-time quality scoring, dynamic insights, statistical distributions, and recommended analytical workflows.
            </p>
        </div>
        """
    )

    # 2. KPI Cards Row
    render_html("<h4 style='font-size: 0.95rem; font-weight: 700; margin-bottom: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em;'>Dataset at a Glance</h4>")
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    with m1:
        render_html(
            f"""
            <div class="dataset-kpi-card blue-kpi">
                <div class="dataset-kpi-lbl">{icon_svg("table", size=12)} Total Rows</div>
                <div class="dataset-kpi-val">{total_rows:,}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-info">Records</span></div>
            </div>
            """
        )

    with m2:
        render_html(
            f"""
            <div class="dataset-kpi-card purple-kpi">
                <div class="dataset-kpi-lbl">{icon_svg("layers", size=12)} Columns</div>
                <div class="dataset-kpi-val">{total_cols}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-purple">Attributes</span></div>
            </div>
            """
        )

    with m3:
        render_html(
            f"""
            <div class="dataset-kpi-card emerald-kpi">
                <div class="dataset-kpi-lbl">{icon_svg("hash", size=12)} Numeric</div>
                <div class="dataset-kpi-val">{len(num_cols)}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-emerald">Quantitative</span></div>
            </div>
            """
        )

    with m4:
        render_html(
            f"""
            <div class="dataset-kpi-card amber-kpi">
                <div class="dataset-kpi-lbl">{icon_svg("tag", size=12)} Categorical</div>
                <div class="dataset-kpi-val">{len(cat_cols)}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-amber">Discrete</span></div>
            </div>
            """
        )

    with m5:
        missing_color = "#10B981" if missing_cells == 0 else ("#F59E0B" if missing_pct < 5.0 else "#EF4444")
        render_html(
            f"""
            <div class="dataset-kpi-card" style="border-top: 2px solid {missing_color};">
                <div class="dataset-kpi-lbl">{icon_svg("alert-triangle", size=12)} Missing</div>
                <div class="dataset-kpi-val" style="color: {missing_color};">{missing_cells:,}</div>
                <div class="dataset-kpi-badge"><span class="badge" style="background: {'rgba(239, 68, 68, 0.1)' if missing_cells > 0 else 'rgba(16, 185, 129, 0.1)'}; color: {missing_color}; font-size: 0.68rem;">{missing_pct:.1f}% null</span></div>
            </div>
            """
        )

    with m6:
        dup_color = "#10B981" if duplicate_rows == 0 else "#EF4444"
        render_html(
            f"""
            <div class="dataset-kpi-card" style="border-top: 2px solid {dup_color};">
                <div class="dataset-kpi-lbl">{icon_svg("copy", size=12)} Duplicates</div>
                <div class="dataset-kpi-val" style="color: {dup_color};">{duplicate_rows:,}</div>
                <div class="dataset-kpi-badge"><span class="badge" style="background: {'rgba(239, 68, 68, 0.1)' if duplicate_rows > 0 else 'rgba(16, 185, 129, 0.1)'}; color: {dup_color}; font-size: 0.68rem;">{dup_pct:.1f}% dupes</span></div>
            </div>
            """
        )

    st.write("")

    # 3. Quality Score & Quick Insights
    col_score, col_insights = st.columns([1.1, 1.9])

    with col_score:
        render_html(
            f"""
            <div class="feature-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <span style="font-size: 0.72rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Data Quality Score</span>
                        <span class="badge" style="background: {quality['color']}15; color: {quality['color']}; border: 1px solid {quality['color']}35; font-size: 0.74rem; font-weight: 600;">{quality['status']}</span>
                    </div>
                    
                    <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 0.65rem;">
                        <div style="font-size: 2.4rem; font-weight: 800; color: {quality['color']}; line-height: 1; font-family: var(--font-mono);">
                            {quality['score']}
                        </div>
                        <div style="font-size: 0.95rem; color: {'#64748B' if is_dark else '#94A3B8'}; font-weight: 600;">/ 100</div>
                    </div>

                    <!-- Progress bar -->
                    <div style="width: 100%; height: 6px; background: {'#1F2937' if is_dark else '#F1F5F9'}; border-radius: 9999px; overflow: hidden; margin-bottom: 0.85rem;">
                        <div style="width: {quality['score']}%; height: 100%; background: {quality['color']}; border-radius: 9999px;"></div>
                    </div>

                    <div style="font-size: 0.74rem; font-weight: 600; color: {'#CBD5E1' if is_dark else '#475569'}; margin-bottom: 0.4rem;">Health Breakdown:</div>
                    <ul style="margin: 0; padding-left: 1.1rem; font-size: 0.76rem; color: {'#94A3B8' if is_dark else '#64748B'}; line-height: 1.5;">
                        {''.join(f'<li style="margin-bottom: 2px;">{f}</li>' for f in quality['factors'])}
                    </ul>
                </div>

                <div style="margin-top: 0.85rem; padding-top: 0.65rem; border-top: 1px solid {'#1E293B' if is_dark else '#F1F5F9'}; font-size: 0.7rem; color: {'#64748B' if is_dark else '#94A3B8'};">
                    Quality computed based on missing cells, duplicate records, and cardinality.
                </div>
            </div>
            """
        )

    with col_insights:
        insight_items_html = "".join(
            f"""
            <div style="display: flex; align-items: flex-start; gap: 8px; padding: 0.55rem 0.75rem; background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; margin-bottom: 0.45rem; font-size: 0.82rem; color: {'#F1F5F9' if is_dark else '#1E293B'}; line-height: 1.4;">
                <div style="flex: 1;">{item}</div>
            </div>
            """
            for item in insights
        )

        render_html(
            f"""
            <div class="feature-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <span style="font-size: 0.72rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Automated Quick Insights</span>
                    <span class="badge badge-purple" style="font-size: 0.7rem;">Dynamic EDA</span>
                </div>
                <div>
                    {insight_items_html}
                </div>
            </div>
            """
        )

    st.write("")

    # 4. Dataset Summary & Recommended Next Actions
    col_summary, col_actions = st.columns([1.1, 1.9])

    with col_summary:
        render_html(
            f"""
            <div class="feature-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <span style="font-size: 0.72rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Dataset Summary</span>
                        <span class="badge badge-info" style="font-size: 0.7rem;">Active</span>
                    </div>

                    <div style="margin-bottom: 0.75rem;">
                        <div style="font-size: 1rem; font-weight: 700; color: {'#F8FAFC' if is_dark else '#0F172A'}; word-break: break-all; margin-bottom: 0.15rem; font-family: var(--font-heading);">
                            {filename}
                        </div>
                        <div style="font-size: 0.76rem; color: {'#94A3B8' if is_dark else '#64748B'};">
                            {file_type_str}
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.85rem;">
                        <div style="background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; padding: 0.5rem 0.65rem;">
                            <div style="font-size: 0.65rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.04em;">Dimensions</div>
                            <div style="font-size: 0.84rem; font-weight: 700; color: {'#F8FAFC' if is_dark else '#0F172A'}; font-family: var(--font-mono);">{total_rows:,} &times; {total_cols}</div>
                        </div>
                        <div style="background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; padding: 0.5rem 0.65rem;">
                            <div style="font-size: 0.65rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.04em;">Memory Footprint</div>
                            <div style="font-size: 0.84rem; font-weight: 700; color: {'#F8FAFC' if is_dark else '#0F172A'}; font-family: var(--font-mono);">{format_bytes(file_size_val)}</div>
                        </div>
                    </div>
                </div>
            </div>
            """
        )
        if st.button("View Full Dataset", key="overview_view_dataset_btn", use_container_width=True):
            st.session_state.current_page = NAV_DATASET
            st.rerun()

    with col_actions:
        render_html(
            f"""
            <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.72rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Recommended Next Actions</span>
            </div>
            """
        )

        act1, act2, act3 = st.columns(3)

        with act1:
            render_html(
                f"""
                <div class="feature-card" style="padding: 0.9rem; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div class="feature-icon-wrapper blue-glow" style="margin-bottom: 0.4rem;">{icon_svg("database", size=14, color="#2563EB")}</div>
                        <div class="feature-title" style="font-size: 0.88rem; margin-bottom: 0.15rem;">Explore Dataset</div>
                        <p class="feature-desc" style="font-size: 0.74rem; line-height: 1.35; margin-bottom: 0.65rem;">Inspect schema, filter rows, and view distributions.</p>
                    </div>
                </div>
                """
            )
            if st.button("Explore Data", key="overview_action_dataset", use_container_width=True):
                st.session_state.current_page = NAV_DATASET
                st.rerun()

        with act2:
            render_html(
                f"""
                <div class="feature-card" style="padding: 0.9rem; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div class="feature-icon-wrapper purple-glow" style="margin-bottom: 0.4rem;">{icon_svg("cpu", size=14, color="#4F46E5")}</div>
                        <div class="feature-title" style="font-size: 0.88rem; margin-bottom: 0.15rem;">Ask AI Analyst</div>
                        <p class="feature-desc" style="font-size: 0.74rem; line-height: 1.35; margin-bottom: 0.65rem;">Query in plain English and compute aggregates.</p>
                    </div>
                </div>
                """
            )
            if st.button("Ask AI", key="overview_action_ai", use_container_width=True):
                st.session_state.current_page = NAV_AI_ANALYST
                st.rerun()

        with act3:
            render_html(
                f"""
                <div class="feature-card" style="padding: 0.9rem; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div class="feature-icon-wrapper amber-glow" style="margin-bottom: 0.4rem;">{icon_svg("bar-chart-2", size=14, color="#D97706")}</div>
                        <div class="feature-title" style="font-size: 0.88rem; margin-bottom: 0.15rem;">Visualizations</div>
                        <p class="feature-desc" style="font-size: 0.74rem; line-height: 1.35; margin-bottom: 0.65rem;">Build bar, line, scatter, box, and histogram charts.</p>
                    </div>
                </div>
                """
            )
            if st.button("Build Charts", key="overview_action_vis", use_container_width=True):
                st.session_state.current_page = NAV_VISUALIZATION
                st.rerun()

    st.write("")
    render_html("<div class='section-divider'></div>")

    # 5. Recent Activity
    activity_log = st.session_state.get("activity_log", [])

    render_html(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
            <span style="font-size: 0.74rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Recent Session Events</span>
            <span style="font-size: 0.72rem; color: #94A3B8;">Event audit trail</span>
        </div>
        """
    )

    if activity_log:
        cols_act = st.columns(min(len(activity_log), 4))
        for idx, entry in enumerate(activity_log[:4]):
            col_target = cols_act[idx % len(cols_act)]
            icon_name = entry.get('icon', 'activity')
            if icon_name not in ["activity", "database", "cpu", "bar-chart-2", "upload-cloud", "filter"]:
                icon_name = "activity"
            with col_target:
                render_html(
                    f"""
                    <div style="background: {'#111827' if is_dark else '#FFFFFF'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; padding: 0.55rem 0.75rem; height: 100%;">
                        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 0.15rem;">
                            <span style="color: #3B82F6;">{icon_svg(icon_name, size=13)}</span>
                            <span style="font-size: 0.78rem; font-weight: 600; color: {'#F8FAFC' if is_dark else '#0F172A'};">{entry.get('action', 'Activity')}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: {'#94A3B8' if is_dark else '#64748B'}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: var(--font-mono);">
                            {entry.get('detail', '')}
                        </div>
                    </div>
                    """
                )
    else:
        render_html(
            f"""
            <div style="background: {'#111827' if is_dark else '#FFFFFF'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; padding: 0.75rem 0.9rem; display: flex; align-items: center; gap: 10px;">
                <span style="color: #3B82F6;">{icon_svg("database", size=18)}</span>
                <div>
                    <div style="font-size: 0.82rem; font-weight: 600; color: {'#F8FAFC' if is_dark else '#0F172A'};">Dataset Active: {filename}</div>
                    <div style="font-size: 0.74rem; color: {'#94A3B8' if is_dark else '#64748B'};">Explore schema, query with AI, or generate interactive charts to build your session activity.</div>
                </div>
            </div>
            """
        )
