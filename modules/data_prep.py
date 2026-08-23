"""
Data Preparation Module for Data Studio
Comprehensive data cleaning, transformation, filtering, and preparation.

Architecture:
- Dual dataset states: original_df (immutable raw data) and working_df (interactive staging)
- Transformation history, undo stack, redo stack, and active filters
- Propagates to st.session_state.df on "Apply Changes"
- 100% Vector icons (Lucide SVGs), zero emojis, full light/dark theme support
"""

import os
import re
import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

import modules.config as config
from modules.config import (
    # pyrefly: ignore [parse-error]
    APP_NAME,)
from modules.icons import icon_svg, icon_with_text


def render_html(html_str: str):
    """Render HTML safely without Markdown treating indented lines as code blocks."""
    lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    cleaned = "".join(lines)
    st.markdown(cleaned, unsafe_allow_html=True)


# =============================================================================
# 1. STATE & HISTORY ENGINE
# =============================================================================

def get_original_df() -> Optional[pd.DataFrame]:
    """Retrieve immutable original dataset."""
    return st.session_state.get("original_df")


def get_working_df() -> Optional[pd.DataFrame]:
    """Retrieve interactive working dataset."""
    df = st.session_state.get("working_df")
    if df is None and st.session_state.get("df") is not None:
        # Auto-initialize working_df and original_df if missing
        raw = st.session_state.df.copy(deep=True)
        st.session_state.original_df = raw.copy(deep=True)
        st.session_state.working_df = raw.copy(deep=True)
        st.session_state.transformation_history = []
        st.session_state.undo_stack = []
        st.session_state.redo_stack = []
        st.session_state.has_unsaved_changes = False
        return st.session_state.working_df
    return df


def push_undo_state():
    """Snapshot current working_df to undo stack before a transformation."""
    if "undo_stack" not in st.session_state:
        st.session_state.undo_stack = []
    if "working_df" in st.session_state and st.session_state.working_df is not None:
        # Keep up to 15 undo snapshots
        st.session_state.undo_stack.append(st.session_state.working_df.copy(deep=True))
        if len(st.session_state.undo_stack) > 15:
            st.session_state.undo_stack.pop(0)
    # Clear redo stack on new action
    st.session_state.redo_stack = []
    st.session_state.has_unsaved_changes = True


def apply_undo():
    """Revert working_df to previous snapshot."""
    if st.session_state.get("undo_stack"):
        current = st.session_state.working_df.copy(deep=True)
        st.session_state.redo_stack.append(current)
        prev = st.session_state.undo_stack.pop()
        st.session_state.working_df = prev
        st.session_state.has_unsaved_changes = True
        record_transformation("Undo", "All", len(prev), "Reverted previous transformation")
        st.rerun()


def apply_redo():
    """Redo previously reverted snapshot."""
    if st.session_state.get("redo_stack"):
        current = st.session_state.working_df.copy(deep=True)
        st.session_state.undo_stack.append(current)
        next_df = st.session_state.redo_stack.pop()
        st.session_state.working_df = next_df
        st.session_state.has_unsaved_changes = True
        record_transformation("Redo", "All", len(next_df), "Re-applied transformation")
        st.rerun()


def reset_to_original():
    """Reset working_df back to the original dataset."""
    orig = get_original_df()
    if orig is not None:
        push_undo_state()
        st.session_state.working_df = orig.copy(deep=True)
        st.session_state.has_unsaved_changes = True
        record_transformation("Reset", "All", len(orig), "Restored working dataset to raw original state")
        st.rerun()


def record_transformation(action_type: str, column: str, rows_affected: int, details: str):
    """Log an event in transformation history."""
    if "transformation_history" not in st.session_state:
        st.session_state.transformation_history = []
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "action": action_type,
        "column": column,
        "rows_affected": rows_affected,
        "details": details,
    }
    st.session_state.transformation_history.insert(0, entry)
    # Keep up to 30 history records
    st.session_state.transformation_history = st.session_state.transformation_history[:30]


def apply_changes_to_active():
    """Validate and commit working_df to st.session_state.df for all EDA modules."""
    from modules.config import add_activity_log
    working = get_working_df()
    if working is not None:
        st.session_state.df = working.copy(deep=True)
        st.session_state.has_unsaved_changes = False
        add_activity_log("sliders", "Applied Data Prep", f"Updated active dataset ({len(working):,} rows, {len(working.columns)} cols)")
        st.toast("Changes applied! All analysis modules are now using the cleaned dataset.", icon="✅")
        st.rerun()


# =============================================================================
# 2. METRICS & CHANGES COMPARISON ENGINE
# =============================================================================

def calculate_dataset_metrics(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """Compute core summary & data quality metrics for dataset comparison."""
    if df is None or df.empty:
        return {
            "rows": 0,
            "columns": 0,
            "total_cells": 0,
            "missing_cells": 0,
            "missing_pct": 0.0,
            "duplicate_rows": 0,
            "duplicate_pct": 0.0,
            "numeric_cols": 0,
            "categorical_cols": 0,
            "quality_score": 0,
            "memory_mb": 0.0,
        }

    rows = len(df)
    cols = len(df.columns)
    total_cells = rows * cols
    missing_cells = int(df.isna().sum().sum())
    missing_pct = round((missing_cells / total_cells * 100), 2) if total_cells > 0 else 0.0
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / rows * 100), 2) if rows > 0 else 0.0
    numeric_cols = len(df.select_dtypes(include=["number"]).columns)
    categorical_cols = cols - numeric_cols
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    # Simplified Quality Score Engine (0-100)
    score = 100
    if missing_pct > 0:
        score -= min(40, int(missing_pct * 1.5))
    if duplicate_pct > 0:
        score -= min(25, int(duplicate_pct * 2.0))
    if cols < 2:
        score -= 10
    score = max(5, min(100, score))

    return {
        "rows": rows,
        "columns": cols,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": duplicate_pct,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "quality_score": score,
        "memory_mb": round(memory_mb, 2),
    }


def render_compact_summary(orig_m: Dict[str, Any], work_m: Dict[str, Any], filename: str):
    """Render compact, high-density summary strip (no oversized rounded cards)."""
    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    bg_strip = "#111827" if is_dark else "#F8FAFC"
    border_color = "#1E293B" if is_dark else "#E2E8F0"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    muted_color = "#94A3B8" if is_dark else "#64748B"

    render_html(
        f"""
        <div style="background: {bg_strip}; border: 1px solid {border_color}; border-radius: 8px; padding: 0.75rem 1.1rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="color: #2563EB;">{icon_svg("database", size=18)}</span>
                    <div>
                        <div style="font-size: 0.88rem; font-weight: 700; color: {text_color};">{filename}</div>
                        <div style="font-size: 0.72rem; color: {muted_color};">Working Staging Area &bull; {work_m['memory_mb']} MB RAM</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 1.25rem; font-size: 0.8rem; font-family: var(--font-mono);">
                    <div><span style="color: {muted_color}; font-family: var(--font-body);">Rows:</span> <strong>{work_m['rows']:,}</strong></div>
                    <div><span style="color: {muted_color}; font-family: var(--font-body);">Columns:</span> <strong>{work_m['columns']}</strong></div>
                    <div><span style="color: {muted_color}; font-family: var(--font-body);">Missing:</span> <strong style="color: {'#EF4444' if work_m['missing_cells'] > 0 else '#10B981'};">{work_m['missing_cells']:,} ({work_m['missing_pct']}%)</strong></div>
                    <div><span style="color: {muted_color}; font-family: var(--font-body);">Duplicates:</span> <strong style="color: {'#EF4444' if work_m['duplicate_rows'] > 0 else '#10B981'};">{work_m['duplicate_rows']:,}</strong></div>
                    <div>
                        <span style="color: {muted_color}; font-family: var(--font-body);">Health:</span> 
                        <span class="badge" style="background: {'rgba(16, 185, 129, 0.15)' if work_m['quality_score']>=80 else ('rgba(245, 158, 11, 0.15)' if work_m['quality_score']>=60 else 'rgba(239, 68, 68, 0.15)')}; color: {'#10B981' if work_m['quality_score']>=80 else ('#F59E0B' if work_m['quality_score']>=60 else '#EF4444')}; font-weight: 700;">{work_m['quality_score']}/100</span>
                    </div>
                </div>
            </div>
        </div>
        """
    )


