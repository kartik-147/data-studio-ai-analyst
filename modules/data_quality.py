"""
Data Quality & Health Analysis Module for Data Studio
Provides deep tabular diagnostics, multi-factor health scoring,
column-level audits, IQR outlier detection, automated anomaly detection,
dynamic data engineering recommendations, and non-destructive cleaning tools.
"""

import io
import os
import textwrap
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
# pyrefly: ignore [missing-import]
import streamlit as st

from modules.config import (
    SAMPLE_DATA_DIR,
    NAV_DATASET,
)

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


def render_html(html_str: str):
    """Render HTML safely without Markdown treating indented lines as code blocks."""
    cleaned = textwrap.dedent(html_str).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


# =============================================================================
# 1. CORE STATISTICAL & DATA QUALITY COMPUTATION ENGINE
# =============================================================================

def compute_iqr_outliers(series: pd.Series) -> Dict[str, Any]:
    """
    Compute outliers for a numerical pandas Series using the IQR (Interquartile Range) method.
    Returns boundary thresholds, outlier counts, and outlier percentage.
    """
    clean_s = series.dropna()
    n_count = len(clean_s)
    if n_count < 4:
        return {
            "outlier_count": 0,
            "outlier_pct": 0.0,
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_bound": None,
            "upper_bound": None,
            "min_val": clean_s.min() if n_count > 0 else None,
            "max_val": clean_s.max() if n_count > 0 else None,
        }

    try:
        q1 = float(clean_s.quantile(0.25))
        q3 = float(clean_s.quantile(0.75))
        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        outliers = clean_s[(clean_s < lower_bound) | (clean_s > upper_bound)]
        outlier_count = int(len(outliers))
        outlier_pct = round((outlier_count / n_count) * 100.0, 2)

        return {
            "outlier_count": outlier_count,
            "outlier_pct": outlier_pct,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "min_val": float(clean_s.min()),
            "max_val": float(clean_s.max()),
        }
    except Exception:
        return {
            "outlier_count": 0,
            "outlier_pct": 0.0,
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_bound": None,
            "upper_bound": None,
            "min_val": None,
            "max_val": None,
        }


