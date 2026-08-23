"""
Standard Exploratory Data Analysis (EDA) Toolkit for Data Studio
Provides comprehensive, high-end analytical modules:
1. Correlation Heatmap (Visual interactive Plotly heatmap with diverging palette)
2. Distribution Plots per Numeric Column (Histogram + Boxplot combo grid)
3. Outlier Detection (IQR and Z-score based with per-column counts and drilldown)
4. Column Deep-Dive Inspector (Focused panel with stats, distribution & frequencies)
5. Composite Data Quality Scoring Engine (0-100 score combining health dimensions)
6. Skewness & Kurtosis Statistical Indicators (With interpretive badges)
7. Pivot Table & Group-By Builder (Multi-column aggregation with charts)
8. Visual Filter / Query Builder UI (Condition builder with filter chips)
9. Target / Feature Comparison Analysis (Bivariate correlation against target variable)
10. Executive Report Export (HTML/Markdown summary report & CSV export)
"""

import io
import base64
import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

from plotly.subplots import make_subplots
import streamlit as st
from modules.icons import icon_svg, icon_with_text


def render_html(html_str: str):
    """Render HTML safely without Markdown treating indented lines as code blocks."""
    lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    cleaned = "".join(lines)
    st.markdown(cleaned, unsafe_allow_html=True)


# =============================================================================
# THEME & PLOTLY STYLING UTILITY
# =============================================================================

def get_plotly_layout(title: str = "", height: int = 400) -> dict:
    """Return clean, polished Plotly layout matching current theme."""
    is_dark = st.session_state.get("theme", "light") == "dark"
    bg_color = "#111827" if is_dark else "#FFFFFF"
    paper_color = "#111827" if is_dark else "#FFFFFF"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    grid_color = "#1E293B" if is_dark else "#F1F5F9"
    border_color = "#334155" if is_dark else "#E2E8F0"

    return {
        "title": {
            "text": title,
            "font": {"family": "Plus Jakarta Sans, Inter, sans-serif", "size": 14, "color": text_color},
            "x": 0.02,
            "y": 0.96,
        },
        "height": height,
        "margin": {"l": 50, "r": 30, "t": 45, "b": 45},
        "plot_bgcolor": bg_color,
        "paper_bgcolor": paper_color,
        "font": {"family": "Inter, sans-serif", "color": text_color, "size": 11},
        "xaxis": {
            "gridcolor": grid_color,
            "linecolor": border_color,
            "zerolinecolor": grid_color,
            "tickfont": {"color": "#94A3B8", "size": 10},
        },
        "yaxis": {
            "gridcolor": grid_color,
            "linecolor": border_color,
            "zerolinecolor": grid_color,
            "tickfont": {"color": "#94A3B8", "size": 10},
        },
    }


# =============================================================================
# 1. CORRELATION HEATMAP
# =============================================================================

def render_correlation_heatmap(df: pd.DataFrame):
    """Render interactive visual correlation heatmap with threshold filtering."""
    num_df = df.select_dtypes(include=["number"])
    num_cols = num_df.columns.tolist()

    if len(num_cols) < 2:
        st.info("At least 2 numerical columns are required to generate a correlation heatmap.")
        return

    ctrl1, ctrl2, ctrl3 = st.columns([1.5, 1.5, 2])
    with ctrl1:
        method = st.selectbox(
            "Correlation Method",
            options=["pearson", "spearman", "kendall"],
            format_func=lambda x: x.capitalize(),
            key="eda_corr_method_select",
        )
    with ctrl2:
        threshold = st.slider(
            "Min Correlation (|r|)",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            key="eda_corr_threshold_slider",
        )
    with ctrl3:
        colorscale = st.selectbox(
            "Color Palette",
            options=["RdBu_r", "Blues", "Viridis", "Tealrose"],
            key="eda_corr_colorscale_select",
        )

    corr = num_df.corr(method=method).round(2)

    # Filter by threshold if specified
    if threshold > 0.0:
        mask = (corr.abs() >= threshold)
        filtered_corr = corr.where(mask, 0)
    else:
        filtered_corr = corr

    is_dark = st.session_state.get("theme", "light") == "dark"

    fig = px.imshow(
        filtered_corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=colorscale,
        zmin=-1.0,
        zmax=1.0,
        labels=dict(color="Correlation"),
    )

    layout = get_plotly_layout(f"{method.capitalize()} Correlation Matrix (N={len(num_cols)} Variables)", height=max(420, len(num_cols) * 35))
    fig.update_layout(**layout)
    fig.update_traces(textfont={"size": 10, "family": "JetBrains Mono, monospace"})

    st.plotly_chart(fig, use_container_width=True)

    # Top Correlated Pairs Summary
    corr_unstacked = corr.abs().unstack()
    corr_unstacked = corr_unstacked[corr_unstacked < 1.0].sort_values(ascending=False).drop_duplicates()
    
    if not corr_unstacked.empty:
        render_html(
            f"""
            <div style="margin-top: 0.8rem; margin-bottom: 0.5rem;">
                <span style="font-size: 0.76rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.05em;">Top Feature Correlations</span>
            </div>
            """
        )
        top_pairs = []
        for (c1, c2), val in corr_unstacked.head(5).items():
            raw_r = corr.loc[c1, c2]
            direction = "Positive" if raw_r > 0 else "Negative"
            badge = "badge-emerald" if abs(raw_r) >= 0.7 else "badge-info"
            top_pairs.append(f"<code>{c1}</code> &harr; <code>{c2}</code>: <strong>{raw_r:+.2f}</strong> ({direction})")
        
        cols = st.columns(min(len(top_pairs), 3))
        for i, pair in enumerate(top_pairs[:3]):
            with cols[i]:
                render_html(
                    f"""
                    <div style="background: {'#111827' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; padding: 0.55rem 0.75rem; font-size: 0.8rem;">
                        {pair}
                    </div>
                    """
                )