def render_changes_comparison(orig_m: Dict[str, Any], work_m: Dict[str, Any]):
    """Render subtle before/after comparison grid with delta indicators."""
    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    delta_rows = work_m["rows"] - orig_m["rows"]
    delta_cols = work_m["columns"] - orig_m["columns"]
    delta_missing = work_m["missing_cells"] - orig_m["missing_cells"]
    delta_dups = work_m["duplicate_rows"] - orig_m["duplicate_rows"]
    delta_score = work_m["quality_score"] - orig_m["quality_score"]

    def fmt_delta(val: int, positive_is_good: bool = True) -> str:
        if val == 0:
            return "<span style='color: #94A3B8; font-size: 0.72rem;'>0 (No change)</span>"
        color = "#10B981" if (val > 0 if positive_is_good else val < 0) else "#EF4444"
        sign = "+" if val > 0 else ""
        return f"<span style='color: {color}; font-weight: 700; font-size: 0.72rem;'>{sign}{val:,}</span>"

    comp_items = [
        {"metric": "Total Rows", "orig": f"{orig_m['rows']:,}", "work": f"{work_m['rows']:,}", "delta": fmt_delta(delta_rows, positive_is_good=True)},
        {"metric": "Columns", "orig": f"{orig_m['columns']}", "work": f"{work_m['columns']}", "delta": fmt_delta(delta_cols, positive_is_good=True)},
        {"metric": "Missing Values", "orig": f"{orig_m['missing_cells']:,}", "work": f"{work_m['missing_cells']:,}", "delta": fmt_delta(delta_missing, positive_is_good=False)},
        {"metric": "Duplicate Rows", "orig": f"{orig_m['duplicate_rows']:,}", "work": f"{work_m['duplicate_rows']:,}", "delta": fmt_delta(delta_dups, positive_is_good=False)},
        {"metric": "Quality Score", "orig": f"{orig_m['quality_score']}/100", "work": f"{work_m['quality_score']}/100", "delta": fmt_delta(delta_score, positive_is_good=True)},
    ]

    card_bg = "#111827" if is_dark else "#FFFFFF"
    border_color = "#1E293B" if is_dark else "#E2E8F0"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    muted = "#94A3B8" if is_dark else "#64748B"

    cols = st.columns(len(comp_items))
    for idx, item in enumerate(comp_items):
        with cols[idx]:
            render_html(
                f"""
                <div style="background: {card_bg}; border: 1px solid {border_color}; border-radius: 6px; padding: 0.55rem 0.75rem; text-align: left;">
                    <div style="font-size: 0.72rem; color: {muted}; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;">{item['metric']}</div>
                    <div style="display: flex; align-items: baseline; justify-content: space-between; font-family: var(--font-mono);">
                        <span style="font-size: 0.95rem; font-weight: 700; color: {text_color};">{item['work']}</span>
                        <span style="font-size: 0.72rem; color: {muted};">Orig: {item['orig']}</span>
                    </div>
                    <div style="margin-top: 3px; font-family: var(--font-mono);">{item['delta']}</div>
                </div>
                """
            )


# =============================================================================
# 3. SMART CLEANING RECOMMENDATIONS
# =============================================================================