def detect_potential_type_mismatches(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Identify columns that might have suboptimal or mismatched data types:
    - Text columns containing numeric data (>80% parseable)
    - Text columns containing ISO/standard dates (>80% parseable)
    - Numeric columns with binary values (0/1) that could be boolean
    - High cardinality string IDs
    """
    type_issues = []
    total_rows = len(df)
    if total_rows == 0:
        return type_issues

    for col in df.columns:
        s = df[col].dropna()
        if len(s) == 0:
            continue

        dtype_str = str(df[col].dtype)

        # 1. Check if string/object column could be numeric
        if dtype_str in ["object", "string"]:
            # Check for empty strings / spaces
            sample_non_empty = [v for v in s.astype(str) if v.strip() != ""]
            if len(sample_non_empty) > 0:
                sample_slice = sample_non_empty[:min(200, len(sample_non_empty))]
                parsed_nums = pd.to_numeric(pd.Series(sample_slice), errors="coerce")
                valid_num_ratio = parsed_nums.notnull().sum() / len(sample_slice)
                if valid_num_ratio >= 0.85:
                    type_issues.append({
                        "column": col,
                        "current_type": dtype_str,
                        "suggested_type": "Numeric (float/int)",
                        "reason": f"~{int(valid_num_ratio*100)}% of text values are parseable as numbers",
                        "severity": "Warning",
                    })
                    continue

                # 2. Check if string/object column could be datetime
                if any(kw in col.lower() for kw in ["date", "time", "created", "updated", "timestamp", "dob", "day", "year", "month"]):
                    try:
                        parsed_dates = pd.to_datetime(pd.Series(sample_slice), errors="coerce", format="mixed")
                        valid_date_ratio = parsed_dates.notnull().sum() / len(sample_slice)
                        if valid_date_ratio >= 0.8:
                            type_issues.append({
                                "column": col,
                                "current_type": dtype_str,
                                "suggested_type": "Datetime",
                                "reason": f"Column name and values match datetime formats (~{int(valid_date_ratio*100)}% parseable)",
                                "severity": "Info",
                            })
                            continue
                    except Exception:
                        pass

        # 3. Check if float column has only integers
        if "float" in dtype_str:
            if s.notnull().all() and (s == s.round()).all():
                type_issues.append({
                    "column": col,
                    "current_type": dtype_str,
                    "suggested_type": "Integer",
                    "reason": "Contains only whole numbers with no decimal values",
                    "severity": "Info",
                })

        # 4. Check for constant/zero-variance columns (only when dataset has multiple rows)
        if total_rows > 1 and s.nunique() <= 1:
            type_issues.append({
                "column": col,
                "current_type": dtype_str,
                "suggested_type": "Drop or Review",
                "reason": "Zero variance / constant column (only 1 distinct value)",
                "severity": "Warning",
            })

    return type_issues


def analyze_dataset_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Perform a complete, dynamic data quality audit across the entire dataset.
    Returns comprehensive metrics, score out of 100, column statistics,
    outliers, duplicates, missing values, anomalies, and recommendations.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "score": 0,
            "status": "No Dataset",
            "badge_class": "badge-rose",
            "color": "#EF4444",
            "factors": ["No active dataset loaded in memory."],
            "total_rows": 0,
            "total_cols": 0,
            "total_cells": 0,
            "null_cells": 0,
            "null_percentage": 0.0,
            "duplicate_rows": 0,
            "duplicate_percentage": 0.0,
            "empty_string_cells": 0,
            "total_outliers": 0,
            "outlier_columns_count": 0,
            "type_issues_count": 0,
            "column_quality_df": pd.DataFrame(),
            "missing_summary_df": pd.DataFrame(),
            "duplicate_df": pd.DataFrame(),
            "outlier_summary_df": pd.DataFrame(),
            "outlier_details": {},
            "issues_list": [],
            "recommendations": [],
            "type_issues": [],
        }

    total_rows, total_cols = df.shape
    total_cells = total_rows * total_cols

    # 1. Missing Values Analysis
    null_counts = df.isnull().sum()
    null_cells = int(null_counts.sum())
    null_percentage = round((null_cells / total_cells * 100.0), 2) if total_cells > 0 else 0.0

    # 2. Duplicate Rows Analysis
    try:
        duplicate_mask = df.duplicated(keep=False)
        duplicate_rows = int(df.duplicated().sum())
        duplicate_df = df[duplicate_mask].copy() if duplicate_rows > 0 else pd.DataFrame()
        duplicate_percentage = round((duplicate_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0
    except Exception:
        duplicate_rows = 0
        duplicate_percentage = 0.0
        duplicate_df = pd.DataFrame()

    # 3. Empty String / Whitespace Cells Analysis (for text columns)
    empty_string_counts = {}
    total_empty_strings = 0
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype) == "string":
            s_valid = df[col].dropna().astype(str)
            empty_count = int((s_valid.str.strip() == "").sum())
            empty_string_counts[col] = empty_count
            total_empty_strings += empty_count
        else:
            empty_string_counts[col] = 0

    # 4. Outlier Detection via IQR
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    outlier_details = {}
    total_outliers = 0
    outlier_cols_with_findings = []
    outlier_records = []

    for col in numeric_cols:
        res = compute_iqr_outliers(df[col])
        outlier_details[col] = res
        cnt = res["outlier_count"]
        if cnt > 0:
            total_outliers += cnt
            outlier_cols_with_findings.append(col)
            outlier_records.append({
                "Column": col,
                "Data Type": str(df[col].dtype),
                "Outliers": cnt,
                "Outlier %": res["outlier_pct"],
                "Lower Bound (IQR)": f"{res['lower_bound']:,.2f}" if res["lower_bound"] is not None else "-",
                "Upper Bound (IQR)": f"{res['upper_bound']:,.2f}" if res["upper_bound"] is not None else "-",
                "Min Value": f"{res['min_val']:,.2f}" if res["min_val"] is not None else "-",
                "Max Value": f"{res['max_val']:,.2f}" if res["max_val"] is not None else "-",
            })

    outlier_summary_df = pd.DataFrame(outlier_records) if outlier_records else pd.DataFrame(
        columns=["Column", "Data Type", "Outliers", "Outlier %", "Lower Bound (IQR)", "Upper Bound (IQR)", "Min Value", "Max Value"]
    )
    if not outlier_summary_df.empty:
        outlier_summary_df = outlier_summary_df.sort_values(by="Outliers", ascending=False)

    # 5. Potential Type Mismatches & Anomalies
    type_issues = detect_potential_type_mismatches(df)
    type_issues_count = len(type_issues)

    # 6. Column-by-Column Detailed Health Records
    column_records = []
    for col in df.columns:
        col_type = str(df[col].dtype)
        col_nulls = int(null_counts[col])
        col_null_pct = round((col_nulls / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        unique_cnt = int(df[col].nunique(dropna=True))
        unique_pct = round((unique_cnt / total_rows * 100.0), 1) if total_rows > 0 else 0.0
        empty_str_cnt = empty_string_counts.get(col, 0)
        
        # Outliers if numeric
        out_cnt = outlier_details.get(col, {}).get("outlier_count", 0) if col in numeric_cols else "-"
        out_pct = outlier_details.get(col, {}).get("outlier_pct", 0.0) if col in numeric_cols else 0.0

        # Quality Status calculation for column
        status = "Good"
        badge_symbol = "🟢"
        if col_null_pct >= 25.0 or (isinstance(out_cnt, int) and out_pct >= 15.0) or (total_rows > 1 and unique_cnt <= 1):
            status = "Needs Attention"
            badge_symbol = "🔴"
        elif col_null_pct > 0.0 or (isinstance(out_cnt, int) and out_cnt > 0) or empty_str_cnt > 0:
            status = "Warning"
            badge_symbol = "🟡"

        dup_val_pct = round(100.0 - unique_pct, 1) if total_rows > 0 else 0.0

        column_records.append({
            "Column Name": col,
            "Data Type": col_type,
            "Missing": col_nulls,
            "Missing %": col_null_pct,
            "Unique": unique_cnt,
            "Unique %": f"{unique_pct}%",
            "Duplicate Values %": f"{dup_val_pct}%",
            "Empty Strings": empty_str_cnt if (col_type == "object" or str(col_type) == "string") else "-",
            "Outliers (IQR)": out_cnt,
            "Status": f"{badge_symbol} {status}",
            "_raw_status": status,
        })

    column_quality_df = pd.DataFrame(column_records)

    # 7. Missing Summary Sorted
    missing_records = []
    for col in df.columns:
        cnt = int(null_counts[col])
        pct = round((cnt / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        missing_records.append({
            "Column": col,
            "Data Type": str(df[col].dtype),
            "Missing Count": cnt,
            "Missing %": pct,
            "Completeness %": round(100.0 - pct, 2),
            "Impact": "Critical (>30%)" if pct > 30 else ("Moderate (>5%)" if pct > 5 else ("Minor (>0%)" if pct > 0 else "Clean (0%)")),
        })
    missing_summary_df = pd.DataFrame(missing_records).sort_values(by="Missing %", ascending=False)

    # =========================================================================
    # 8. WEIGHTED DATA QUALITY SCORE ALGORITHM (0 - 100)
    # =========================================================================
    missing_and_empty_cells = null_cells + total_empty_strings
    missing_and_empty_pct = (missing_and_empty_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    missing_penalty = min(35.0, missing_and_empty_pct * 1.5)

    dup_penalty = min(25.0, duplicate_percentage * 1.8)

    total_numeric_cells = (len(numeric_cols) * total_rows) if numeric_cols else 1
    outlier_cell_pct = (total_outliers / total_numeric_cells * 100.0) if total_numeric_cells > 0 else 0.0
    outlier_penalty = min(20.0, outlier_cell_pct * 2.0)

    type_penalty = min(20.0, type_issues_count * 4.0)

    raw_score = 100.0 - missing_penalty - dup_penalty - outlier_penalty - type_penalty
    final_score = int(max(10, min(100, round(raw_score))))

    if final_score >= 90:
        quality_status = "Excellent"
        badge_class = "badge-emerald"
        status_color = "#10B981"
    elif final_score >= 75:
        quality_status = "Good"
        badge_class = "badge-info"
        status_color = "#3B82F6"
    elif final_score >= 60:
        quality_status = "Fair"
        badge_class = "badge-amber"
        status_color = "#F59E0B"
    else:
        quality_status = "Needs Attention"
        badge_class = "badge-rose"
        status_color = "#EF4444"

    score_factors = []
    if null_cells == 0 and total_empty_strings == 0:
        score_factors.append("✅ <strong>Completeness:</strong> 100% complete dataset with 0 missing or empty string cells.")
    else:
        parts = []
        if null_cells > 0:
            parts.append(f"{null_cells:,} missing cells ({null_percentage}%)")
        if total_empty_strings > 0:
            parts.append(f"{total_empty_strings:,} empty/whitespace strings")
        score_factors.append(f"⚠️ <strong>Completeness:</strong> Found {', '.join(parts)} (-{missing_penalty:.1f} pts).")

    if duplicate_rows == 0:
        score_factors.append("✅ <strong>Uniqueness:</strong> 100% row uniqueness with zero duplicate records detected.")
    else:
        score_factors.append(f"⚠️ <strong>Uniqueness:</strong> {duplicate_rows:,} duplicate rows ({duplicate_percentage}%) detected (-{dup_penalty:.1f} pts).")

    if total_outliers == 0:
        if numeric_cols:
            score_factors.append("✅ <strong>Distribution:</strong> No extreme numerical outliers found across numerical columns.")
        else:
            score_factors.append("ℹ️ <strong>Distribution:</strong> Dataset contains no numerical columns to audit.")
    else:
        score_factors.append(f"⚠️ <strong>Outliers:</strong> Detected {total_outliers:,} potential outliers across {len(outlier_cols_with_findings)} numerical column(s) (-{outlier_penalty:.1f} pts).")

    if type_issues_count == 0:
        score_factors.append("✅ <strong>Schema & Types:</strong> All column data types match their underlying distribution cleanly.")
    else:
        score_factors.append(f"⚠️ <strong>Data Types:</strong> {type_issues_count} potential schema/type optimization(s) found (-{type_penalty:.1f} pts).")

    # =========================================================================
    # 9. STRUCTURED ISSUES & DYNAMIC RECOMMENDATIONS
    # =========================================================================
    issues_list = []
    recommendations = []

    cols_with_nulls = [col for col in df.columns if null_counts[col] > 0]
    for col in cols_with_nulls:
        cnt = int(null_counts[col])
        pct = round(cnt / total_rows * 100.0, 1)
        severity = "Critical" if pct >= 30.0 else "Warning"
        issues_list.append({
            "severity": severity,
            "icon": "🔴" if severity == "Critical" else "🟡",
            "title": f"Column `{col}` contains {cnt:,} missing values ({pct}%)",
            "desc": "Missing entries can skew aggregations or cause model errors.",
        })
        if pct >= 50.0:
            recommendations.append(f"Consider dropping column **`{col}`** or imputing if critical (currently {pct}% null).")
        else:
            recommendations.append(f"Review and handle missing entries in **`{col}`** (e.g. median/mode imputation or record filtering).")

    for col, cnt in empty_string_counts.items():
        if cnt > 0:
            pct = round(cnt / total_rows * 100.0, 1)
            issues_list.append({
                "severity": "Warning",
                "icon": "🟡",
                "title": f"Column `{col}` contains {cnt:,} blank / whitespace-only string values ({pct}%)",
                "desc": "Empty strings can bypass standard null checks and corrupt categoricals.",
            })
            recommendations.append(f"Trim whitespace and convert empty strings in **`{col}`** into explicit null values.")

    if duplicate_rows > 0:
        issues_list.append({
            "severity": "Warning" if duplicate_percentage < 15.0 else "Critical",
            "icon": "🟡" if duplicate_percentage < 15.0 else "🔴",
            "title": f"{duplicate_rows:,} duplicate rows detected ({duplicate_percentage}% of total dataset)",
            "desc": "Duplicate observations inflate sample sizes and distort descriptive statistics.",
        })
        recommendations.append(f"Remove or review the **{duplicate_rows:,} duplicate records** to ensure clean analysis.")

    for col in outlier_cols_with_findings:
        res = outlier_details[col]
        cnt = res["outlier_count"]
        pct = res["outlier_pct"]
        low = res["lower_bound"]
        high = res["upper_bound"]
        issues_list.append({
            "severity": "Warning" if pct < 15.0 else "Critical",
            "icon": "🟡" if pct < 15.0 else "🔴",
            "title": f"Column `{col}` contains {cnt:,} potential numerical outliers ({pct}%)",
            "desc": f"Values fall outside standard 1.5x IQR boundaries [{low:,.2f}, {high:,.2f}].",
        })
        recommendations.append(f"Investigate extreme outliers in **`{col}`** (min: {res['min_val']:,.2f}, max: {res['max_val']:,.2f}) or apply IQR capping.")

    for issue in type_issues:
        issues_list.append({
            "severity": issue["severity"],
            "icon": "ℹ️" if issue["severity"] == "Info" else "🟡",
            "title": f"Column `{issue['column']}`: {issue['reason']}",
            "desc": f"Currently inferred as `{issue['current_type']}`, consider converting to `{issue['suggested_type']}`.",
        })
        recommendations.append(f"Cast **`{issue['column']}`** from `{issue['current_type']}` to `{issue['suggested_type']}` for optimal operations.")

    unique_recommendations = []
    for r in recommendations:
        if r not in unique_recommendations:
            unique_recommendations.append(r)

    return {
        "score": final_score,
        "status": quality_status,
        "badge_class": badge_class,
        "color": status_color,
        "factors": score_factors,
        "total_rows": total_rows,
        "total_cols": total_cols,
        "total_cells": total_cells,
        "null_cells": null_cells,
        "null_percentage": null_percentage,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_percentage,
        "empty_string_cells": total_empty_strings,
        "total_outliers": total_outliers,
        "outlier_columns_count": len(outlier_cols_with_findings),
        "type_issues_count": type_issues_count,
        "column_quality_df": column_quality_df,
        "missing_summary_df": missing_summary_df,
        "duplicate_df": duplicate_df,
        "outlier_summary_df": outlier_summary_df,
        "outlier_details": outlier_details,
        "issues_list": issues_list,
        "recommendations": unique_recommendations,
        "type_issues": type_issues,
    }


# =============================================================================
# 2. NON-DESTRUCTIVE DATA CLEANING WORKBENCH
# =============================================================================

def apply_cleaning_transformations(
    df: pd.DataFrame,
    remove_duplicates: bool = False,
    missing_strategy: str = "None",
    missing_fill_value: str = "Unknown",
    trim_whitespace: bool = False,
    cap_outliers: bool = False,
) -> pd.DataFrame:
    """
    Apply safe, non-destructive cleaning transformations on a copy of the dataset.
    """
    if df is None or df.empty:
        return df

    cleaned_df = df.copy()

    if trim_whitespace:
        for col in cleaned_df.select_dtypes(include=["object"]).columns:
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip().replace("", np.nan)

    if remove_duplicates:
        cleaned_df = cleaned_df.drop_duplicates()

    if missing_strategy == "Drop Rows with Nulls":
        cleaned_df = cleaned_df.dropna()
    elif missing_strategy == "Impute Numeric (Median) & Text (Mode)":
        for col in cleaned_df.columns:
            if cleaned_df[col].isnull().any():
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    median_val = cleaned_df[col].median()
                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                else:
                    mode_series = cleaned_df[col].mode()
                    mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                    cleaned_df[col] = cleaned_df[col].fillna(mode_val)
    elif missing_strategy == "Impute Numeric (Mean) & Text (Mode)":
        for col in cleaned_df.columns:
            if cleaned_df[col].isnull().any():
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    mean_val = cleaned_df[col].mean()
                    cleaned_df[col] = cleaned_df[col].fillna(mean_val)
                else:
                    mode_series = cleaned_df[col].mode()
                    mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                    cleaned_df[col] = cleaned_df[col].fillna(mode_val)
    elif missing_strategy == "Fill with Custom Placeholder":
        cleaned_df = cleaned_df.fillna(missing_fill_value)

    if cap_outliers:
        for col in cleaned_df.select_dtypes(include=["number"]).columns:
            clean_s = cleaned_df[col].dropna()
            if len(clean_s) >= 4:
                q1 = clean_s.quantile(0.25)
                q3 = clean_s.quantile(0.75)
                iqr = q3 - q1
                lower_b = q1 - (1.5 * iqr)
                upper_b = q3 + (1.5 * iqr)
                cleaned_df[col] = cleaned_df[col].clip(lower=lower_b, upper=upper_b)

    return cleaned_df


# =============================================================================
# 3. UI RENDERING COMPONENTS
# =============================================================================

def render_data_quality_score_card(report: Dict[str, Any], is_dark: bool):
    """Render Section 1: Prominent Data Quality Score."""
    score = report["score"]
    status = report["status"]
    color = report["color"]
    factors = report["factors"]
    factors_html = "".join(f"<li style='margin-bottom: 4px;'>{f}</li>" for f in factors)

    render_html(
        f"""
        <div class="feature-card" style="padding: 1.3rem 1.5rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.85rem;">
                <div>
                    <span style="font-size: 0.76rem; font-weight: 700; color: {'#94A3B8' if is_dark else '#64748B'}; text-transform: uppercase; letter-spacing: 0.06em;">Comprehensive Quality Score</span>
                    <h3 style="font-size: 1.25rem; font-weight: 700; color: {'#FFFFFF' if is_dark else '#0F172A'}; margin: 0.15rem 0 0 0;">Dataset Health & Reliability Audit</h3>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="badge" style="background: {color}18; color: {color}; border: 1px solid {color}40; font-size: 0.82rem; font-weight: 700; padding: 0.3rem 0.8rem; border-radius: 6px;">Quality Status: {status}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1.1rem;">
                <div style="display: flex; align-items: baseline; gap: 6px;">
                    <span style="font-size: 3.1rem; font-weight: 800; color: {color}; line-height: 1; font-family: -apple-system, BlinkMacSystemFont, monospace;">{score}</span>
                    <span style="font-size: 1.15rem; color: {'#64748B' if is_dark else '#94A3B8'}; font-weight: 600;">/ 100</span>
                </div>
                <div style="flex: 1; min-width: 220px;">
                    <div style="width: 100%; height: 10px; background: {'#1F2937' if is_dark else '#E2E8F0'}; border-radius: 9999px; overflow: hidden; margin-bottom: 0.4rem;">
                        <div style="width: {score}%; height: 100%; background: {color}; border-radius: 9999px; transition: width 0.3s ease;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: {'#94A3B8' if is_dark else '#64748B'}; font-weight: 600;">
                        <span>0 Critical</span>
                        <span>60 Fair</span>
                        <span>75 Good</span>
                        <span>90+ Excellent</span>
                    </div>
                </div>
            </div>
            <div style="background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 8px; padding: 0.85rem 1rem;">
                <div style="font-size: 0.78rem; font-weight: 700; color: {'#CBD5E1' if is_dark else '#334155'}; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.45rem;">Health Factor Breakdown:</div>
                <ul style="margin: 0; padding-left: 1.15rem; font-size: 0.83rem; color: {'#94A3B8' if is_dark else '#475569'}; line-height: 1.55;">
                    {factors_html}
                </ul>
            </div>
        </div>
        """
    )


def render_data_quality_overview_cards(report: Dict[str, Any]):
    """Render Section 2: Compact Overview Cards."""
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    with kpi1:
        render_html(
            f"""
            <div class="dataset-kpi-card blue-kpi">
                <div class="dataset-kpi-lbl">Total Missing</div>
                <div class="dataset-kpi-val">{report['null_cells']:,}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-info">{report['null_percentage']}% Null</span></div>
            </div>
            """
        )

    with kpi2:
        render_html(
            f"""
            <div class="dataset-kpi-card emerald-kpi">
                <div class="dataset-kpi-lbl">Completeness</div>
                <div class="dataset-kpi-val">{round(100.0 - report['null_percentage'], 1)}%</div>
                <div class="dataset-kpi-badge"><span class="badge badge-emerald">{report['total_cells'] - report['null_cells']:,} Clean Cells</span></div>
            </div>
            """
        )

    with kpi3:
        render_html(
            f"""
            <div class="dataset-kpi-card amber-kpi">
                <div class="dataset-kpi-lbl">Duplicate Rows</div>
                <div class="dataset-kpi-val">{report['duplicate_rows']:,}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-amber">{report['duplicate_percentage']}% Dups</span></div>
            </div>
            """
        )

    with kpi4:
        render_html(
            f"""
            <div class="dataset-kpi-card purple-kpi">
                <div class="dataset-kpi-lbl">Empty Cells</div>
                <div class="dataset-kpi-val">{report['empty_string_cells']:,}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-purple">Blank Strings</span></div>
            </div>
            """
        )

    with kpi5:
        render_html(
            f"""
            <div class="dataset-kpi-card blue-kpi">
                <div class="dataset-kpi-lbl">Numeric Outliers</div>
                <div class="dataset-kpi-val">{report['total_outliers']:,}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-info">{report['outlier_columns_count']} Cols Affected</span></div>
            </div>
            """
        )

    with kpi6:
        render_html(
            f"""
            <div class="dataset-kpi-card amber-kpi">
                <div class="dataset-kpi-lbl">Type Anomalies</div>
                <div class="dataset-kpi-val">{report['type_issues_count']}</div>
                <div class="dataset-kpi-badge"><span class="badge badge-amber">Schema Checks</span></div>
            </div>
            """
        )


def render_column_quality_table_section(report: Dict[str, Any], is_dark: bool):
    """Render Section 3: Detailed Column Quality Table."""
    render_html(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.3rem; margin-bottom: 0.6rem;">
            <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0; color: {'#FFFFFF' if is_dark else '#0F172A'};">📊 Column Quality & Health Breakdown</h4>
            <span style="font-size: 0.78rem; color: {'#94A3B8' if is_dark else '#64748B'};">Audited {report['total_cols']} columns</span>
        </div>
        """
    )

    col_df = report["column_quality_df"]
    if col_df.empty:
        st.info("No columns available to display.")
        return

    f_col1, f_col2, _ = st.columns([1.5, 1.5, 3])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All Columns", "🟢 Good", "🟡 Warning", "🔴 Needs Attention"],
            key="dq_col_status_filter",
            label_visibility="collapsed",
        )
    with f_col2:
        search_query = st.text_input(
            "Search column name",
            placeholder="🔍 Search column...",
            key="dq_col_search_input",
            label_visibility="collapsed",
        )

    filtered_col_df = col_df.copy()
    if status_filter != "All Columns":
        filtered_col_df = filtered_col_df[filtered_col_df["Status"].str.contains(status_filter.split(" ")[1], case=False, na=False)]
    if search_query.strip():
        filtered_col_df = filtered_col_df[filtered_col_df["Column Name"].str.contains(search_query.strip(), case=False, na=False)]

    display_df = filtered_col_df.drop(columns=["_raw_status"], errors="ignore")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Column Name": st.column_config.TextColumn("Column Name", help="Dataset column name", width="medium"),
            "Data Type": st.column_config.TextColumn("Inferred Type", width="small"),
            "Missing": st.column_config.NumberColumn("Null Count", format="%d"),
            "Missing %": st.column_config.ProgressColumn("Missing %", min_value=0, max_value=100, format="%.1f%%"),
            "Unique": st.column_config.NumberColumn("Unique Values", format="%d"),
            "Unique %": st.column_config.TextColumn("Unique Rate"),
            "Duplicate Values %": st.column_config.TextColumn("Duplicate Rate"),
            "Empty Strings": st.column_config.TextColumn("Blank Strings"),
            "Outliers (IQR)": st.column_config.TextColumn("IQR Outliers"),
            "Status": st.column_config.TextColumn("Quality Status", width="medium"),
        },
    )


