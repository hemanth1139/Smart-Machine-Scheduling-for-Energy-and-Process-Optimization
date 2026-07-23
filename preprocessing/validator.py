"""
Data Validation Module.
Performs automated checks on dataset integrity, schema types, missing values, duplicates,
out-of-bound invalid values, empty columns, and computes summary statistics.
Generates an automated markdown report saved to outputs/reports.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from config.config import Config, config
from utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Class for executing comprehensive automated data quality validation checks."""

    def __init__(self, cfg: Config = config):
        self.cfg = cfg

    def validate_dataset(
        self, df: pd.DataFrame, dataset_name: str
    ) -> Dict[str, Any]:
        """
        Runs comprehensive data quality validation checks on a single dataframe.

        Args:
            df: Input pandas DataFrame.
            dataset_name: Identifier name for the dataset (e.g. 'Energy', 'Job', 'Machine').

        Returns:
            Dict[str, Any]: Detailed validation result dictionary.
        """
        logger.info(f"Executing data validation for dataset: {dataset_name}")

        num_rows, num_cols = df.shape

        # 1. Missing Values Analysis
        missing_counts = df.isnull().sum()
        missing_pcts = (missing_counts / num_rows) * 100 if num_rows > 0 else 0
        missing_summary = {
            col: {"count": int(cnt), "percentage": round(float(pct), 2)}
            for col, cnt, pct in zip(df.columns, missing_counts, missing_pcts)
            if cnt > 0
        }
        total_missing = int(missing_counts.sum())

        # 2. Duplicate Rows
        duplicate_count = int(df.duplicated().sum())

        # 3. Empty Columns (all NaN or empty string)
        empty_cols = [
            col for col in df.columns if df[col].isnull().all() or (df[col] == "").all()
        ]

        # 4. Data Types
        data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

        # 5. Invalid Values Validation
        invalid_issues = []

        # Check negative values in strictly non-negative columns if applicable
        if dataset_name.lower() == "energy":
            for col in self.cfg.NON_NEGATIVE_COLS:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    neg_cnt = int((df[col] < 0).sum())
                    if neg_cnt > 0:
                        invalid_issues.append(
                            f"Column '{col}' contains {neg_cnt} negative values."
                        )

            # Power Factor Range Check [0, 100]
            pf_cols = [
                "Lagging_Current_Power_Factor",
                "Leading_Current_Power_Factor",
            ]
            for col in pf_cols:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    out_range = int(
                        ((df[col] < 0.0) | (df[col] > 100.0)).sum()
                    )
                    if out_range > 0:
                        invalid_issues.append(
                            f"Column '{col}' has {out_range} values outside valid range [0, 100]."
                        )

        # 6. Basic Statistics for Numeric Columns
        numeric_df = df.select_dtypes(include=[np.number])
        stats_summary = {}
        if not numeric_df.empty:
            desc = numeric_df.describe().T
            for col, row in desc.iterrows():
                stats_summary[col] = {
                    "mean": round(float(row["mean"]), 3),
                    "std": round(float(row["std"]), 3),
                    "min": round(float(row["min"]), 3),
                    "25%": round(float(row["25%"]), 3),
                    "50%": round(float(row["50%"]), 3),
                    "75%": round(float(row["75%"]), 3),
                    "max": round(float(row["max"]), 3),
                }

        results = {
            "dataset_name": dataset_name,
            "dimensions": {"rows": num_rows, "columns": num_cols},
            "total_missing_cells": total_missing,
            "missing_summary": missing_summary,
            "duplicate_rows": duplicate_count,
            "empty_columns": empty_cols,
            "data_types": data_types,
            "invalid_value_warnings": invalid_issues,
            "numeric_stats": stats_summary,
        }

        logger.info(
            f"Validation complete for {dataset_name}. "
            f"Rows: {num_rows}, Cols: {num_cols}, Duplicates: {duplicate_count}, "
            f"Missing Cells: {total_missing}, Invalid Issues: {len(invalid_issues)}"
        )
        return results

    def validate_all_and_save_report(
        self,
        energy_df: pd.DataFrame,
        job_df: pd.DataFrame,
        machine_df: pd.DataFrame,
        save_path: Optional[Path] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Executes validation across all three datasets and exports a structured markdown report.

        Returns:
            Dict[str, Dict[str, Any]]: Combined validation result dicts.
        """
        if save_path is None:
            save_path = self.cfg.REPORTS_OUTPUT_DIR / "data_validation_report.md"

        save_path.parent.mkdir(parents=True, exist_ok=True)

        results = {
            "Energy": self.validate_dataset(energy_df, "Energy"),
            "Job": self.validate_dataset(job_df, "Job"),
            "Machine": self.validate_dataset(machine_df, "Machine"),
        }

        # Build Markdown Report
        lines = [
            "# Data Validation Report",
            "",
            "## Executive Summary",
            "",
            "Automated quality validation executed across Energy, Job, and Machine datasets.",
            "",
            "| Dataset | Dimensions | Duplicates | Total Missing Cells | Empty Cols | Invalid Warnings |",
            "|---|---|---|---|---|---|",
        ]

        for ds_name, res in results.items():
            dim = f"{res['dimensions']['rows']} x {res['dimensions']['columns']}"
            dups = res['duplicate_rows']
            miss = res['total_missing_cells']
            empty = len(res['empty_columns'])
            inv = len(res['invalid_value_warnings'])
            lines.append(f"| {ds_name} | {dim} | {dups} | {miss} | {empty} | {inv} |")

        lines.extend(["", "---", ""])

        for ds_name, res in results.items():
            lines.append(f"## Dataset: {ds_name}")
            lines.append(f"- **Dimensions**: {res['dimensions']['rows']} rows, {res['dimensions']['columns']} columns")
            lines.append(f"- **Duplicate Rows**: {res['duplicate_rows']}")
            lines.append(f"- **Empty Columns**: {res['empty_columns'] if res['empty_columns'] else 'None'}")
            
            # Missing Summary
            lines.append("- **Missing Values**:")
            if res['missing_summary']:
                for col, info in res['missing_summary'].items():
                    lines.append(f"  - `{col}`: {info['count']} missing ({info['percentage']}%)")
            else:
                lines.append("  - No missing values detected.")

            # Invalid warnings
            lines.append("- **Invalid Value Checks**:")
            if res['invalid_value_warnings']:
                for warn in res['invalid_value_warnings']:
                    lines.append(f"  - ⚠️ {warn}")
            else:
                lines.append("  - All values within expected domain bounds.")

            # Data Types
            lines.append("- **Column Data Types**:")
            for col, dtype in res['data_types'].items():
                lines.append(f"  - `{col}`: `{dtype}`")

            # Numeric Stats Table
            if res['numeric_stats']:
                lines.append("")
                lines.append("### Basic Numerical Statistics")
                lines.append("| Column | Mean | Std | Min | 25% | 50% | 75% | Max |")
                lines.append("|---|---|---|---|---|---|---|---|")
                for col, st in res['numeric_stats'].items():
                    lines.append(
                        f"| `{col}` | {st['mean']} | {st['std']} | {st['min']} | "
                        f"{st['25%']} | {st['50%']} | {st['75%']} | {st['max']} |"
                    )

            lines.extend(["", "---", ""])

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Data validation report successfully written to: {save_path}")
        return results
