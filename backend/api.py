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
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

MODEL_ORDER  = [
    "FCFS", "EDF", "Makespan_Greedy",
    "Deterministic_Greedy", "Proposed_Robust_Greedy", "Hybrid_Solver",
]
SCHEDULE_FILES = {
    "FCFS":                  "fcfs_schedule.csv",
    "EDF":                   "edf_schedule.csv",
    "Makespan_Greedy":       "makespan_schedule.csv",
    "Deterministic_Greedy":  "deterministic_schedule.csv",
    "Proposed_Robust_Greedy":"robust_schedule.csv",
    "Hybrid_Solver":         "hybrid_schedule.csv",
}
HIGHER_BETTER = {"On-Time Completion (%)", "Machine Utilization (%)"}

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Machine Scheduling API",
    description="Serves pre-computed scheduling benchmark results as JSON.",
    version="1.0.0",
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
        "message": "Smart Machine Scheduling API",
        "docs": "/docs",
        "endpoints": ["/api/kpi", "/api/schedule/{model}", "/api/forecast", "/api/comparison"],
    }


@app.get("/api/kpi")
def get_kpi():
    """
    Returns the full KPI comparison table as a nested dict:
    {
      models: [...],
      metrics: [...],
      values: { "Hybrid_Solver": { "Total Energy Cost (INR)": 125432.0, ... }, ... }
    }
    """
    df = load_csv(OUTPUT_DIR / "comprehensive_report.csv")

    values: dict = {}
    for model in MODEL_ORDER:
        if model not in df.columns:
            continue
        values[model] = {}
        for _, row in df.iterrows():
            values[model][row["Metric"]] = parse_val(row[model])

    metrics = df["Metric"].tolist()

    # Pre-compute % improvement vs FCFS for every model / metric
    improvements: dict = {}
    fcfs_vals = values.get("FCFS", {})
    for model in MODEL_ORDER[1:]:
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
        "models":       MODEL_ORDER,
        "metrics":      metrics,
        "values":       values,
        "improvements": improvements,   # pre-computed % vs FCFS (positive = better)
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