def render_missing_values_section(report: Dict[str, Any], is_dark: bool):
    """Render Section 4: Missing Values Analysis."""
    render_html(
        f"""
        <div style="margin-top: 1.4rem; margin-bottom: 0.6rem;">
            <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0 0 0.2rem 0; color: {'#FFFFFF' if is_dark else '#0F172A'};">🔍 Missing Values Analysis</h4>
            <p style="font-size: 0.82rem; color: {'#94A3B8' if is_dark else '#64748B'}; margin: 0;">Columns ranked from highest missing percentage to lowest.</p>
        </div>
        """
    )

    missing_df = report["missing_summary_df"]
    null_cols = missing_df[missing_df["Missing Count"] > 0]

    if null_cols.empty:
        render_html(
            f"""
            <div class="alert-banner alert-success" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">✓</div>
                <div class="alert-content">
                    <div class="alert-title">100% Complete Dataset</div>
                    <div class="alert-message">Zero missing or null values detected across all {report['total_cols']} columns and {report['total_rows']:,} records.</div>
                </div>
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div class="alert-banner alert-error" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <div class="alert-title">Missing Values Detected</div>
                    <div class="alert-message">Found <strong>{report['null_cells']:,} missing cells</strong> ({report['null_percentage']}%) across <strong>{len(null_cols)} affected column(s)</strong>.</div>
                </div>
            </div>
            """
        )

        chart_col, table_col = st.columns([1.3, 1.7])
        with chart_col:
            render_html("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 6px;'>Missing % by Affected Column</div>")
            chart_series = null_cols.set_index("Column")["Missing %"]
            st.bar_chart(chart_series, color="#EF4444")

        with table_col:
            render_html("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 6px;'>Missing Values Breakdown Table</div>")
            st.dataframe(
                missing_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Column": st.column_config.TextColumn("Column Name"),
                    "Data Type": st.column_config.TextColumn("Type"),
                    "Missing Count": st.column_config.NumberColumn("Missing Count", format="%d"),
                    "Missing %": st.column_config.ProgressColumn("Missing %", min_value=0, max_value=100, format="%.1f%%"),
                    "Completeness %": st.column_config.ProgressColumn("Completeness", min_value=0, max_value=100, format="%.1f%%"),
                    "Impact": st.column_config.TextColumn("Severity"),
                },
            )