# =============================================================================
# 2. DISTRIBUTION PLOTS PER NUMERIC COLUMN
# =============================================================================

def render_distribution_plots(df: pd.DataFrame):
    """Auto-generate histogram + boxplot combo for numeric columns."""
    num_df = df.select_dtypes(include=["number"])
    num_cols = num_df.columns.tolist()

    if not num_cols:
        st.info("No numerical columns detected for distribution analysis.")
        return

    st.markdown(
        f"""
        <div style="font-size: 0.84rem; color: #94A3B8; margin-bottom: 0.85rem;">
            Displaying auto-generated distribution profiles across <strong>{len(num_cols)}</strong> quantitative attributes.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Column selector or batch view
    c_choice = st.selectbox(
        "Select Column to Inspect Distribution (or view all)",
        options=["All Numerical Columns"] + num_cols,
        key="eda_dist_col_select",
    )

    cols_to_plot = num_cols if c_choice == "All Numerical Columns" else [c_choice]

    for col in cols_to_plot:
        series = df[col].dropna()
        if len(series) == 0:
            continue

        mean_val = series.mean()
        median_val = series.median()
        std_val = series.std()
        skew_val = series.skew()

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.25, 0.75],
        )

        # 1. Box plot on top
        fig.add_trace(
            go.Box(x=series, name="", marker_color="#3B82F6", boxpoints="outliers"),
            row=1,
            col=1,
        )

        # 2. Histogram on bottom
        fig.add_trace(
            go.Histogram(
                x=series,
                name="Frequency",
                marker_color="#2563EB",
                opacity=0.8,
            ),
            row=2,
            col=1,
        )

        layout = get_plotly_layout(f"Distribution & Quartiles: {col} (Mean: {mean_val:.2f} | Median: {median_val:.2f} | Skew: {skew_val:.2f})", height=320)
        fig.update_layout(**layout)
        fig.update_layout(showlegend=False)

        st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# 3. OUTLIER DETECTION (IQR & Z-SCORE)
# =============================================================================

def render_outlier_detection(df: pd.DataFrame):
    """IQR and Z-score outlier detection with counts and interactive inspection."""
    num_df = df.select_dtypes(include=["number"])
    num_cols = num_df.columns.tolist()

    if not num_cols:
        st.info("No numerical columns available for outlier detection.")
        return

    ctrl1, ctrl2 = st.columns([1.5, 2.5])
    with ctrl1:
        method = st.radio(
            "Detection Method",
            options=["IQR (1.5 × Interquartile Range)", "Z-Score (|z| > 3.0)"],
            key="eda_outlier_method_radio",
            horizontal=True,
        )

    outlier_summary = []
    outlier_masks = {}

    for c in num_cols:
        s = df[c].dropna()
        n_total = len(df[c])
        if len(s) < 4:
            continue

        if "IQR" in method:
            q1 = s.quantile(0.25)
            q3 = s.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (df[c] < lower) | (df[c] > upper)
        else:
            mean = s.mean()
            std = s.std()
            lower = mean - 3.0 * std if std > 0 else mean
            upper = mean + 3.0 * std if std > 0 else mean
            mask = (df[c] < lower) | (df[c] > upper)

        count = int(mask.sum())
        pct = round((count / n_total * 100), 2) if n_total > 0 else 0.0
        outlier_masks[c] = mask

        outlier_summary.append({
            "Column": c,
            "Outlier Count": count,
            "Outlier %": pct,
            "Lower Bound": round(lower, 2),
            "Upper Bound": round(upper, 2),
            "Min Value": round(s.min(), 2),
            "Max Value": round(s.max(), 2),
        })

    sum_df = pd.DataFrame(outlier_summary)
    if not sum_df.empty:
        sum_df = sum_df.sort_values(by="Outlier Count", ascending=False)
        st.dataframe(sum_df, use_container_width=True, hide_index=True)

        st.write("")
        inspect_col = st.selectbox(
            "Drilldown into Column Outlier Records",
            options=sum_df["Column"].tolist(),
            key="eda_outlier_drilldown_col",
        )
        if inspect_col and inspect_col in outlier_masks:
            flagged_rows = df[outlier_masks[inspect_col]]
            st.markdown(
                f"""
                <div class="table-info-bar">
                    <span>Flagged <strong>{len(flagged_rows):,}</strong> outlier rows in <code>{inspect_col}</code></span>
                    <span>{len(flagged_rows) / len(df) * 100:.1f}% of dataset</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.dataframe(flagged_rows, use_container_width=True)


# =============================================================================
# 4. COLUMN DEEP-DIVE VIEW
# =============================================================================

def render_column_deep_dive(df: pd.DataFrame):
    """Focused single-column inspector with type, counts, and top values."""
    col_name = st.selectbox(
        "Select Column to Inspect",
        options=df.columns.tolist(),
        key="eda_deep_dive_col_select",
    )

    if not col_name:
        return

    series = df[col_name]
    total_len = len(df)
    non_nulls = int(series.notna().sum())
    nulls = total_len - non_nulls
    null_pct = round((nulls / total_len * 100), 2) if total_len > 0 else 0.0
    n_unique = int(series.nunique(dropna=False))
    dtype_str = str(series.dtype)

    is_dark = st.session_state.get("theme", "light") == "dark"

    # Top KPI metrics
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_html(
            f"""
            <div class="dataset-kpi-card blue-kpi">
                <div class="dataset-kpi-lbl">Data Type</div>
                <div class="dataset-kpi-val" style="font-size: 1.1rem;">{dtype_str}</div>
            </div>
            """
        )
    with k2:
        render_html(
            f"""
            <div class="dataset-kpi-card purple-kpi">
                <div class="dataset-kpi-lbl">Distinct Values</div>
                <div class="dataset-kpi-val">{n_unique:,}</div>
            </div>
            """
        )
    with k3:
        render_html(
            f"""
            <div class="dataset-kpi-card emerald-kpi">
                <div class="dataset-kpi-lbl">Valid Values</div>
                <div class="dataset-kpi-val">{non_nulls:,}</div>
            </div>
            """
        )
    with k4:
        null_col = "#10B981" if nulls == 0 else "#EF4444"
        render_html(
            f"""
            <div class="dataset-kpi-card" style="border-top: 2px solid {null_col};">
                <div class="dataset-kpi-lbl">Missing Values</div>
                <div class="dataset-kpi-val" style="color: {null_col};">{nulls:,} <span style="font-size: 0.8rem; font-weight: 500;">({null_pct}%)</span></div>
            </div>
            """
        )

    st.write("")

    # Visual Distribution / Top Values
    if pd.api.types.is_numeric_dtype(series):
        s_clean = series.dropna()
        c_left, c_right = st.columns([1.2, 2.8])
        with c_left:
            stats = {
                "Mean": round(s_clean.mean(), 2),
                "Std Dev": round(s_clean.std(), 2),
                "Median": round(s_clean.median(), 2),
                "Min": round(s_clean.min(), 2),
                "25% (Q1)": round(s_clean.quantile(0.25), 2),
                "75% (Q3)": round(s_clean.quantile(0.75), 2),
                "Max": round(s_clean.max(), 2),
                "Skewness": round(s_clean.skew(), 2),
                "Kurtosis": round(s_clean.kurtosis(), 2),
            }
            stats_df = pd.DataFrame(list(stats.items()), columns=["Metric", "Value"])
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

        with c_right:
            fig = px.histogram(s_clean, x=col_name, nbins=30, color_discrete_sequence=["#3B82F6"])
            layout = get_plotly_layout(f"Frequency Distribution: {col_name}", height=320)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

    else:
        # Categorical Value Counts
        counts = series.value_counts(dropna=False).head(15).reset_index()
        counts.columns = [col_name, "Frequency"]
        counts["Percentage"] = (counts["Frequency"] / total_len * 100).round(1)

        c_left, c_right = st.columns([1.5, 2.5])
        with c_left:
            st.dataframe(counts, use_container_width=True, hide_index=True)

        with c_right:
            fig = px.bar(
                counts,
                x=col_name,
                y="Frequency",
                text="Percentage",
                color_discrete_sequence=["#6366F1"],
            )
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            layout = get_plotly_layout(f"Top 15 Categories: {col_name}", height=320)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# 5. SKEWNESS & KURTOSIS STATISTICAL INDICATORS
# =============================================================================

def render_skewness_kurtosis_table(df: pd.DataFrame):
    """Detailed summary table with Skewness, Kurtosis, and descriptive badges."""
    num_df = df.select_dtypes(include=["number"])
    num_cols = num_df.columns.tolist()

    if not num_cols:
        st.info("No numerical columns available.")
        return

    rows = []
    for c in num_cols:
        s = df[c].dropna()
        if len(s) < 3:
            continue

        skew = s.skew()
        kurt = s.kurtosis()
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1

        # Skewness classification
        if abs(skew) < 0.5:
            skew_label = "Symmetric"
        elif skew > 0:
            skew_label = "Right Skewed"
        else:
            skew_label = "Left Skewed"

        # Kurtosis classification (Fisher kurtosis, 0 = normal)
        if abs(kurt) < 0.5:
            kurt_label = "Mesokurtic (Normal)"
        elif kurt > 0.5:
            kurt_label = "Leptokurtic (Heavy-tailed)"
        else:
            kurt_label = "Platykurtic (Light-tailed)"

        rows.append({
            "Column": c,
            "Mean": round(s.mean(), 2),
            "Median": round(s.median(), 2),
            "Std Dev": round(s.std(), 2),
            "Variance": round(s.var(), 2),
            "IQR": round(iqr, 2),
            "Skewness": round(skew, 2),
            "Skew Shape": skew_label,
            "Kurtosis": round(kurt, 2),
            "Tail Profile": kurt_label,
        })

    stats_df = pd.DataFrame(rows)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)


