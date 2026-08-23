"""
Interactive Visualization and Chart Builder Module for Data Studio
Supports:
- Bar Chart
- Line Chart
- Pie / Donut Chart
- Scatter Plot
- Histogram
- Box Plot
With smart column classification, statistical aggregations, theme styling, and interactive Plotly charts.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from modules.config import (
    NAV_DATASET,
    APP_NAME,
)
from modules.ui_components import render_top_action_bar, render_html
from modules.icons import icon_svg

try:
    from modules.config import add_activity_log
except ImportError:
    def add_activity_log(icon: str, action: str, detail: str):
        pass


DARK_COLOR_PALETTE = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald
    "#8B5CF6",  # Purple
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#6366F1",  # Indigo
    "#F97316",  # Orange
    "#14B8A6",  # Teal
    "#E11D48",  # Rose
]

LIGHT_COLOR_PALETTE = [
    "#2563EB",  # Darker Blue
    "#059669",  # Darker Emerald
    "#7C3AED",  # Darker Purple
    "#D97706",  # Darker Amber
    "#DB2777",  # Darker Pink
    "#0891B2",  # Darker Cyan
    "#4F46E5",  # Darker Indigo
    "#EA580C",  # Darker Orange
    "#0D9488",  # Darker Teal
    "#BE123C",  # Darker Rose
]


def detect_column_types(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Automatically classify DataFrame columns into numerical, categorical, and datetime groups."""
    if df is None or df.empty:
        return {"numeric": [], "categorical": [], "datetime": [], "all": []}

    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    
    datetime_cols = []
    categorical_cols = []

    date_keywords = ["date", "time", "year", "month", "day", "quarter", "period", "timestamp", "dt"]

    for col in all_cols:
        if col in numeric_cols:
            continue

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            datetime_cols.append(col)
            continue

        col_lower = str(col).lower()
        has_date_keyword = any(kw in col_lower for kw in date_keywords)
        
        sample_vals = df[col].dropna().head(10)
        if len(sample_vals) > 0:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed = pd.to_datetime(sample_vals, errors="coerce")
                    if parsed.notna().sum() >= len(sample_vals) * 0.8:
                        datetime_cols.append(col)
                        continue
            except Exception:
                pass

        if has_date_keyword and len(sample_vals) > 0:
            datetime_cols.append(col)
        else:
            categorical_cols.append(col)

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
        "all": all_cols,
    }


def apply_plotly_theme(fig: go.Figure, is_dark: bool = False, title: str = "") -> go.Figure:
    """Apply consistent high-end styling to Plotly charts."""
    bg_color = "#111827" if is_dark else "#FFFFFF"
    paper_color = "#111827" if is_dark else "#FFFFFF"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    grid_color = "#1E293B" if is_dark else "#F1F5F9"
    border_color = "#334155" if is_dark else "#E2E8F0"

    fig.update_layout(
        title={
            "text": title,
            "font": {"family": "Plus Jakarta Sans, Inter, sans-serif", "size": 15, "color": text_color},
            "x": 0.01,
            "y": 0.96,
        },
        plot_bgcolor=bg_color,
        paper_bgcolor=paper_color,
        font={"family": "Inter, sans-serif", "color": text_color, "size": 11},
        margin={"l": 50, "r": 30, "t": 45, "b": 45},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 11, "color": text_color},
        },
    )

    fig.update_xaxes(
        gridcolor=grid_color,
        linecolor=border_color,
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=grid_color,
        linecolor=border_color,
        zeroline=False,
    )

    return fig