def render_duplicate_analysis_section(report: Dict[str, Any], is_dark: bool):
    """Render Section 5: Duplicate Analysis."""
    render_html(
        f"""
        <div style="margin-top: 1.4rem; margin-bottom: 0.6rem;">
            <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0 0 0.2rem 0; color: {'#FFFFFF' if is_dark else '#0F172A'};">👥 Duplicate Rows Audit</h4>
            <p style="font-size: 0.82rem; color: {'#94A3B8' if is_dark else '#64748B'}; margin: 0;">Assessment of complete record redundancy across all feature dimensions.</p>
        </div>
        """
    )

    dup_count = report["duplicate_rows"]
    dup_pct = report["duplicate_percentage"]
    dup_df = report["duplicate_df"]

    if dup_count == 0:
        render_html(
            f"""
            <div class="alert-banner alert-success" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">✓</div>
                <div class="alert-content">
                    <div class="alert-title">No Duplicates Found</div>
                    <div class="alert-message">Every row in the dataset is uniquely identified (100% uniqueness rate).</div>
                </div>
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div class="alert-banner alert-error" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <div class="alert-title">{dup_count:,} Duplicate Rows Detected ({dup_pct}%)</div>
                    <div class="alert-message">Redundant rows may lead to biased metrics, distorted model weights, and inaccurate data counts. Review the preview below.</div>
                </div>
            </div>
            """
        )

        with st.expander(f"🔍 Inspect Duplicate Records ({len(dup_df)} matching rows preview)", expanded=False):
            st.dataframe(dup_df, use_container_width=True, height=260)


