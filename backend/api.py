"""
FastAPI REST Backend — Smart Machine Scheduling Dashboard
Serves all pre-computed pipeline output as clean JSON for the web frontend.
Deploy on Render: uvicorn backend.api:app --host 0.0.0.0 --port $PORT
"""
import re
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_DIR   = Path(__file__).parent / "output"
RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# 10 algorithms matching comprehensive_report.csv column headers
MODEL_ORDER = [
    "FCFS", "EDD", "SPT", "LPT",
    "Energy_Unaware", "Makespan_Greedy",
    "FD_PDTS_Det", "FD_PDTS_Robust",
    "CP_SAT_Warm", "CP_SAT_Cold",
]

# Map API model key → output CSV filename
SCHEDULE_FILES = {
    "FCFS":              "fcfs_schedule.csv",
    "EDD":               "edf_schedule.csv",
    "SPT":               "spt_schedule.csv",
    "LPT":               "lpt_schedule.csv",
    "Energy_Unaware":    "energy_unaware_schedule.csv",
    "Makespan_Greedy":   "makespan_schedule.csv",
    "FD_PDTS_Det":       "deterministic_schedule.csv",
    "FD_PDTS_Robust":    "robust_schedule.csv",
    "CP_SAT_Warm":       "hybrid_schedule.csv",
    "CP_SAT_Cold":       "cpsat_cold_schedule.csv",
}

HIGHER_BETTER = {"On-Time Completion (%)", "Machine Utilization (%)"}

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Machine Scheduling API",
    description="Serves pre-computed scheduling benchmark results as JSON.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend static files at root (optional — works when both are on same server)
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="web")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def parse_val(v) -> float:
    """Strip units and convert to float."""
    if pd.isna(v):
        return 0.0
    cleaned = re.sub(r"[₹INRkWhrstjobs%,\s]", "", str(v))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{path.name} not found. Run `python run_pipeline.py` first.",
        )
    return pd.read_csv(path)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Smart Machine Scheduling API v2",
        "docs": "/docs",
        "endpoints": [
            "/api/kpi",
            "/api/schedule/{model}",
            "/api/forecast",
            "/api/comparison",
            "/api/datasets/machines",
            "/api/datasets/jobs",
            "/api/aggregate-stats",
        ],
    }


@app.get("/api/kpi")
def get_kpi():
    """
    Returns the full KPI comparison table as a nested dict:
    {
      models: [...],
      metrics: [...],
      values: { "CP_SAT_Warm": { "Total Energy Cost (INR)": 125432.0, ... }, ... }
    }
    """
    df = load_csv(OUTPUT_DIR / "comprehensive_report.csv")

    values: dict = {}
    available_models = [m for m in MODEL_ORDER if m in df.columns]

    for model in available_models:
        values[model] = {}
        for _, row in df.iterrows():
            values[model][row["Metric"]] = parse_val(row[model])

    metrics = df["Metric"].tolist()

    # Pre-compute % improvement vs FCFS for every model / metric
    improvements: dict = {}
    fcfs_vals = values.get("FCFS", {})
    for model in available_models:
        if model == "FCFS":
            continue
        improvements[model] = {}
        for metric in metrics:
            base = fcfs_vals.get(metric, 0)
            val  = values.get(model, {}).get(metric, 0)
            if base == 0:
                pct = 0.0
            elif metric in HIGHER_BETTER:
                pct = (val - base) / base * 100
            else:
                pct = (base - val) / base * 100
            improvements[model][metric] = round(pct, 2)

    return {
        "models":       available_models,
        "metrics":      metrics,
        "values":       values,
        "improvements": improvements,
    }


@app.get("/api/schedule/{model}")
def get_schedule(model: str):
    """Returns all job rows for the specified scheduling model."""
    filename = SCHEDULE_FILES.get(model)
    if not filename:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Valid: {list(SCHEDULE_FILES.keys())}",
        )
    df = load_csv(OUTPUT_DIR / filename)
    return df.fillna("").to_dict(orient="records")


@app.get("/api/forecast")
def get_forecast():
    """Returns the 48-hour XGBoost energy demand forecast."""
    df = load_csv(OUTPUT_DIR / "future_forecast.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/comparison")
def get_comparison():
    """Returns the raw comparison_report.csv (FCFS vs CP-SAT)."""
    df = load_csv(OUTPUT_DIR / "comparison_report.csv")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/datasets/machines")
def get_machines():
    """Returns the machine fleet dataset."""
    df = load_csv(RAW_DATA_DIR / "machine_table.csv")
    return {
        "count": len(df),
        "columns": df.columns.tolist(),
        "data": df.fillna("").to_dict(orient="records"),
    }


@app.get("/api/datasets/jobs")
def get_jobs():
    """Returns the job scheduling dataset."""
    df = load_csv(RAW_DATA_DIR / "job_table.csv")

    # Compute summary stats
    stats = {
        "total_jobs": len(df),
        "avg_duration_min": round(float(df["Duration_min"].mean()), 2) if "Duration_min" in df.columns else 0,
        "min_duration_min": int(df["Duration_min"].min()) if "Duration_min" in df.columns else 0,
        "max_duration_min": int(df["Duration_min"].max()) if "Duration_min" in df.columns else 0,
        "priority_distribution": df["Priority"].value_counts().to_dict() if "Priority" in df.columns else {},
        "setup_type_distribution": df["Setup_Type"].value_counts().to_dict() if "Setup_Type" in df.columns else {},
    }

    return {
        "count": len(df),
        "columns": df.columns.tolist(),
        "stats": stats,
        "data": df.fillna("").to_dict(orient="records"),
    }


@app.get("/api/aggregate-stats")
def get_aggregate_stats():
    """Returns the 20-seed aggregate statistics for all algorithms."""
    path = OUTPUT_DIR / "aggregate_stats.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="aggregate_stats.csv not found.")
    df = load_csv(path)
    return df.fillna("").to_dict(orient="records")