# =============================================================================
# 6. PIVOT TABLE & GROUP-BY BUILDER
# =============================================================================

def render_pivot_table_builder(df: pd.DataFrame):
    """Interactive aggregator by group columns, metric, and aggregation function."""
    c1, c2, c3 = st.columns(3)

    with c1:
        group_cols = st.multiselect(
            "Group By Column(s)",
            options=df.columns.tolist(),
            default=[df.columns[0]],
            key="eda_pivot_group_cols",
        )

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    with c2:
        val_col = st.selectbox(
            "Aggregate Metric Column",
            options=num_cols if num_cols else df.columns.tolist(),
            key="eda_pivot_val_col",
        )

    with c3:
        agg_func = st.selectbox(
            "Aggregation Function",
            options=["mean", "sum", "count", "median", "min", "max", "std"],
            key="eda_pivot_agg_func",
        )

    if not group_cols or not val_col:
        st.info("Select at least one group column and metric column to build the pivot table.")
        return

    try:
        pivot_df = df.groupby(group_cols)[val_col].agg(agg_func).reset_index()
        pivot_df[val_col] = pivot_df[val_col].round(2)
        pivot_df = pivot_df.sort_values(by=val_col, ascending=False)

        st.dataframe(pivot_df, use_container_width=True, hide_index=True)

        # Plot aggregated result
        if len(group_cols) == 1:
            fig = px.bar(
                pivot_df.head(20),
                x=group_cols[0],
                y=val_col,
                title=f"{agg_func.upper()} of {val_col} grouped by {group_cols[0]}",
                color_discrete_sequence=["#2563EB"],
            )
            layout = get_plotly_layout(f"{agg_func.upper()} of {val_col} by {group_cols[0]}", height=320)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error computing pivot aggregation: {str(e)}")