def render_outlier_detection_section(report: Dict[str, Any], df: pd.DataFrame, is_dark: bool):
    """Render Section 6: Outlier Detection using IQR Method."""
    render_html(
        f"""
        <div style="margin-top: 1.4rem; margin-bottom: 0.6rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0 0 0.2rem 0; color: {'#FFFFFF' if is_dark else '#0F172A'};">📈 Numerical Outlier Detection (IQR Method)</h4>
                    <p style="font-size: 0.82rem; color: {'#94A3B8' if is_dark else '#64748B'}; margin: 0;">Identifies data points falling outside <strong>Q1 - 1.5×IQR</strong> and <strong>Q3 + 1.5×IQR</strong>. Non-destructive identification only.</p>
                </div>
                <span class="badge badge-purple" style="font-size: 0.72rem;">Interquartile Range</span>
            </div>
        </div>
        """
    )

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_cols:
        render_html(
            """
            <div class="table-info-bar">
                ℹ️ <strong>No Numerical Columns:</strong> This dataset contains only categorical or text fields. Numerical outlier detection is not applicable.
            </div>
            """
        )
        return

    outlier_df = report["outlier_summary_df"]
    total_outliers = report["total_outliers"]

    if total_outliers == 0 or outlier_df.empty:
        render_html(
            f"""
            <div class="alert-banner alert-success" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">✓</div>
                <div class="alert-content">
                    <div class="alert-title">Clean Numerical Distribution</div>
                    <div class="alert-message">Zero extreme numerical outliers detected across all {len(numeric_cols)} numerical columns using the 1.5× IQR standard.</div>
                </div>
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div class="alert-banner alert-error" style="margin: 0.5rem 0 1rem 0;">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <div class="alert-title">{total_outliers:,} Potential Numerical Outliers Identified</div>
                    <div class="alert-message">Detected across <strong>{report['outlier_columns_count']} numerical columns</strong>. Outliers are reported for audit purposes; original values remain completely untouched.</div>
                </div>
            </div>
            """
        )

        st.dataframe(
            outlier_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Column": st.column_config.TextColumn("Numerical Column", width="medium"),
                "Data Type": st.column_config.TextColumn("Type", width="small"),
                "Outliers": st.column_config.NumberColumn("Outlier Count", format="%d"),
                "Outlier %": st.column_config.ProgressColumn("Outlier %", min_value=0, max_value=100, format="%.1f%%"),
                "Lower Bound (IQR)": st.column_config.TextColumn("Lower Bound"),
                "Upper Bound (IQR)": st.column_config.TextColumn("Upper Bound"),
                "Min Value": st.column_config.TextColumn("Sample Min"),
                "Max Value": st.column_config.TextColumn("Sample Max"),
            },
        )

        with st.expander("🔍 Interactive Outlier Record Inspector", expanded=False):
            insp_col1, insp_col2 = st.columns([1.5, 3.5])
            with insp_col1:
                sel_num_col = st.selectbox(
                    "Select numerical column to inspect",
                    options=outlier_df["Column"].tolist(),
                    key="dq_outlier_inspect_col_select",
                )
            with insp_col2:
                if sel_num_col:
                    details = report["outlier_details"].get(sel_num_col, {})
                    low_b = details.get("lower_bound")
                    high_b = details.get("upper_bound")
                    if low_b is not None and high_b is not None:
                        outlier_mask = (df[sel_num_col] < low_b) | (df[sel_num_col] > high_b)
                        outlier_rows = df[outlier_mask]
                        render_html(f"<div style='font-size: 0.8rem; color: #94A3B8; margin-top: 6px;'>Found <strong>{len(outlier_rows):,} rows</strong> in <code>{sel_num_col}</code> outside range <strong>[{low_b:,.2f}, {high_b:,.2f}]</strong></div>")
                        st.dataframe(outlier_rows.head(50), use_container_width=True, height=200)