def get_smart_recommendations(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Scan working_df for data-driven diagnostics and actionable recommendations."""
    recs = []
    total_rows = len(df)
    if total_rows == 0:
        return recs

    # 1. Duplicates
    dups = int(df.duplicated().sum())
    if dups > 0:
        pct = round((dups / total_rows) * 100, 1)
        recs.append({
            "type": "duplicate",
            "title": f"{dups:,} Duplicate Rows Detected ({pct}%)",
            "desc": f"Found {dups} identical rows across all columns. Removing duplicates improves model accuracy and reporting integrity.",
            "action_label": "Remove Duplicates",
            "action_id": "smart_drop_dups",
            "severity": "medium" if pct < 10 else "high",
        })

    # 2. High Null Columns (>50%)
    null_counts = df.isna().sum()
    high_nulls = null_counts[null_counts / total_rows >= 0.5]
    if not high_nulls.empty:
        col_names = ", ".join(f"'{c}'" for c in high_nulls.index[:3])
        recs.append({
            "type": "high_nulls",
            "title": f"High Missing Values in {len(high_nulls)} Column(s)",
            "desc": f"Columns ({col_names}) have over 50% missing data. Dropping sparse columns prevents skewed estimations.",
            "action_label": f"Drop {len(high_nulls)} Sparse Column(s)",
            "action_id": "smart_drop_high_nulls",
            "severity": "high",
            "cols": list(high_nulls.index),
        })

    # 3. Moderate Null Columns (impute candidate)
    mod_nulls = null_counts[(null_counts / total_rows > 0) & (null_counts / total_rows < 0.5)]
    if not mod_nulls.empty:
        recs.append({
            "type": "mod_nulls",
            "title": f"Missing Data in {len(mod_nulls)} Column(s)",
            "desc": f"{len(mod_nulls)} column(s) have moderate missing values. Impute with median (numeric) or mode (categorical).",
            "action_label": "Impute All Missing",
            "action_id": "smart_impute_all",
            "severity": "low",
        })

    # 4. Numeric Stored as Object/String
    object_cols = df.select_dtypes(include=["object"]).columns
    convertible_numeric = []
    for c in object_cols:
        sample = df[c].dropna().head(20)
        if len(sample) > 0:
            cleaned_s = sample.astype(str).str.replace(r"[^\d.-]", "", regex=True)
            try:
                num_parsed = pd.to_numeric(cleaned_s, errors="coerce")
                if num_parsed.notna().sum() >= len(sample) * 0.8:
                    convertible_numeric.append(c)
            except Exception:
                pass

    if convertible_numeric:
        col_list = ", ".join(f"'{c}'" for c in convertible_numeric[:3])
        recs.append({
            "type": "type_cast",
            "title": f"Numeric Data in Text Columns ({len(convertible_numeric)})",
            "desc": f"Columns ({col_list}) appear to contain numerical values formatted as text strings.",
            "action_label": f"Cast {len(convertible_numeric)} Column(s) to Numeric",
            "action_id": "smart_cast_numeric",
            "severity": "medium",
            "cols": convertible_numeric,
        })

    # 5. Outliers in Numeric Columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    outlier_cols = []
    for c in numeric_cols:
        clean_s = df[c].dropna()
        if len(clean_s) >= 8:
            q1 = clean_s.quantile(0.25)
            q3 = clean_s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                out_cnt = ((clean_s < (q1 - 1.5 * iqr)) | (clean_s > (q3 + 1.5 * iqr))).sum()
                if out_cnt > 0 and (out_cnt / len(clean_s)) >= 0.03:
                    outlier_cols.append((c, out_cnt))

    if outlier_cols:
        top_col, cnt = outlier_cols[0]
        recs.append({
            "type": "outlier",
            "title": f"Outliers in {len(outlier_cols)} Numeric Column(s)",
            "desc": f"Column '{top_col}' has {cnt} values outside standard IQR fences. Consider capping or reviewing.",
            "action_label": "Review Outliers Tab",
            "action_id": "smart_goto_outliers",
            "severity": "low",
        })

    return recs


def render_smart_recommendations(recs: List[Dict[str, Any]], df: pd.DataFrame):
    """Render clean diagnostic recommendation cards with instant triggers."""
    if not recs:
        return

    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    card_bg = "#111827" if is_dark else "#FFFFFF"
    border_color = "#1E293B" if is_dark else "#E2E8F0"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    muted = "#94A3B8" if is_dark else "#64748B"

    st.markdown("#### Smart Cleaning Diagnostics")
    
    rec_cols = st.columns(min(len(recs), 3))
    for idx, rec in enumerate(recs[:3]):
        with rec_cols[idx]:
            border_accent = "#EF4444" if rec["severity"] == "high" else ("#F59E0B" if rec["severity"] == "medium" else "#3B82F6")
            render_html(
                f"""
                <div style="background: {card_bg}; border: 1px solid {border_color}; border-left: 3px solid {border_accent}; border-radius: 6px; padding: 0.75rem 0.9rem; height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-size: 0.84rem; font-weight: 700; color: {text_color}; margin-bottom: 3px;">{rec['title']}</div>
                        <div style="font-size: 0.74rem; color: {muted}; line-height: 1.4; margin-bottom: 0.75rem;">{rec['desc']}</div>
                    </div>
                </div>
                """
            )
            
            # Action button
            if rec["action_id"] == "smart_drop_dups":
                if st.button(rec["action_label"], key=f"rec_btn_{idx}", use_container_width=True):
                    push_undo_state()
                    old_len = len(df)
                    st.session_state.working_df = df.drop_duplicates().reset_index(drop=True)
                    new_len = len(st.session_state.working_df)
                    record_transformation("Drop Duplicates", "All", old_len - new_len, "Removed duplicate rows across all columns")
                    st.rerun()

            elif rec["action_id"] == "smart_drop_high_nulls":
                if st.button(rec["action_label"], key=f"rec_btn_{idx}", use_container_width=True):
                    push_undo_state()
                    cols_to_drop = rec.get("cols", [])
                    st.session_state.working_df = df.drop(columns=cols_to_drop)
                    record_transformation("Drop Columns", ", ".join(cols_to_drop), 0, f"Dropped {len(cols_to_drop)} columns with >50% nulls")
                    st.rerun()

            elif rec["action_id"] == "smart_impute_all":
                if st.button(rec["action_label"], key=f"rec_btn_{idx}", use_container_width=True):
                    push_undo_state()
                    w_df = df.copy()
                    for col in w_df.columns:
                        if w_df[col].isna().sum() > 0:
                            if pd.api.types.is_numeric_dtype(w_df[col]):
                                med = w_df[col].median()
                                w_df[col] = w_df[col].fillna(med)
                            else:
                                mode_val = w_df[col].mode()
                                fill_v = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                                w_df[col] = w_df[col].fillna(fill_v)
                    st.session_state.working_df = w_df
                    record_transformation("Impute Missing", "All", int(df.isna().sum().sum()), "Imputed numerical with median and categorical with mode")
                    st.rerun()

            elif rec["action_id"] == "smart_cast_numeric":
                if st.button(rec["action_label"], key=f"rec_btn_{idx}", use_container_width=True):
                    push_undo_state()
                    w_df = df.copy()
                    for c in rec.get("cols", []):
                        cleaned_s = w_df[c].astype(str).str.replace(r"[^\d.-]", "", regex=True)
                        w_df[c] = pd.to_numeric(cleaned_s, errors="coerce")
                    st.session_state.working_df = w_df
                    record_transformation("Cast Types", ", ".join(rec.get("cols", [])), len(w_df), "Converted string columns to numeric")
                    st.rerun()

    st.write("")


# =============================================================================
# 4. ACTION CONTROL BAR (Apply, Undo, Redo, Reset)
# =============================================================================

def render_action_control_bar():
    """Render top sticky action bar with Unsaved Changes indicator and Undo/Redo/Apply."""
    has_unsaved = st.session_state.get("has_unsaved_changes", False)
    undo_count = len(st.session_state.get("undo_stack", []))
    redo_count = len(st.session_state.get("redo_stack", []))
    
    col_status, col_undo, col_redo, col_reset, col_apply = st.columns([3.2, 0.9, 0.9, 1.2, 1.4])

    with col_status:
        if has_unsaved:
            render_html(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; height: 100%; padding-top: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #F59E0B;"></span>
                    <span style="font-size: 0.82rem; font-weight: 600; color: #F59E0B;">Unsaved Changes in Staging Area</span>
                    <span style="font-size: 0.72rem; color: #94A3B8;">&bull; Click 'Apply Changes' to update all EDA modules</span>
                </div>
                """
            )
        else:
            render_html(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; height: 100%; padding-top: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10B981;"></span>
                    <span style="font-size: 0.82rem; font-weight: 600; color: #10B981;">In Sync with Active Workspace</span>
                </div>
                """
            )

    with col_undo:
        if st.button("Undo", key="btn_global_undo", disabled=(undo_count == 0), use_container_width=True):
            apply_undo()

    with col_redo:
        if st.button("Redo", key="btn_global_redo", disabled=(redo_count == 0), use_container_width=True):
            apply_redo()

    with col_reset:
        if st.button("Reset All", key="btn_global_reset", use_container_width=True, help="Revert working dataset to raw original"):
            reset_to_original()

    with col_apply:
        if st.button("Apply Changes", key="btn_global_apply", type="primary", use_container_width=True, help="Commit staging data to active workspace"):
            apply_changes_to_active()


# =============================================================================
# 5. WORKSPACE TABS IMPLEMENTATION
# =============================================================================

def render_missing_values_tab(df: pd.DataFrame):
    """Tab 1: Missing Value Audit & Imputation Controls."""
    total_rows = len(df)
    null_counts = df.isna().sum()
    null_cols = null_counts[null_counts > 0]

    if null_cols.empty:
        render_html(
            f"""
            <div class="alert-banner alert-success">
                <div class="alert-icon">{icon_svg("check-circle", size=18, color="#10B981")}</div>
                <div class="alert-content">
                    <div class="alert-title">Dataset is 100% Complete</div>
                    <div class="alert-message">Zero missing or null cells detected across all {len(df.columns)} columns.</div>
                </div>
            </div>
            """
        )
        return

    # Per-column Missing Summary Table
    null_summary = []
    for col in null_cols.index:
        cnt = int(null_cols[col])
        pct = round((cnt / total_rows) * 100, 2)
        dtype = str(df[col].dtype)
        null_summary.append({
            "Column": col,
            "Data Type": dtype,
            "Missing Count": cnt,
            "Missing %": f"{pct}%",
            "Non-Null Count": total_rows - cnt,
        })
    st.dataframe(pd.DataFrame(null_summary), use_container_width=True, hide_index=True)

    st.write("")
    render_html("<div class='section-divider'></div>")

    # Imputation & Removal Controls
    st.markdown("##### Impute or Remove Missing Values")
    col_sel, method_sel, action_btn = st.columns([1.5, 2, 1.2])

    with col_sel:
        target_col = st.selectbox("Target Column", options=["All Columns"] + list(null_cols.index), key="null_target_col")

    with method_sel:
        is_num = False
        if target_col != "All Columns":
            is_num = pd.api.types.is_numeric_dtype(df[target_col])
            methods = ["Fill with Median", "Fill with Mean", "Fill with Mode", "Fill with Custom Value", "Forward Fill", "Backward Fill", "Drop Rows with Missing", "Drop Column"] if is_num else ["Fill with Mode", "Fill with 'Unknown'", "Fill with Custom Value", "Forward Fill", "Backward Fill", "Drop Rows with Missing", "Drop Column"]
        else:
            methods = ["Smart Impute (Median/Mode)", "Fill with 'Unknown' / 0", "Drop All Rows with Missing"]

        chosen_method = st.selectbox("Imputation Strategy", options=methods, key="null_method_select")

        custom_val = None
        if "Custom" in chosen_method:
            custom_val = st.text_input("Enter Custom Value", value="", key="null_custom_val_input")

    with action_btn:
        st.write("")
        st.write("")
        if st.button("Execute Action", key="null_execute_btn", use_container_width=True):
            push_undo_state()
            w_df = df.copy()

            if target_col == "All Columns":
                if chosen_method == "Smart Impute (Median/Mode)":
                    for c in w_df.columns:
                        if w_df[c].isna().sum() > 0:
                            if pd.api.types.is_numeric_dtype(w_df[c]):
                                w_df[c] = w_df[c].fillna(w_df[c].median())
                            else:
                                m = w_df[c].mode()
                                w_df[c] = w_df[c].fillna(m.iloc[0] if not m.empty else "Unknown")
                    st.session_state.working_df = w_df
                    record_transformation("Impute All", "All", int(null_cols.sum()), "Smart imputed median/mode across all columns")
                elif chosen_method == "Drop All Rows with Missing":
                    old_len = len(w_df)
                    st.session_state.working_df = w_df.dropna().reset_index(drop=True)
                    record_transformation("Drop Rows", "All", old_len - len(st.session_state.working_df), "Dropped all rows containing any nulls")
            else:
                if chosen_method == "Fill with Median":
                    w_df[target_col] = w_df[target_col].fillna(w_df[target_col].median())
                elif chosen_method == "Fill with Mean":
                    w_df[target_col] = w_df[target_col].fillna(w_df[target_col].mean())
                elif chosen_method == "Fill with Mode":
                    m = w_df[target_col].mode()
                    val = m.iloc[0] if not m.empty else 0
                    w_df[target_col] = w_df[target_col].fillna(val)
                elif chosen_method == "Fill with 'Unknown'":
                    w_df[target_col] = w_df[target_col].fillna("Unknown")
                elif chosen_method == "Fill with Custom Value" and custom_val:
                    val = pd.to_numeric(custom_val, errors="ignore") if is_num else custom_val
                    w_df[target_col] = w_df[target_col].fillna(val)
                elif chosen_method == "Forward Fill":
                    w_df[target_col] = w_df[target_col].ffill()
                elif chosen_method == "Backward Fill":
                    w_df[target_col] = w_df[target_col].bfill()
                elif chosen_method == "Drop Rows with Missing":
                    w_df = w_df.dropna(subset=[target_col]).reset_index(drop=True)
                elif chosen_method == "Drop Column":
                    w_df = w_df.drop(columns=[target_col])

                st.session_state.working_df = w_df
                record_transformation(chosen_method, target_col, int(null_counts.get(target_col, 0)), f"Applied '{chosen_method}' on '{target_col}'")
            st.rerun()

    # Threshold-based Column Drop Expander
    st.write("")
    with st.expander("Batch Drop Columns by Missing Threshold", expanded=False):
        st.caption("Automatically drop all columns whose missing value percentage exceeds a threshold.")
        th_col, th_btn = st.columns([3, 1])
        with th_col:
            thresh_pct = st.slider("Missing Percentage Threshold", min_value=10, max_value=90, value=50, step=5, key="null_thresh_slider")
            target_drop_cols = [c for c in df.columns if (df[c].isna().sum() / total_rows * 100) >= thresh_pct]
            st.write(f"Matches **{len(target_drop_cols)}** column(s): {', '.join(target_drop_cols) if target_drop_cols else 'None'}")
        with th_btn:
            st.write("")
            st.write("")
            if st.button("Drop Matching Columns", key="drop_thresh_cols_btn", disabled=(len(target_drop_cols) == 0), use_container_width=True):
                push_undo_state()
                st.session_state.working_df = df.drop(columns=target_drop_cols)
                record_transformation("Threshold Drop", ", ".join(target_drop_cols), 0, f"Dropped columns with >={thresh_pct}% nulls")
                st.rerun()


def render_duplicate_rows_tab(df: pd.DataFrame):
    """Tab 2: Duplicate Row Detection & Removal."""
    total_rows = len(df)
    
    dup_col_subset = st.multiselect(
        "Columns to consider for duplicate detection (leave blank for all columns):",
        options=df.columns.tolist(),
        default=[],
        key="dup_subset_multiselect",
    )

    subset_to_use = dup_col_subset if dup_col_subset else None
    dup_mask = df.duplicated(subset=subset_to_use, keep=False)
    dup_count = int(df.duplicated(subset=subset_to_use, keep="first").sum())
    dup_rows_total = int(dup_mask.sum())

    if dup_count == 0:
        render_html(
            f"""
            <div class="alert-banner alert-success">
                <div class="alert-icon">{icon_svg("check-circle", size=18, color="#10B981")}</div>
                <div class="alert-content">
                    <div class="alert-title">No Duplicate Records Found</div>
                    <div class="alert-message">Every row in the working dataset is unique based on the selected criteria.</div>
                </div>
            </div>
            """
        )
        return

    render_html(
        f"""
        <div class="alert-banner alert-warning">
            <div class="alert-icon">{icon_svg("alert-triangle", size=18, color="#F59E0B")}</div>
            <div class="alert-content">
                <div class="alert-title">{dup_count:,} Duplicate Rows Detected ({round(dup_count / total_rows * 100, 1)}%)</div>
                <div class="alert-message">A total of {dup_rows_total} rows share identical values across the specified columns.</div>
            </div>
        </div>
        """
    )

    st.write("")
    st.markdown("##### Preview Duplicate Records")
    preview_dup_df = df[dup_mask].sort_values(by=subset_to_use if subset_to_use else df.columns[0]).head(50)
    st.dataframe(preview_dup_df, use_container_width=True, hide_index=False)

    st.write("")
    render_html("<div class='section-divider'></div>")

    # Removal controls
    st.markdown("##### Remove Duplicate Records")
    keep_choice = st.radio(
        "Keep Strategy:",
        options=["Keep First Occurrence (Default)", "Keep Last Occurrence", "Drop All Duplicate Occurrences"],
        horizontal=True,
        key="dup_keep_radio",
    )

    keep_val = "first" if "First" in keep_choice else ("last" if "Last" in keep_choice else False)
    rows_to_remove = dup_count if keep_val else dup_rows_total

    st.write(f"Executing this action will remove **{rows_to_remove:,}** rows, leaving **{total_rows - rows_to_remove:,}** clean rows.")

    if st.button(f"Remove {rows_to_remove:,} Duplicate Rows", key="btn_remove_dups", type="primary"):
        push_undo_state()
        new_df = df.drop_duplicates(subset=subset_to_use, keep=keep_val).reset_index(drop=True)
        st.session_state.working_df = new_df
        record_transformation("Drop Duplicates", "Subset" if subset_to_use else "All", rows_to_remove, f"Strategy: {keep_choice}")
        st.rerun()


def render_data_type_correction_tab(df: pd.DataFrame):
    """Tab 3: Safe Data Type Conversion with Error Inspection."""
    st.markdown("##### Column Data Types & Suggested Conversions")

    type_info = []
    for col in df.columns:
        curr_type = str(df[col].dtype)
        # Determine suggested type
        suggested = curr_type
        sample = df[col].dropna().head(30)
        if len(sample) > 0 and curr_type == "object":
            cleaned_s = sample.astype(str).str.replace(r"[\$,\s%]", "", regex=True)
            num_parsed = pd.to_numeric(cleaned_s, errors="coerce")
            if num_parsed.notna().sum() >= len(sample) * 0.8:
                suggested = "float64"
            else:
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        d_parsed = pd.to_datetime(sample, errors="coerce")
                        if d_parsed.notna().sum() >= len(sample) * 0.8:
                            suggested = "datetime64[ns]"
                except Exception:
                    pass

        type_info.append({
            "Column": col,
            "Current Dtype": curr_type,
            "Suggested Dtype": suggested,
            "Unique Count": df[col].nunique(),
            "Null Count": df[col].isna().sum(),
        })

    st.dataframe(pd.DataFrame(type_info), use_container_width=True, hide_index=True)

    st.write("")
    render_html("<div class='section-divider'></div>")

    st.markdown("##### Safe Type Casting Tool")
    cast_col1, cast_col2, cast_btn = st.columns([1.5, 1.5, 1.2])

    with cast_col1:
        target_cast_col = st.selectbox("Select Column to Cast", options=df.columns.tolist(), key="cast_target_col")

    with cast_col2:
        type_options = ["Integer (Int64)", "Float (float64)", "String (object)", "Datetime", "Boolean", "Category"]
        target_type = st.selectbox("Target Data Type", options=type_options, key="cast_target_type")

    with cast_btn:
        st.write("")
        st.write("")
        if st.button("Apply Type Cast", key="cast_apply_btn", use_container_width=True):
            push_undo_state()
            w_df = df.copy()
            col_series = w_df[target_cast_col]

            try:
                if target_type == "Integer (Int64)":
                    cleaned = col_series.astype(str).str.replace(r"[^\d.-]", "", regex=True)
                    w_df[target_cast_col] = pd.to_numeric(cleaned, errors="coerce").round().astype("Int64")
                elif target_type == "Float (float64)":
                    cleaned = col_series.astype(str).str.replace(r"[^\d.-]", "", regex=True)
                    w_df[target_cast_col] = pd.to_numeric(cleaned, errors="coerce").astype(float)
                elif target_type == "String (object)":
                    w_df[target_cast_col] = col_series.astype(str)
                elif target_type == "Datetime":
                    w_df[target_cast_col] = pd.to_datetime(col_series, errors="coerce")
                elif target_type == "Boolean":
                    w_df[target_cast_col] = col_series.astype(bool)
                elif target_type == "Category":
                    w_df[target_cast_col] = col_series.astype("category")

                st.session_state.working_df = w_df
                record_transformation("Type Cast", target_cast_col, len(w_df), f"Casted from {col_series.dtype} to {target_type}")
                st.toast(f"Column '{target_cast_col}' casted to {target_type}", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Type conversion failed: {str(e)}")


def render_outlier_treatment_tab(df: pd.DataFrame):
    """Tab 4: Outlier Detection & Treatment (IQR & Z-Score)."""
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not num_cols:
        st.info("No numerical columns found in working dataset.")
        return

    method = st.radio("Detection Method:", options=["IQR (1.5 × IQR)", "Z-Score (|z| > 3.0)"], horizontal=True, key="outlier_method_radio")

    outlier_stats = []
    outlier_indices_map = {}

    for col in num_cols:
        clean_s = df[col].dropna()
        if len(clean_s) < 4:
            continue

        if "IQR" in method:
            q1 = clean_s.quantile(0.25)
            q3 = clean_s.quantile(0.75)
            iqr = q3 - q1
            lower_b = q1 - 1.5 * iqr
            upper_b = q3 + 1.5 * iqr
            out_mask = (df[col] < lower_b) | (df[col] > upper_b)
        else:
            mean = clean_s.mean()
            std = clean_s.std()
            lower_b = mean - 3.0 * std
            upper_b = mean + 3.0 * std
            out_mask = (df[col] < lower_b) | (df[col] > upper_b)

        out_count = int(out_mask.sum())
        out_pct = round((out_count / len(df)) * 100, 2)
        outlier_indices_map[col] = (out_mask, lower_b, upper_b)

        outlier_stats.append({
            "Column": col,
            "Outlier Count": out_count,
            "Outlier %": f"{out_pct}%",
            "Lower Bound": round(lower_b, 2),
            "Upper Bound": round(upper_b, 2),
            "Min Value": round(clean_s.min(), 2),
            "Max Value": round(clean_s.max(), 2),
        })

    st.dataframe(pd.DataFrame(outlier_stats), use_container_width=True, hide_index=True)

    st.write("")
    render_html("<div class='section-divider'></div>")

    # Treatment selector
    st.markdown("##### Outlier Treatment Controls")
    o_col, o_treat, o_btn = st.columns([1.5, 2, 1.2])

    with o_col:
        sel_col = st.selectbox("Target Numerical Column", options=num_cols, key="outlier_target_col")

    with o_treat:
        treat_options = [
            "Cap Outliers at Bounds (Winsorize)",
            "Replace Outliers with Median",
            "Replace Outliers with Mean",
            "Remove Rows Containing Outliers",
        ]
        sel_treat = st.selectbox("Treatment Action", options=treat_options, key="outlier_treatment_action")

    with o_btn:
        st.write("")
        st.write("")
        if st.button("Apply Treatment", key="outlier_apply_btn", use_container_width=True):
            push_undo_state()
            w_df = df.copy()
            out_mask, lower_b, upper_b = outlier_indices_map[sel_col]
            affected_rows = int(out_mask.sum())

            if affected_rows > 0:
                if "Cap" in sel_treat:
                    w_df[sel_col] = w_df[sel_col].clip(lower=lower_b, upper=upper_b)
                elif "Median" in sel_treat:
                    med_val = w_df[sel_col].median()
                    w_df.loc[out_mask, sel_col] = med_val
                elif "Mean" in sel_treat:
                    mean_val = w_df[sel_col].mean()
                    w_df.loc[out_mask, sel_col] = mean_val
                elif "Remove" in sel_treat:
                    w_df = w_df[~out_mask].reset_index(drop=True)

                st.session_state.working_df = w_df
                record_transformation(sel_treat, sel_col, affected_rows, f"Outlier treatment using {method}")
                st.toast(f"Treated {affected_rows} outliers in '{sel_col}'", icon="✅")
                st.rerun()
            else:
                st.info(f"No outliers found in column '{sel_col}'.")


def render_column_transforms_tab(df: pd.DataFrame):
    """Tab 5: Column Renaming, Deletion, Text Case, and Safe Calculated Columns."""
    sub_tab1, sub_tab2 = st.tabs(["Single Column Operations", "Safe Calculated Columns"])

    # --- SUB TAB 1: Single Column Transforms ---
    with sub_tab1:
        st.markdown("##### Column Structure & Cleaning")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("###### Rename Column")
            ren_col = st.selectbox("Select Column to Rename", options=df.columns.tolist(), key="ren_col_select")
            new_name = st.text_input("New Name", value=ren_col, key="ren_new_name_input")
            if st.button("Rename Column", key="ren_btn"):
                if new_name and new_name != ren_col:
                    push_undo_state()
                    st.session_state.working_df = df.rename(columns={ren_col: new_name})
                    record_transformation("Rename Column", ren_col, len(df), f"Renamed to '{new_name}'")
                    st.rerun()

            st.write("")
            st.markdown("###### Text Cleaning & Casing")
            text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
            if text_cols:
                case_col = st.selectbox("Select Text Column", options=text_cols, key="case_col_select")
                case_action = st.selectbox("Text Operation", options=["Trim Whitespace", "UPPERCASE", "lowercase", "Title Case"], key="case_action_select")
                if st.button("Apply Text Clean", key="case_btn"):
                    push_undo_state()
                    w_df = df.copy()
                    if case_action == "Trim Whitespace":
                        w_df[case_col] = w_df[case_col].astype(str).str.strip()
                    elif case_action == "UPPERCASE":
                        w_df[case_col] = w_df[case_col].astype(str).str.upper()
                    elif case_action == "lowercase":
                        w_df[case_col] = w_df[case_col].astype(str).str.lower()
                    elif case_action == "Title Case":
                        w_df[case_col] = w_df[case_col].astype(str).str.title()
                    st.session_state.working_df = w_df
                    record_transformation("Text Clean", case_col, len(w_df), case_action)
                    st.rerun()

        with col2:
            st.markdown("###### Find & Replace")
            rep_col = st.selectbox("Select Column to Search", options=df.columns.tolist(), key="rep_col_select")
            find_txt = st.text_input("Find", value="", key="rep_find_input")
            replace_txt = st.text_input("Replace With", value="", key="rep_replace_input")
            if st.button("Replace Values", key="rep_btn"):
                if find_txt:
                    push_undo_state()
                    w_df = df.copy()
                    w_df[rep_col] = w_df[rep_col].astype(str).replace(find_txt, replace_txt, regex=False)
                    st.session_state.working_df = w_df
                    record_transformation("Find & Replace", rep_col, len(w_df), f"Replaced '{find_txt}' with '{replace_txt}'")
                    st.rerun()

            st.write("")
            st.markdown("###### Delete Column")
            del_col = st.selectbox("Select Column to Delete", options=df.columns.tolist(), key="del_col_select")
            confirm_del = st.checkbox(f"Confirm deletion of column '{del_col}'", key="del_col_confirm")
            if st.button("Delete Column", key="del_btn", disabled=not confirm_del):
                push_undo_state()
                st.session_state.working_df = df.drop(columns=[del_col])
                record_transformation("Delete Column", del_col, 0, f"Deleted column '{del_col}'")
                st.rerun()

    # --- SUB TAB 2: Safe Calculated Columns ---
    with sub_tab2:
        st.markdown("##### Safe Calculated Column Builder")
        st.caption("Construct mathematical formulas or conditional columns using a controlled arithmetic engine (no arbitrary JS/exec).")

        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        calc_name = st.text_input("New Column Name", value="calculated_metric", key="calc_col_name")

        calc_type = st.radio("Formula Type:", options=["Two Column Arithmetic", "Column Scaling / Offset", "Condition / Threshold (If-Else)"], horizontal=True, key="calc_type_radio")

        preview_series = None

        if calc_type == "Two Column Arithmetic" and len(num_cols) >= 2:
            c1, c2, c3 = st.columns(3)
            with c1:
                col_a = st.selectbox("Column A", options=num_cols, key="calc_col_a")
            with c2:
                op = st.selectbox("Operator", options=["+", "-", "*", "/", "%"], key="calc_op")
            with c3:
                col_b = st.selectbox("Column B", options=[c for c in num_cols if c != col_a] + num_cols, key="calc_col_b")

            try:
                if op == "+":
                    preview_series = df[col_a] + df[col_b]
                elif op == "-":
                    preview_series = df[col_a] - df[col_b]
                elif op == "*":
                    preview_series = df[col_a] * df[col_b]
                elif op == "/":
                    preview_series = df[col_a] / df[col_b].replace(0, np.nan)
                elif op == "%":
                    preview_series = df[col_a] % df[col_b].replace(0, np.nan)
            except Exception as e:
                st.warning(f"Calculation preview notice: {str(e)}")

        elif calc_type == "Column Scaling / Offset" and num_cols:
            c1, c2, c3 = st.columns(3)
            with c1:
                scale_col = st.selectbox("Base Column", options=num_cols, key="scale_col_select")
            with c2:
                scale_op = st.selectbox("Operation", options=["Multiply (*)", "Divide (/)", "Add (+)", "Subtract (-)", "Log (log1p)"], key="scale_op_select")
            with c3:
                scale_val = st.number_input("Constant Value", value=100.0, key="scale_val_input")

            try:
                if "Multiply" in scale_op:
                    preview_series = df[scale_col] * scale_val
                elif "Divide" in scale_op:
                    preview_series = df[scale_col] / (scale_val if scale_val != 0 else np.nan)
                elif "Add" in scale_op:
                    preview_series = df[scale_col] + scale_val
                elif "Subtract" in scale_op:
                    preview_series = df[scale_col] - scale_val
                elif "Log" in scale_op:
                    preview_series = np.log1p(df[scale_col].clip(lower=0))
            except Exception as e:
                st.warning(f"Calculation preview notice: {str(e)}")

        elif calc_type == "Condition / Threshold (If-Else)":
            c1, c2, c3 = st.columns(3)
            with c1:
                cond_col = st.selectbox("Condition Column", options=df.columns.tolist(), key="cond_col_select")
            with c2:
                cond_op = st.selectbox("Comparison", options=[">", ">=", "<", "<=", "==", "!="], key="cond_op_select")
            with c3:
                cond_val_str = st.text_input("Threshold Value", value="0", key="cond_val_input")

            r1, r2 = st.columns(2)
            with r1:
                then_val = st.text_input("Value If TRUE", value="High", key="cond_then_input")
            with r2:
                else_val = st.text_input("Value If FALSE", value="Low", key="cond_else_input")

            try:
                if pd.api.types.is_numeric_dtype(df[cond_col]):
                    thresh = float(cond_val_str)
                    if cond_op == ">":
                        mask = df[cond_col] > thresh
                    elif cond_op == ">=":
                        mask = df[cond_col] >= thresh
                    elif cond_op == "<":
                        mask = df[cond_col] < thresh
                    elif cond_op == "<=":
                        mask = df[cond_col] <= thresh
                    elif cond_op == "==":
                        mask = df[cond_col] == thresh
                    else:
                        mask = df[cond_col] != thresh
                else:
                    mask = (df[cond_col].astype(str) == cond_val_str) if cond_op == "==" else (df[cond_col].astype(str) != cond_val_str)

                preview_series = pd.Series(np.where(mask, then_val, else_val), index=df.index)
            except Exception as e:
                st.warning(f"Calculation preview notice: {str(e)}")

        # Live Output Preview
        if preview_series is not None:
            st.write("")
            st.markdown("###### Output Preview (First 5 Rows):")
            prev_df = pd.DataFrame({calc_name: preview_series.head(5)})
            st.dataframe(prev_df, use_container_width=True, hide_index=True)

            if st.button("Add Calculated Column", key="add_calc_col_btn", type="primary"):
                push_undo_state()
                w_df = df.copy()
                w_df[calc_name] = preview_series
                st.session_state.working_df = w_df
                record_transformation("Calculated Column", calc_name, len(w_df), f"Formula: {calc_type}")
                st.toast(f"Added new column '{calc_name}'", icon="✅")
                st.rerun()


def render_visual_filter_builder_tab(df: pd.DataFrame):
    """Tab 6: Multi-Condition Visual Filter Builder & Multi-Column Sorting."""
    st.markdown("##### Visual Filter Builder")
    st.caption("Construct filters to isolate records. You can view filtered results or permanently prune matching/unmatching rows.")

    if "active_filters" not in st.session_state:
        st.session_state.active_filters = []

    # Filter Rule Creator
    f_col1, f_col2, f_col3, f_btn = st.columns([1.5, 1.2, 1.5, 1])

    with f_col1:
        f_column = st.selectbox("Column", options=df.columns.tolist(), key="fb_col_select")

    with f_col2:
        is_num = pd.api.types.is_numeric_dtype(df[f_column])
        ops = ["equals", "not equals", "greater than", "greater or equal", "less than", "less or equal", "is missing", "is not missing"] if is_num else ["equals", "not equals", "contains", "starts with", "ends with", "is missing", "is not missing"]
        f_op = st.selectbox("Operator", options=ops, key="fb_op_select")

    with f_col3:
        f_val = ""
        if "missing" not in f_op:
            f_val = st.text_input("Value", value="", key="fb_val_input")

    with f_btn:
        st.write("")
        st.write("")
        if st.button("Add Filter", key="fb_add_btn", use_container_width=True):
            if "missing" in f_op or f_val.strip():
                st.session_state.active_filters.append({
                    "column": f_column,
                    "op": f_op,
                    "value": f_val.strip(),
                })
                st.rerun()

    # Active Filter Chips
    if st.session_state.active_filters:
        st.write("")
        st.markdown("###### Active Filters:")
        
        # Combinator Logic (AND / OR)
        comb_logic = st.radio("Combine Multiple Filters with:", options=["AND (All must match)", "OR (Any can match)"], horizontal=True, key="fb_comb_logic")

        # Evaluate Filter Mask
        combined_mask = None
        for idx, flt in enumerate(st.session_state.active_filters):
            col_name = flt["column"]
            op_name = flt["op"]
            val_str = flt["value"]
            series = df[col_name]

            if op_name == "is missing":
                m = series.isna()
            elif op_name == "is not missing":
                m = series.notna()
            elif pd.api.types.is_numeric_dtype(series):
                try:
                    val_num = float(val_str)
                    if op_name == "equals":
                        m = series == val_num
                    elif op_name == "not equals":
                        m = series != val_num
                    elif op_name == "greater than":
                        m = series > val_num
                    elif op_name == "greater or equal":
                        m = series >= val_num
                    elif op_name == "less than":
                        m = series < val_num
                    elif op_name == "less or equal":
                        m = series <= val_num
                    else:
                        m = pd.Series(True, index=df.index)
                except Exception:
                    m = pd.Series(True, index=df.index)
            else:
                s_str = series.astype(str).str.lower()
                v_lower = val_str.lower()
                if op_name == "equals":
                    m = s_str == v_lower
                elif op_name == "not equals":
                    m = s_str != v_lower
                elif op_name == "contains":
                    m = s_str.str.contains(v_lower, regex=False, na=False)
                elif op_name == "starts with":
                    m = s_str.str.startswith(v_lower)
                elif op_name == "ends with":
                    m = s_str.str.endswith(v_lower)
                else:
                    m = pd.Series(True, index=df.index)

            if combined_mask is None:
                combined_mask = m
            else:
                combined_mask = (combined_mask & m) if "AND" in comb_logic else (combined_mask | m)

        filtered_count = int(combined_mask.sum()) if combined_mask is not None else len(df)
        st.write(f"Matches **{filtered_count:,}** of **{len(df):,}** rows ({round(filtered_count / len(df) * 100, 1)}%).")

        # Action Buttons
        act_col1, act_col2, act_col3 = st.columns([1.5, 1.5, 1.5])
        with act_col1:
            if st.button("Clear All Filters", key="fb_clear_btn", use_container_width=True):
                st.session_state.active_filters = []
                st.rerun()

        with act_col2:
            if st.button("Prune: Keep Matching Rows", key="fb_prune_keep_btn", type="primary", use_container_width=True):
                push_undo_state()
                st.session_state.working_df = df[combined_mask].reset_index(drop=True)
                record_transformation("Filter Prune", "Multiple", len(df) - filtered_count, "Kept only matching rows")
                st.session_state.active_filters = []
                st.rerun()

        with act_col3:
            if st.button("Prune: Drop Matching Rows", key="fb_prune_drop_btn", use_container_width=True):
                push_undo_state()
                st.session_state.working_df = df[~combined_mask].reset_index(drop=True)
                record_transformation("Filter Drop", "Multiple", filtered_count, "Dropped matching rows")
                st.session_state.active_filters = []
                st.rerun()

    st.write("")
    render_html("<div class='section-divider'></div>")

    # Multi-Column Sorting
    st.markdown("##### Multi-Column Dataset Sorting")
    sort_col1, sort_col2, sort_btn = st.columns([1.5, 1.5, 1])

    with sort_col1:
        primary_sort = st.selectbox("Primary Sort Column", options=df.columns.tolist(), key="sort_primary_col")
        primary_asc = st.checkbox("Ascending (A-Z / Low-High)", value=True, key="sort_primary_asc")

    with sort_col2:
        secondary_sort = st.selectbox("Secondary Sort Column (Optional)", options=["None"] + [c for c in df.columns if c != primary_sort], key="sort_secondary_col")
        secondary_asc = st.checkbox("Secondary Ascending", value=True, key="sort_secondary_asc")

    with sort_btn:
        st.write("")
        st.write("")
        if st.button("Sort Dataset", key="sort_exec_btn", use_container_width=True):
            push_undo_state()
            by_cols = [primary_sort]
            asc_list = [primary_asc]
            if secondary_sort != "None":
                by_cols.append(secondary_sort)
                asc_list.append(secondary_asc)

            st.session_state.working_df = df.sort_values(by=by_cols, ascending=asc_list).reset_index(drop=True)
            record_transformation("Sort Dataset", ", ".join(by_cols), len(df), f"Sorted by {by_cols}")
            st.toast("Dataset sorted successfully", icon="✅")
            st.rerun()


def render_history_and_preview_tab(df: pd.DataFrame):
    """Tab 7: Transformation Audit History & Working vs Original Data Table Preview."""
    st.markdown("##### Transformation Audit History")
    history = st.session_state.get("transformation_history", [])

    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        render_html(
            f"""
            <div style="font-size: 0.8rem; color: #94A3B8; padding: 0.6rem 0;">
                No transformations have been applied yet in this session.
            </div>
            """
        )

    st.write("")
    render_html("<div class='section-divider'></div>")

    # High-Density Data Preview
    st.markdown("##### High-Density Dataset Preview")
    
    view_mode = st.radio(
        "Preview Target:",
        options=["Working Dataset (Staging)", "Original Dataset (Raw)"],
        horizontal=True,
        key="preview_target_radio",
    )

    preview_source_df = get_original_df() if "Original" in view_mode else df
    if preview_source_df is None:
        preview_source_df = df

    # Controls: Search & Pagination
    p_ctrl1, p_ctrl2, p_ctrl3 = st.columns([2, 1, 1])
    with p_ctrl1:
        search_kw = st.text_input("Search records across all columns", value="", placeholder="Type to filter...", key="prep_table_search")
    with p_ctrl2:
        page_size = st.selectbox("Rows per page", options=[10, 25, 50, 100], index=1, key="prep_page_size")

    # Apply search filter
    display_df = preview_source_df
    if search_kw.strip():
        kw = search_kw.strip().lower()
        mask = display_df.astype(str).apply(lambda row: row.str.lower().str.contains(kw, regex=False).any(), axis=1)
        display_df = display_df[mask]

    total_display_rows = len(display_df)
    total_pages = max(1, (total_display_rows + page_size - 1) // page_size)

    with p_ctrl3:
        page_num = st.number_input(f"Page (1 to {total_pages})", min_value=1, max_value=total_pages, value=1, key="prep_page_num")

    start_idx = (page_num - 1) * page_size
    end_idx = min(start_idx + page_size, total_display_rows)
    paged_df = display_df.iloc[start_idx:end_idx]

    render_html(
        f"""
        <div class="table-info-bar">
            <span>Showing rows <strong>{start_idx + 1 if total_display_rows > 0 else 0}</strong> to <strong>{end_idx}</strong> of <strong>{total_display_rows:,}</strong> records ({len(display_df.columns)} columns).</span>
        </div>
        """
    )

    st.dataframe(paged_df, use_container_width=True, hide_index=False)


def render_export_cleaned_tab(df: pd.DataFrame):
    """Tab 8: Export Cleaned Dataset as CSV or Excel."""
    st.markdown("##### Download Cleaned Dataset")
    st.caption("Export the current working dataset containing all applied cleaning, transformations, and filters.")

    exp_scope = st.radio(
        "Export Scope:",
        options=["Full Working Dataset", "Active Filtered Records Only (if filters applied)"],
        horizontal=True,
        key="export_scope_radio",
    )

    export_df = df
    if "Filtered" in exp_scope and st.session_state.get("active_filters"):
        # evaluate filters
        comb_mask = None
        for flt in st.session_state.active_filters:
            col_name = flt["column"]
            op_name = flt["op"]
            val_str = flt["value"]
            s = df[col_name]
            if op_name == "is missing":
                m = s.isna()
            elif op_name == "is not missing":
                m = s.notna()
            elif pd.api.types.is_numeric_dtype(s):
                try:
                    num_v = float(val_str)
                    m = s == num_v if op_name == "equals" else (s > num_v if op_name == "greater than" else s < num_v)
                except Exception:
                    m = pd.Series(True, index=df.index)
            else:
                m = s.astype(str).str.lower().str.contains(val_str.lower(), regex=False, na=False)
            comb_mask = m if comb_mask is None else (comb_mask & m)
        if comb_mask is not None:
            export_df = df[comb_mask]

    orig_name = st.session_state.get("uploaded_file_name", "dataset")
    clean_base = os.path.splitext(orig_name)[0]

    d_col1, d_col2 = st.columns(2)

    with d_col1:
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV (.csv)",
            data=csv_bytes,
            file_name=f"{clean_base}_cleaned.csv",
            mime="text/csv",
            key="prep_dl_csv_btn",
            use_container_width=True,
        )

    with d_col2:
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Cleaned Data")
            excel_bytes = buffer.getvalue()
            st.download_button(
                label="Download as Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{clean_base}_cleaned.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="prep_dl_xlsx_btn",
                use_container_width=True,
            )
        except Exception:
            st.button("Excel Export Unavailable", disabled=True, use_container_width=True)


# =============================================================================
# 6. MAIN PAGE RENDERER
# =============================================================================

def render_data_prep_page():
    """Main entry point for the Data Preparation module."""
    from modules.config import NAV_DATASET
    from modules.ui_components import render_top_action_bar

    # Top Action Bar
    render_top_action_bar(key_suffix="data_prep")

    # Header Banner
    render_html(
        """
        <div class="page-header-container">
            <div class="page-header-badge">Data Preparation</div>
            <h1 class="page-header-title">Data Preparation</h1>
            <p class="page-header-subtitle">
                Clean, transform, and prepare your dataset before analysis.
            </p>
        </div>
        """
    )

    # Check dataset loaded
    df = get_working_df()
    is_loaded = st.session_state.get("dataset_loaded", False) and df is not None

    if not is_loaded:
        render_html(
            f"""
            <div class="empty-upload-card" style="padding: 3rem 2rem; margin-top: 1rem;">
                <div class="empty-upload-icon">{icon_svg("sliders", size=28, color="#2563EB")}</div>
                <div class="empty-upload-title">No Dataset Loaded</div>
                <p class="empty-upload-desc">
                    Upload a CSV or Excel file to start cleaning and preparing your data.
                </p>
            </div>
            """
        )
        st.write("")
        _, col_btn, _ = st.columns([1.5, 1.2, 1.5])
        with col_btn:
            if st.button("Go to Dataset", key="prep_empty_goto_dataset_btn", use_container_width=True):
                st.session_state.current_page = NAV_DATASET
                st.rerun()
        return

    orig_df = get_original_df()
    filename = st.session_state.get("uploaded_file_name", "Dataset")

    # Compute metrics for comparison
    orig_m = calculate_dataset_metrics(orig_df)
    work_m = calculate_dataset_metrics(df)

    # 1. Compact Summary
    render_compact_summary(orig_m, work_m, filename)

    # 2. Sticky Action Controls (Apply, Undo, Redo, Reset)
    render_action_control_bar()

    st.write("")

    # 3. Changes Comparison (Original vs Working)
    render_changes_comparison(orig_m, work_m)

    st.write("")

    # 4. Smart Cleaning Diagnostics
    recs = get_smart_recommendations(df)
    render_smart_recommendations(recs, df)

    render_html("<div class='section-divider'></div>")

    # 5. Core Workspace Tabs
    t_missing, t_dups, t_types, t_outliers, t_transforms, t_filters, t_preview, t_export = st.tabs([
        "Missing Values",
        "Duplicate Rows",
        "Data Types",
        "Outliers Treatment",
        "Transform Columns",
        "Visual Filter & Sort",
        "History & Preview",
        "Export Cleaned Data",
    ])

    with t_missing:
        render_missing_values_tab(df)

    with t_dups:
        render_duplicate_rows_tab(df)

    with t_types:
        render_data_type_correction_tab(df)

    with t_outliers:
        render_outlier_treatment_tab(df)

    with t_transforms:
        render_column_transforms_tab(df)

    with t_filters:
        render_visual_filter_builder_tab(df)

    with t_preview:
        render_history_and_preview_tab(df)

    with t_export:
        render_export_cleaned_tab(df)
