"""
Dashboard Exporter Utility Module.
Handles exporting DataFrames to CSV/Excel bytes for Streamlit download buttons.
"""

import io
import pandas as pd
from dashboard.utils.logger import dash_logger


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Converts DataFrame to CSV byte stream for download."""
    dash_logger.info(f"Converting DataFrame ({df.shape}) to CSV byte stream.")
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    """Converts DataFrame to Excel XLSX byte stream for download."""
    dash_logger.info(f"Converting DataFrame ({df.shape}) to Excel XLSX byte stream.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()