def render_issues_and_recommendations_section(report: Dict[str, Any], is_dark: bool):
    """Render Section 7 (Issues Found) and Section 8 (Recommended Actions)."""
    col_issues, col_recs = st.columns([1.1, 1.1])

    with col_issues:
        issues = report["issues_list"]
        if not issues:
            body_html = f"""
            <div style="padding: 1rem; background: {'#0B0F17' if is_dark else '#F0FDF4'}; border: 1px solid {'#1E293B' if is_dark else '#BBF7D0'}; border-radius: 8px; color: {'#34D399' if is_dark else '#047857'}; font-size: 0.85rem; line-height: 1.45;">
                ✨ <strong>No major data quality issues detected.</strong> Your dataset is clean, complete, and ready for advanced analysis.
            </div>
            """
        else:
            items_html = "".join(
                f"""
                <div style="padding: 0.65rem 0.75rem; background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; margin-bottom: 0.5rem; font-size: 0.82rem;">
                    <div style="font-weight: 700; color: {'#F1F5F9' if is_dark else '#0F172A'}; margin-bottom: 2px;">{item['icon']} {item['title']}</div>
                    <div style="font-size: 0.76rem; color: {'#94A3B8' if is_dark else '#64748B'}; line-height: 1.35;">{item['desc']}</div>
                </div>
                """
                for item in issues[:6]
            )
            extra_msg = f"<div style='font-size: 0.75rem; color: #94A3B8; text-align: center;'>+ {len(issues)-6} additional minor issues identified in table above</div>" if len(issues) > 6 else ""
            body_html = f"{items_html}{extra_msg}"

        render_html(
            f"""
            <div class="feature-card" style="padding: 1.2rem; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="font-size: 0.88rem; font-weight: 700; color: {'#FFFFFF' if is_dark else '#0F172A'};">⚠️ Data Quality Issues Found</div>
                    <span class="badge badge-amber" style="font-size: 0.7rem;">{len(report['issues_list'])} Issues</span>
                </div>
                {body_html}
            </div>
            """
        )

    with col_recs:
        recs = report["recommendations"]
        if not recs:
            body_html = f"""
            <div style="padding: 1rem; background: {'#0B0F17' if is_dark else '#EFF6FF'}; border: 1px solid {'#1E293B' if is_dark else '#DBEAFE'}; border-radius: 8px; color: {'#60A5FA' if is_dark else '#1D4ED8'}; font-size: 0.85rem; line-height: 1.45;">
                💡 <strong>Ready for EDA:</strong> No remediation required. You can proceed directly to the <strong>Visualization</strong> or <strong>AI Analyst</strong> workspaces.
            </div>
            """
        else:
            items_html = "".join(
                f"""
                <div style="display: flex; align-items: flex-start; gap: 8px; padding: 0.65rem 0.75rem; background: {'#0B0F17' if is_dark else '#F8FAFC'}; border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'}; border-radius: 6px; margin-bottom: 0.5rem; font-size: 0.82rem; color: {'#E2E8F0' if is_dark else '#1E293B'};">
                    <span style="color: #2563EB; font-weight: bold; font-size: 1rem; line-height: 1.1;">•</span>
                    <div style="flex: 1; line-height: 1.4;">{r}</div>
                </div>
                """
                for r in recs[:6]
            )
            extra_msg = f"<div style='font-size: 0.75rem; color: #94A3B8; text-align: center;'>+ {len(recs)-6} additional suggestions</div>" if len(recs) > 6 else ""
            body_html = f"{items_html}{extra_msg}"

        render_html(
            f"""
            <div class="feature-card" style="padding: 1.2rem; height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="font-size: 0.88rem; font-weight: 700; color: {'#FFFFFF' if is_dark else '#0F172A'};">🎯 Recommended Actions</div>
                    <span class="badge badge-purple" style="font-size: 0.7rem;">Automated Plan</span>
                </div>
                {body_html}
            </div>
            """
        )