# =============================================================================
# 7. FILTER / QUERY BUILDER UI
# =============================================================================

def render_filter_query_builder(df: pd.DataFrame) -> pd.DataFrame:
    """Visual filter builder with conditions and active query state."""
    if "active_filters" not in st.session_state:
        st.session_state.active_filters = []

    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 2, 1])

    with f_col1:
        f_column = st.selectbox("Column", options=df.columns.tolist(), key="eda_filter_col_select")

    with f_col2:
        f_op = st.selectbox(
            "Operator",
            options=["==", "!=", ">", "<", ">=", "<=", "contains", "is null", "is not null"],
            key="eda_filter_op_select",
        )

    with f_col3:
        f_val = ""
        if f_op not in ["is null", "is not null"]:
            f_val = st.text_input("Value", placeholder="e.g. 50 or Sedan", key="eda_filter_val_input")

    with f_col4:
        st.write("")
        st.write("")
        if st.button("Add Filter", key="eda_add_filter_btn", use_container_width=True):
            if f_op in ["is null", "is not null"] or f_val != "":
                st.session_state.active_filters.append({
                    "column": f_column,
                    "operator": f_op,
                    "value": f_val,
                })
                st.rerun()

    # Display Active Filters Chips
    filtered_df = df.copy()
    if st.session_state.active_filters:
        st.markdown(
            """
            <div style="font-size: 0.76rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 6px;">Active Filter Conditions</div>
            """,
            unsafe_allow_html=True,
        )

        chip_cols = st.columns(len(st.session_state.active_filters) + 1)
        for idx, flt in enumerate(st.session_state.active_filters):
            col = flt["column"]
            op = flt["operator"]
            val = flt["value"]

            # Apply filter logic
            try:
                if op == "==":
                    if pd.api.types.is_numeric_dtype(filtered_df[col]):
                        filtered_df = filtered_df[filtered_df[col] == float(val)]
                    else:
                        filtered_df = filtered_df[filtered_df[col].astype(str) == str(val)]
                elif op == "!=":
                    if pd.api.types.is_numeric_dtype(filtered_df[col]):
                        filtered_df = filtered_df[filtered_df[col] != float(val)]
                    else:
                        filtered_df = filtered_df[filtered_df[col].astype(str) != str(val)]
                elif op == ">":
                    filtered_df = filtered_df[filtered_df[col] > float(val)]
                elif op == "<":
                    filtered_df = filtered_df[filtered_df[col] < float(val)]
                elif op == ">=":
                    filtered_df = filtered_df[filtered_df[col] >= float(val)]
                elif op == "<=":
                    filtered_df = filtered_df[filtered_df[col] <= float(val)]
                elif op == "contains":
                    filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(str(val), case=False, na=False)]
                elif op == "is null":
                    filtered_df = filtered_df[filtered_df[col].isna()]
                elif op == "is not null":
                    filtered_df = filtered_df[filtered_df[col].notna()]
            except Exception:
                pass

            with chip_cols[idx]:
                render_html(
                    f"""
                    <div class="spec-chip" style="margin-bottom: 6px; display: inline-block;">
                        {col} {op} {val}
                    </div>
                    """
                )

        with chip_cols[-1]:
            if st.button("Reset Filters", key="eda_reset_filters_btn"):
                st.session_state.active_filters = []
                st.rerun()

    render_html(
        f"""
        <div class="table-info-bar">
            <span>Filtered Records: <strong>{len(filtered_df):,}</strong> of <strong>{len(df):,}</strong> rows</span>
            <span>{len(filtered_df) / len(df) * 100:.1f}% remaining</span>
        </div>
        """
    )
    st.dataframe(filtered_df, use_container_width=True)
    return filtered_df