def render_visualization_page():
    """Render the complete Visualization section and Chart Builder workspace."""
    render_top_action_bar(key_suffix="visualization")

    render_html(
        """
        <div class="page-header-container">
            <div class="page-header-badge">Interactive Studio</div>
            <h1 class="page-header-title">Visualize Your Data</h1>
            <p class="page-header-subtitle">
                Create interactive charts from your uploaded dataset and explore patterns, trends, and relationships.
            </p>
        </div>
        """
    )

    df: Optional[pd.DataFrame] = st.session_state.get("df")
    is_dataset_loaded = st.session_state.get("dataset_loaded", False) and df is not None

    if not is_dataset_loaded:
        render_html(
            f"""
            <div class="empty-upload-card" style="padding: 3rem 2rem; margin-top: 1rem;">
                <div class="empty-upload-icon">{icon_svg("bar-chart-2", size=26, color="#2563EB")}</div>
                <div class="empty-upload-title">No Dataset Loaded</div>
                <p class="empty-upload-desc">
                    Please upload a CSV or Excel dataset to unlock the interactive chart builder and begin exploring visual insights.
                </p>
            </div>
            """
        )
        st.write("")
        col1, col2, col3 = st.columns([1.5, 1.2, 1.5])
        with col2:
            if st.button("Go to Dataset Workspace", key="vis_empty_upload_btn", use_container_width=True):
                st.session_state.current_page = NAV_DATASET
                st.rerun()
        return

    filename = st.session_state.get("uploaded_file_name", "Dataset")
    col_types = detect_column_types(df)
    numeric_cols = col_types["numeric"]
    categorical_cols = col_types["categorical"]
    datetime_cols = col_types["datetime"]
    all_cols = col_types["all"]

    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"
    palette = DARK_COLOR_PALETTE if is_dark else LIGHT_COLOR_PALETTE

    render_html(
        f"""
        <div class="table-info-bar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem;">
            <div>Active Dataset: <strong>{filename}</strong> &bull; <strong>{len(df):,}</strong> rows &bull; <strong>{len(all_cols)}</strong> columns</div>
            <div style="font-size: 0.78rem;">
                <span class="badge badge-info">{len(numeric_cols)} Numerical</span>
                <span class="badge badge-purple">{len(categorical_cols)} Categorical</span>
                {f'<span class="badge badge-emerald">{len(datetime_cols)} Date/Time</span>' if datetime_cols else ''}
            </div>
        </div>
        """
    )

    st.markdown("#### Chart Configuration")
    
    chart_types = [
        "Bar Chart",
        "Line Chart",
        "Pie / Donut Chart",
        "Scatter Plot",
        "Histogram",
        "Box Plot",
    ]

    ctrl_col1, ctrl_col2 = st.columns([1, 2.2])

    with ctrl_col1:
        selected_chart_type = st.selectbox(
            "1. Select Chart Type",
            options=chart_types,
            index=0,
            key="vis_chart_type_select",
        )

    x_col = None
    y_col = None
    agg_func = "Sum"
    color_col = None
    chart_title = ""

    with ctrl_col2:
        st.markdown(f"**2. Configure {selected_chart_type} Parameters**")
        p_row1, p_row2 = st.columns(2)

        if selected_chart_type == "Bar Chart":
            with p_row1:
                x_col = st.selectbox("Category (X-Axis)", options=categorical_cols + all_cols, key="bar_x_col")
                y_col = st.selectbox("Metric (Y-Axis)", options=["Row Count"] + numeric_cols, key="bar_y_col")
                if y_col == "Row Count":
                    y_col = None
                    agg_func = "Count"
            with p_row2:
                if y_col is not None:
                    agg_func = st.selectbox("Aggregation", options=["Sum", "Average", "Minimum", "Maximum"], index=0, key="bar_agg_func")
                color_col = st.selectbox("Color / Grouping (Optional)", options=["None"] + categorical_cols, key="bar_color_col")
                if color_col == "None":
                    color_col = None

        elif selected_chart_type == "Line Chart":
            with p_row1:
                x_options = datetime_cols + numeric_cols + categorical_cols
                x_col = st.selectbox("X-Axis (Time or Sequence)", options=x_options, key="line_x_col")
                y_col = st.selectbox("Y-Axis (Metric)", options=numeric_cols + ["Row Count"], key="line_y_col")
                if y_col == "Row Count":
                    y_col = None
                    agg_func = "Count"
            with p_row2:
                if y_col is not None:
                    agg_func = st.selectbox("Aggregation", options=["Average", "Sum", "None (Raw Data)"], index=0, key="line_agg_func")
                color_col = st.selectbox("Color / Grouping (Optional)", options=["None"] + categorical_cols, key="line_color_col")
                if color_col == "None":
                    color_col = None

        elif selected_chart_type == "Pie / Donut Chart":
            with p_row1:
                x_col = st.selectbox("Category Column", options=categorical_cols + all_cols, key="pie_x_col")
                y_col = st.selectbox("Values Column", options=["Row Count"] + numeric_cols, key="pie_y_col")
                if y_col == "Row Count":
                    y_col = None
                    agg_func = "Count"
            with p_row2:
                if y_col is not None:
                    agg_func = st.selectbox("Aggregation", options=["Sum", "Average"], index=0, key="pie_agg_func")
                is_donut = st.checkbox("Donut Chart Style", value=True, key="pie_donut_check")

        elif selected_chart_type == "Scatter Plot":
            with p_row1:
                x_col = st.selectbox("X-Axis (Numerical)", options=numeric_cols, key="scatter_x_col")
                y_col = st.selectbox("Y-Axis (Numerical)", options=[c for c in numeric_cols if c != x_col] + numeric_cols, key="scatter_y_col")
            with p_row2:
                color_col = st.selectbox("Color by Category (Optional)", options=["None"] + categorical_cols, key="scatter_color_col")
                if color_col == "None":
                    color_col = None

        elif selected_chart_type == "Histogram":
            with p_row1:
                x_col = st.selectbox("Numerical Column", options=numeric_cols, key="hist_x_col")
            with p_row2:
                hist_bins = st.slider("Number of Bins", min_value=5, max_value=60, value=25, key="hist_bins_slider")
                color_col = st.selectbox("Color by Category (Optional)", options=["None"] + categorical_cols, key="hist_color_col")
                if color_col == "None":
                    color_col = None

        elif selected_chart_type == "Box Plot":
            with p_row1:
                y_col = st.selectbox("Numerical Metric (Y-Axis)", options=numeric_cols, key="box_y_col")
            with p_row2:
                x_col = st.selectbox("Group by Category (X-Axis, Optional)", options=["None"] + categorical_cols, key="box_x_col")
                if x_col == "None":
                    x_col = None

        default_title = f"{selected_chart_type}: {y_col if y_col else 'Count'} by {x_col if x_col else ''}".strip(" by ")
        chart_title = st.text_input("Chart Title", value=default_title, key="vis_custom_chart_title")

    # Generate Action
    st.write("")
    gen_col1, _ = st.columns([1.5, 4.5])
    with gen_col1:
        st.button("Generate Chart", key="vis_generate_chart_btn", use_container_width=True)

    render_html("<div class='section-divider'></div>")

    # Execution & Processing
    fig: Optional[go.Figure] = None
    summary_metrics: Dict[str, Any] = {}
    chart_df: Optional[pd.DataFrame] = None

    try:
        if selected_chart_type == "Bar Chart" and x_col:
            group_cols = [x_col]
            if color_col and color_col != x_col:
                group_cols.append(color_col)

            if agg_func == "Count" or not y_col:
                val_col = "Count"
                chart_df = df.groupby(group_cols).size().reset_index(name=val_col)
            else:
                agg_map = {"Sum": "sum", "Average": "mean", "Minimum": "min", "Maximum": "max"}
                func = agg_map.get(agg_func, "sum")
                val_col = f"{y_col}_{agg_func}"
                chart_df = df.groupby(group_cols)[y_col].agg(func).reset_index(name=val_col)

            chart_df = chart_df.sort_values(by=val_col, ascending=False)
            fig = px.bar(chart_df, x=x_col, y=val_col, color=color_col, color_discrete_sequence=palette, text_auto=True)
            summary_metrics = {
                "Categories": chart_df[x_col].nunique(),
                "Total Value": f"{chart_df[val_col].sum():,.2f}" if pd.api.types.is_numeric_dtype(chart_df[val_col]) else len(chart_df),
                "Max Value": f"{chart_df[val_col].max():,.2f}" if pd.api.types.is_numeric_dtype(chart_df[val_col]) else "-",
            }

        elif selected_chart_type == "Line Chart" and x_col:
            if agg_func == "None (Raw Data)":
                chart_df = df.sort_values(by=x_col)
                val_col = y_col
            elif agg_func == "Count" or not y_col:
                group_cols = [x_col]
                if color_col and color_col != x_col:
                    group_cols.append(color_col)
                chart_df = df.groupby(group_cols).size().reset_index(name="Count")
                val_col = "Count"
            else:
                group_cols = [x_col]
                if color_col and color_col != x_col:
                    group_cols.append(color_col)
                agg_map = {"Sum": "sum", "Average": "mean"}
                func = agg_map.get(agg_func, "mean")
                val_col = f"{y_col}_{agg_func}"
                chart_df = df.groupby(group_cols)[y_col].agg(func).reset_index(name=val_col)

            chart_df = chart_df.sort_values(by=x_col)
            fig = px.line(chart_df, x=x_col, y=val_col, color=color_col, markers=True, color_discrete_sequence=palette)
            summary_metrics = {
                "Data Points": len(chart_df),
                "Min Value": f"{chart_df[val_col].min():,.2f}" if pd.api.types.is_numeric_dtype(chart_df[val_col]) else "-",
                "Max Value": f"{chart_df[val_col].max():,.2f}" if pd.api.types.is_numeric_dtype(chart_df[val_col]) else "-",
            }

        elif selected_chart_type == "Pie / Donut Chart" and x_col:
            if agg_func == "Count" or not y_col:
                chart_df = df.groupby(x_col).size().reset_index(name="Count")
                val_col = "Count"
            else:
                func = "sum" if agg_func == "Sum" else "mean"
                val_col = f"{y_col}_{agg_func}"
                chart_df = df.groupby(x_col)[y_col].agg(func).reset_index(name=val_col)

            fig = px.pie(chart_df, names=x_col, values=val_col, hole=0.4 if is_donut else 0.0, color_discrete_sequence=palette)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            summary_metrics = {
                "Total Slices": len(chart_df),
                "Total Value": f"{chart_df[val_col].sum():,.2f}",
            }

        elif selected_chart_type == "Scatter Plot" and x_col and y_col:
            chart_df = df.dropna(subset=[x_col, y_col])
            fig = px.scatter(chart_df, x=x_col, y=y_col, color=color_col, color_discrete_sequence=palette)
            corr_val = chart_df[[x_col, y_col]].corr().iloc[0, 1] if len(chart_df) > 1 else 0.0
            summary_metrics = {
                "Sample Points": len(chart_df),
                "Correlation (r)": f"{corr_val:.3f}",
            }

        elif selected_chart_type == "Histogram" and x_col:
            chart_df = df.dropna(subset=[x_col])
            fig = px.histogram(chart_df, x=x_col, nbins=hist_bins, color=color_col, color_discrete_sequence=palette, marginal="box")
            summary_metrics = {
                "Total Records": len(chart_df),
                "Mean": f"{chart_df[x_col].mean():,.2f}",
                "Median": f"{chart_df[x_col].median():,.2f}",
            }

        elif selected_chart_type == "Box Plot" and y_col:
            chart_df = df.dropna(subset=[y_col])
            fig = px.box(chart_df, x=x_col, y=y_col, color=color_col if color_col else x_col, color_discrete_sequence=palette)
            summary_metrics = {
                "Records Analyzed": len(chart_df),
                "Median": f"{chart_df[y_col].median():,.2f}",
            }

    except Exception as e:
        render_html(
            f"""
            <div class="alert-banner alert-error">
                <div class="alert-icon">{icon_svg("alert-triangle", size=18, color="#EF4444")}</div>
                <div class="alert-content">
                    <div class="alert-title">Visualization Error</div>
                    <div class="alert-message">Could not generate {selected_chart_type}: {str(e)}</div>
                </div>
            </div>
            """
        )
        return

    if fig is not None:
        fig = apply_plotly_theme(fig, is_dark=is_dark, title=chart_title)

        if summary_metrics:
            m_cols = st.columns(len(summary_metrics))
            for idx, (label, val) in enumerate(summary_metrics.items()):
                with m_cols[idx]:
                    render_html(
                        f"""
                        <div class="dataset-kpi-card {'blue-kpi' if idx%4==0 else ('emerald-kpi' if idx%4==1 else ('purple-kpi' if idx%4==2 else 'amber-kpi'))}">
                            <div class="dataset-kpi-lbl">{label}</div>
                            <div class="dataset-kpi-val" style="font-size: 1.15rem;">{val}</div>
                        </div>
                        """
                    )
            st.write("")

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
        )
        add_activity_log("bar-chart-2", "Created Chart", f"{selected_chart_type} on {x_col if x_col else 'dataset'}")

        if chart_df is not None and not chart_df.empty:
            with st.expander("View & Export Source Data", expanded=False):
                st.dataframe(chart_df.head(100), use_container_width=True)
                csv_bytes = chart_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Chart Data as CSV",
                    data=csv_bytes,
                    file_name=f"{selected_chart_type.lower().replace(' ', '_')}_data.csv",
                    mime="text/csv",
                    key="download_vis_chart_data_btn",
                )