def render_clean_data_action_section(df: pd.DataFrame, filename: str, is_dark: bool):
    """
    Render Section 9: Safe, Non-Destructive Clean Data Action Tools.
    Permits optional duplicate removal, missing value handling, empty string trimming,
    and outlier capping on a working copy with before/after comparison and CSV download.
    Original dataset is never modified without explicit user apply/confirmation.
    """
    render_html(
        f"""
        <div style="margin-top: 1.8rem; margin-bottom: 0.8rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0 0 0.2rem 0; color: {'#FFFFFF' if is_dark else '#0F172A'};">🧹 Non-Destructive Data Cleaning Workbench</h4>
                    <p style="font-size: 0.82rem; color: {'#94A3B8' if is_dark else '#64748B'}; margin: 0;">Configure transformation recipes to clean a working copy. The original uploaded dataset is safely preserved.</p>
                </div>
                <span class="badge badge-emerald" style="font-size: 0.72rem;">Safe Working Copy</span>
            </div>
        </div>
        """
    )

    if "df_original" not in st.session_state or st.session_state.get("uploaded_file_name_orig") != filename:
        st.session_state.df_original = df.copy()
        st.session_state.uploaded_file_name_orig = filename

    with st.container():
        render_html(
            """
            <div class="feature-card" style="padding: 1.2rem 1.4rem; margin-bottom: 1rem;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.8rem;">Cleaning Recipe Configuration</div>
            </div>
            """
        )

        c_opt1, c_opt2, c_opt3 = st.columns(3)

        with c_opt1:
            clean_dups = st.checkbox(
                "Remove Duplicate Rows",
                value=False,
                key="dq_clean_opt_dups",
                help="Drops all subsequent exact row duplicates.",
            )
            clean_trim = st.checkbox(
                "Trim Whitespace & Normalize Blanks",
                value=False,
                key="dq_clean_opt_trim",
                help="Strips leading/trailing spaces and converts empty strings to NaN.",
            )

        with c_opt2:
            missing_strat = st.selectbox(
                "Handle Missing Values",
                options=[
                    "None (Keep as-is)",
                    "Drop Rows with Nulls",
                    "Impute Numeric (Median) & Text (Mode)",
                    "Impute Numeric (Mean) & Text (Mode)",
                    "Fill with Custom Placeholder",
                ],
                index=0,
                key="dq_clean_opt_missing_strat",
            )
            custom_fill = "Unknown"
            if missing_strat == "Fill with Custom Placeholder":
                custom_fill = st.text_input("Custom fill placeholder", value="Unknown", key="dq_clean_custom_fill_val")

        with c_opt3:
            clean_outliers = st.checkbox(
                "Cap Numerical Outliers (IQR Winsorize)",
                value=False,
                key="dq_clean_opt_outliers",
                help="Clips extreme values to lower and upper 1.5x IQR boundaries.",
            )

        st.write("")

        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.5, 1.8, 1.8, 1.4])

        with btn_col1:
            preview_clean_clicked = st.button(
                "👁️ Preview Clean Data",
                key="dq_btn_preview_clean",
                use_container_width=True,
            )

        cleaned_df = apply_cleaning_transformations(
            df=df,
            remove_duplicates=clean_dups,
            missing_strategy=missing_strat,
            missing_fill_value=custom_fill,
            trim_whitespace=clean_trim,
            cap_outliers=clean_outliers,
        )

        if preview_clean_clicked or st.session_state.get("dq_preview_active", False):
            st.session_state.dq_preview_active = True

        with btn_col2:
            clean_csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
            base_name = os.path.splitext(filename)[0]
            st.download_button(
                label="📥 Download Cleaned CSV",
                data=clean_csv_bytes,
                file_name=f"{base_name}_cleaned.csv",
                mime="text/csv",
                key="dq_btn_download_clean_csv",
                use_container_width=True,
            )

        with btn_col3:
            if st.button("✨ Apply to Active Workspace", key="dq_btn_apply_to_workspace", use_container_width=True):
                st.session_state.df = cleaned_df
                add_activity_log("🧹", "Cleaned dataset", f"Applied transformations ({len(cleaned_df):,} rows)")
                st.toast("✅ Cleaned dataset applied to active workspace!", icon="✨")
                st.session_state.dq_preview_active = False
                st.rerun()

        with btn_col4:
            if st.button("↺ Reset Original", key="dq_btn_reset_original", use_container_width=True, help="Restores pristine uploaded dataset"):
                st.session_state.df = st.session_state.df_original.copy()
                add_activity_log("↺", "Reset dataset", "Restored pristine uploaded dataset")
                st.toast("Restored original dataset!", icon="↺")
                st.session_state.dq_preview_active = False
                st.rerun()

        if st.session_state.get("dq_preview_active", False):
            orig_rows, orig_cols = df.shape
            orig_nulls = int(df.isnull().sum().sum())
            orig_dups = int(df.duplicated().sum())

            new_rows, new_cols = cleaned_df.shape
            new_nulls = int(cleaned_df.isnull().sum().sum())
            new_dups = int(cleaned_df.duplicated().sum())

            render_html(
                f"""
                <div style="margin-top: 1rem; padding: 0.9rem 1.1rem; background: {'#0B0F17' if is_dark else '#F0FDF4'}; border: 1px solid {'#1E293B' if is_dark else '#BBF7D0'}; border-radius: 8px;">
                    <div style="font-size: 0.84rem; font-weight: 700; color: {'#34D399' if is_dark else '#047857'}; margin-bottom: 0.4rem;">Before vs After Transformation Comparison:</div>
                    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.8rem; color: {'#E2E8F0' if is_dark else '#1E293B'};">
                        <div><strong>Rows:</strong> {orig_rows:,} → <strong>{new_rows:,}</strong> ({new_rows - orig_rows:+d})</div>
                        <div><strong>Missing Cells:</strong> {orig_nulls:,} → <strong>{new_nulls:,}</strong> ({new_nulls - orig_nulls:+d})</div>
                        <div><strong>Duplicates:</strong> {orig_dups:,} → <strong>{new_dups:,}</strong> ({new_dups - orig_dups:+d})</div>
                    </div>
                </div>
                """
            )

            st.write("")
            render_html("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 4px;'>Cleaned Dataset Preview (First 50 rows)</div>")
            st.dataframe(cleaned_df.head(50), use_container_width=True, height=220)