# =============================================================================
# 8. TARGET / COMPARISON ANALYSIS
# =============================================================================

def render_target_comparison_analysis(df: pd.DataFrame):
    """Pick target column (e.g. Price) and compare all features against it."""
    target_col = st.selectbox(
        "Select Target Column for Comparative Relationship Analysis",
        options=df.columns.tolist(),
        key="eda_target_col_select",
    )

    if not target_col:
        return

    is_target_num = pd.api.types.is_numeric_dtype(df[target_col])
    other_cols = [c for c in df.columns if c != target_col]

    if not other_cols:
        st.info("No other columns available to compare.")
        return

    st.markdown(
        f"""
        <div style="font-size: 0.84rem; color: #94A3B8; margin-bottom: 0.85rem;">
            Analyzing relationships against Target: <strong>{target_col}</strong> ({'Quantitative' if is_target_num else 'Categorical'}).
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_target_num:
        # Numeric Target: Compute Pearson Correlations
        num_features = df[other_cols].select_dtypes(include=["number"]).columns.tolist()
        if num_features:
            corrs = []
            for nf in num_features:
                valid = df[[nf, target_col]].dropna()
                if len(valid) > 2:
                    r = valid[nf].corr(valid[target_col])
                    corrs.append({"Feature": nf, "Correlation (r)": round(r, 2), "Abs Correlation": abs(r)})
            
            if corrs:
                corr_df = pd.DataFrame(corrs).sort_values(by="Abs Correlation", ascending=False)
                st.markdown("#### Feature Correlation Ranking vs Target")
                st.dataframe(corr_df[["Feature", "Correlation (r)"]], use_container_width=True, hide_index=True)

        # Interactive Bivariate Plot
        compare_col = st.selectbox(
            "Select Feature for Bivariate Plot",
            options=other_cols,
            key="eda_target_bivariate_col",
        )

        if compare_col:
            if pd.api.types.is_numeric_dtype(df[compare_col]):
                fig = px.scatter(
                    df,
                    x=compare_col,
                    y=target_col,
                    trendline="ols",
                    color_discrete_sequence=["#3B82F6"],
                )
                layout = get_plotly_layout(f"Scatter: {compare_col} vs {target_col}", height=380)
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = px.box(
                    df,
                    x=compare_col,
                    y=target_col,
                    color=compare_col,
                )
                layout = get_plotly_layout(f"{target_col} Distribution by {compare_col}", height=380)
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)

    else:
        # Categorical Target
        compare_col = st.selectbox(
            "Select Feature to Compare",
            options=other_cols,
            key="eda_target_cat_bivariate_col",
        )
        if compare_col:
            if pd.api.types.is_numeric_dtype(df[compare_col]):
                fig = px.box(df, x=target_col, y=compare_col, color=target_col)
                layout = get_plotly_layout(f"{compare_col} by {target_col}", height=380)
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)
            else:
                cross = pd.crosstab(df[compare_col], df[target_col])
                fig = px.bar(cross, barmode="group")
                layout = get_plotly_layout(f"{compare_col} vs {target_col} Cross Tabulation", height=380)
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# 9. EXPORT REPORT & CLEANED CSV
# =============================================================================

def render_export_report_section(df: pd.DataFrame, filename: str):
    """Generate downloadable HTML summary report & cleaned CSV."""
    st.markdown("#### Export Analytics Report & Data")

    col1, col2 = st.columns(2)

    with col1:
        # Generate Cleaned CSV
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Cleaned CSV",
            data=csv_bytes,
            file_name=f"cleaned_{filename}",
            mime="text/csv",
            use_container_width=True,
            key="eda_export_csv_btn",
        )

    with col2:
        # Generate Self-Contained HTML Executive Report
        total_rows, total_cols = df.shape
        null_count = int(df.isna().sum().sum())
        dup_count = int(df.duplicated().sum())
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()

        html_report = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Data Studio - EDA Report ({filename})</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #FAFAFA; color: #1E293B; }}
        .header {{ border-bottom: 2px solid #2563EB; padding-bottom: 15px; margin-bottom: 25px; }}
        h1 {{ margin: 0 0 5px 0; color: #0F172A; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }}
        .card {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; }}
        .metric-title {{ font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 700; }}
        .metric-val {{ font-size: 24px; font-weight: 800; color: #0F172A; }}
        table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 15px; }}
        th, td {{ border: 1px solid #E2E8F0; padding: 8px 12px; font-size: 13px; text-align: left; }}
        th {{ background: #F8FAFC; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Exploratory Data Analysis Report</h1>
        <p>Dataset: <strong>{filename}</strong> | Generated by Data Studio</p>
    </div>
    <div class="stats-grid">
        <div class="card"><div class="metric-title">Total Records</div><div class="metric-val">{total_rows:,}</div></div>
        <div class="card"><div class="metric-title">Total Columns</div><div class="metric-val">{total_cols}</div></div>
        <div class="card"><div class="metric-title">Missing Cells</div><div class="metric-val">{null_count:,}</div></div>
        <div class="card"><div class="metric-title">Duplicates</div><div class="metric-val">{dup_count:,}</div></div>
    </div>
    <h2>Numerical Summary</h2>
    {df[num_cols].describe().T.to_html(classes="table") if num_cols else "<p>No numerical fields</p>"}
</body>
</html>
"""
        st.download_button(
            label="Download HTML Executive Report",
            data=html_report.encode("utf-8"),
            file_name=f"eda_report_{filename.split('.')[0]}.html",
            mime="text/html",
            use_container_width=True,
            key="eda_export_html_report_btn",
        )
