"""
Data Ingestion and Loading Utilities for Data Studio
"""

import io
import os
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


def validate_file_extension(filename: str) -> bool:
    """Validate whether uploaded file extension is supported."""
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)


def load_dataset(file_or_path) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load a dataset from an uploaded file buffer, file-like object, or file path.
    Supports CSV and Excel formats with robust encoding and error handling.

    Args:
        file_or_path: Streamlit UploadedFile, file buffer, or string path.

    Returns:
        Tuple of (DataFrame or None, error_message or None).
    """
    if file_or_path is None:
        return None, "No file provided. Please select a CSV or Excel file."

    if isinstance(file_or_path, str):
        filename = os.path.basename(file_or_path).strip()
        is_path = True
    else:
        filename = getattr(file_or_path, "name", str(file_or_path)).strip()
        is_path = False

    if not filename:
        return None, "Invalid file name."

    lower_name = filename.lower()

    if not validate_file_extension(lower_name):
        return None, "Unsupported format. Please provide a .csv, .xlsx, or .xls file."

    try:
        # Reset buffer pointer if available
        if hasattr(file_or_path, "seek"):
            file_or_path.seek(0)

        df: Optional[pd.DataFrame] = None

        if lower_name.endswith(".csv"):
            try:
                # Primary attempt: UTF-8
                df = pd.read_csv(file_or_path)
            except UnicodeDecodeError:
                # Fallback 1: Latin-1
                if hasattr(file_or_path, "seek"):
                    file_or_path.seek(0)
                try:
                    df = pd.read_csv(file_or_path, encoding="latin1")
                except Exception:
                    # Fallback 2: cp1252
                    if hasattr(file_or_path, "seek"):
                        file_or_path.seek(0)
                    df = pd.read_csv(file_or_path, encoding="cp1252")
            except pd.errors.EmptyDataError:
                return None, "The CSV file is empty and contains no readable rows."
            except pd.errors.ParserError as pe:
                return None, f"Could not parse CSV: {str(pe)}"

        elif lower_name.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(file_or_path)
            except Exception as xe:
                return None, f"Could not read Excel workbook: {str(xe)}"

        if df is None:
            return None, "Unable to read dataset from file."

        if df.empty:
            return None, "The dataset has 0 rows."

        # Clean column names
        df.columns = [str(c).strip() if str(c).strip() != "" else f"Col_{i}" for i, c in enumerate(df.columns)]

        # Ensure object columns serialize cleanly to Arrow without mixed-type warnings
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).replace("<NA>", "").replace("nan", "")

        return df, None

    except Exception as e:
        return None, f"Error reading file: {str(e)}"


def get_dataset_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extract structural metrics, null counts, and column schema from a DataFrame.

    Args:
        df: Loaded pandas DataFrame.

    Returns:
        Dictionary containing rows, cols, null cells, memory, duplicate rows, and schema DataFrame.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return {
            "total_rows": 0,
            "total_columns": 0,
            "columns": [],
            "memory_usage_mb": 0.0,
            "null_cells": 0,
            "null_percentage": 0.0,
            "duplicate_rows": 0,
            "numeric_columns": [],
            "categorical_columns": [],
            "schema_df": pd.DataFrame(),
        }

    total_rows, total_cols = df.shape
    total_cells = total_rows * total_cols

    try:
        mem_bytes = df.memory_usage(deep=True).sum()
        mem_mb = round(mem_bytes / (1024 * 1024), 2)
    except Exception:
        mem_mb = 0.0

    null_cells = int(df.isnull().sum().sum())
    null_percentage = round((null_cells / total_cells * 100), 2) if total_cells > 0 else 0.0

    try:
        duplicate_rows = int(df.duplicated().sum())
    except Exception:
        duplicate_rows = 0

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # Build detailed schema DataFrame
    schema_records = []
    for col in df.columns:
        col_type = str(df[col].dtype)
        null_count = int(df[col].isnull().sum())
        non_null_count = total_rows - null_count
        null_pct = round((null_count / total_rows * 100), 1) if total_rows > 0 else 0.0
        unique_count = int(df[col].nunique(dropna=False))
        
        # Sample non-null value
        first_valid = df[col].dropna().iloc[0] if non_null_count > 0 else "-"
        sample_str = str(first_valid)
        if len(sample_str) > 35:
            sample_str = sample_str[:32] + "..."

        schema_records.append({
            "Column": col,
            "Data Type": col_type,
            "Non-Null": f"{non_null_count:,}",
            "Nulls": f"{null_count:,} ({null_pct}%)",
            "Unique": f"{unique_count:,}",
            "Sample": sample_str,
        })

    schema_df = pd.DataFrame(schema_records)

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "columns": df.columns.tolist(),
        "memory_usage_mb": mem_mb,
        "null_cells": null_cells,
        "null_percentage": null_percentage,
        "duplicate_rows": duplicate_rows,
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
        "schema_df": schema_df,
    }


def get_data_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate an in-depth data quality audit report.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "health_score": 100,
            "completeness_pct": 100.0,
            "uniqueness_pct": 100.0,
            "null_summary_df": pd.DataFrame(),
            "duplicate_df": pd.DataFrame(),
            "dtype_breakdown": {},
            "constant_columns": [],
        }

    total_rows, total_cols = df.shape
    total_cells = total_rows * total_cols

    # 1. Completeness & Uniqueness
    null_cells = int(df.isnull().sum().sum())
    completeness_pct = round(100.0 - (null_cells / total_cells * 100), 2) if total_cells > 0 else 100.0

    try:
        duplicate_rows = int(df.duplicated().sum())
        duplicate_df = df[df.duplicated(keep=False)].head(100) if duplicate_rows > 0 else pd.DataFrame()
    except Exception:
        duplicate_rows = 0
        duplicate_df = pd.DataFrame()

    uniqueness_pct = round(100.0 - (duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 100.0

    # Overall Data Health Score (weighted average: 60% completeness, 40% uniqueness)
    health_score = int(round((completeness_pct * 0.6) + (uniqueness_pct * 0.4)))

    # 2. Null Breakdown per Column
    null_counts = df.isnull().sum()
    null_records = []
    for col in df.columns:
        cnt = int(null_counts[col])
        pct = round(cnt / total_rows * 100, 2) if total_rows > 0 else 0.0
        status = "Clean" if cnt == 0 else ("Severe (>30%)" if pct > 30 else "Moderate (<30%)")
        null_records.append({
            "Column": col,
            "Data Type": str(df[col].dtype),
            "Missing Count": cnt,
            "Missing %": pct,
            "Status": status,
        })

    null_summary_df = pd.DataFrame(null_records).sort_values(by="Missing %", ascending=False)

    # 3. Dtype Breakdown
    dtype_breakdown = df.dtypes.astype(str).value_counts().to_dict()

    # 4. Constant / Zero-variance columns
    constant_columns = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]

    return {
        "health_score": health_score,
        "completeness_pct": completeness_pct,
        "uniqueness_pct": uniqueness_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_df": duplicate_df,
        "null_summary_df": null_summary_df,
        "dtype_breakdown": dtype_breakdown,
        "constant_columns": constant_columns,
    }


def query_dataframe_with_pandas(df: pd.DataFrame, query_type: str, col_name: Optional[str] = None, top_n: int = 5) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Run common analytical queries on DataFrame and return result + code explanation.
    """
    if df is None or df.empty:
        return None, "No active dataset."

    try:
        if query_type == "top_records" and col_name and col_name in df.columns:
            res = df.sort_values(by=col_name, ascending=False).head(top_n)
            code = f"df.sort_values(by='{col_name}', ascending=False).head({top_n})"
            return res, code

        elif query_type == "bottom_records" and col_name and col_name in df.columns:
            res = df.sort_values(by=col_name, ascending=True).head(top_n)
            code = f"df.sort_values(by='{col_name}', ascending=True).head({top_n})"
            return res, code

        elif query_type == "group_counts" and col_name and col_name in df.columns:
            counts = df[col_name].value_counts().head(top_n).reset_index()
            counts.columns = [col_name, "Count"]
            code = f"df['{col_name}'].value_counts().head({top_n}).reset_index()"
            return counts, code

        elif query_type == "correlation":
            num_df = df.select_dtypes(include=["number"])
            if num_df.shape[1] >= 2:
                corr = num_df.corr().round(3)
                code = "df.select_dtypes(include=['number']).corr().round(3)"
                return corr, code
            else:
                return None, "Need at least 2 numerical columns to calculate correlation."

        elif query_type == "missing_summary":
            nulls = df.isnull().sum()[lambda x: x > 0].reset_index()
            if not nulls.empty:
                nulls.columns = ["Column", "Missing Values"]
                code = "df.isnull().sum()[lambda x: x > 0].reset_index()"
                return nulls, code
            else:
                return pd.DataFrame([{"Status": "Zero missing values across all columns."}]), "df.isnull().sum()"

        elif query_type == "numerical_describe":
            num_df = df.select_dtypes(include=["number"])
            if not num_df.empty:
                desc = num_df.describe().T.round(2).reset_index().rename(columns={"index": "Column"})
                code = "df.select_dtypes(include=['number']).describe().T.round(2)"
                return desc, code
            else:
                return None, "No numerical columns found in this dataset."

        return df.head(top_n), f"df.head({top_n})"

    except Exception as e:
        return None, f"Query error: {str(e)}"