# =============================================================================
# 4. MAIN ENTRY POINT FOR DATA QUALITY TAB
# =============================================================================

def render_data_quality_section(df: Optional[pd.DataFrame] = None, filename: Optional[str] = None):
    """
    Main entry point to render the complete Data Quality section.
    Handles empty state gracefully and dynamically audits any uploaded dataset.
    """
    if df is None:
        df = st.session_state.get("df")
    if filename is None:
        filename = st.session_state.get("uploaded_file_name", "dataset")

    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        render_html(
            """
            <div class="empty-upload-card">
                <div class="empty-upload-icon">🛡️</div>
                <div class="empty-upload-title">No Dataset Loaded for Quality Analysis</div>
                <div class="empty-upload-desc">Please upload a CSV or Excel dataset on the <strong>Dataset Explorer</strong> page to run the comprehensive Data Quality & Health Audit.</div>
                <div class="empty-upload-specs">
                    <div class="spec-chip">CSV (.csv)</div>
                    <div class="spec-chip">Excel (.xlsx, .xls)</div>
                    <div class="spec-chip">Automated IQR Outliers</div>
                    <div class="spec-chip">Health Scoring</div>
                </div>
            </div>
            """
        )
        st.write("")
        col1, _, _ = st.columns([1.5, 1.5, 3])
        with col1:
            if st.button("📁 Go to Dataset Explorer", key="dq_empty_nav_btn", use_container_width=True):
                st.session_state.current_page = NAV_DATASET
                st.rerun()
        return

    with st.spinner("Analyzing dataset health and computing quality metrics..."):
        report = analyze_dataset_quality(df)

    # 1. Data Quality Score
    render_data_quality_score_card(report, is_dark=is_dark)

    # 2. Data Quality Overview Cards
    render_data_quality_overview_cards(report)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 3. Column Quality Table
    render_column_quality_table_section(report, is_dark=is_dark)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 4. Missing Values Analysis
    render_missing_values_section(report, is_dark=is_dark)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 5. Duplicate Analysis
    render_duplicate_analysis_section(report, is_dark=is_dark)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 6. Outlier Detection
    render_outlier_detection_section(report, df=df, is_dark=is_dark)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 7. Data Quality Issues & 8. Recommended Actions
    render_issues_and_recommendations_section(report, is_dark=is_dark)

    st.write("")
    render_html("<div class='section-divider' style='margin: 1.4rem 0 1.2rem 0;'></div>")

    # 9. Clean Data Action Workbench
    render_clean_data_action_section(df, filename=filename, is_dark=is_dark)
