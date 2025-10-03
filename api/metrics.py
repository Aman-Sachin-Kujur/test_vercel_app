from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import numpy as np
from statistics import mean
import os

app = FastAPI()

# added to top
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific domains for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
    expose_headers=["*"]
)

# Load telemetry data (adjust path if needed for Vercel)
telemetry_path = Path(os.path.dirname(__file__)) / "q-vercel-latency.json"
try:
    with telemetry_path.open() as f:
        telemetry = json.load(f)
except FileNotFoundError:
    telemetry = []  # Fallback to empty list to avoid crashes

# Pydantic model for request validation
class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# Routes defined FIRST
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

@app.options("/metrics")  # Explicitly handle OPTIONS for preflight
def metrics_options():
    return {"status": "OK"}

@app.post("/metrics")
def compute_metrics(request: MetricsRequest):
    result = {}
    for region in request.regions:
        region_data = [r for r in telemetry if r.get("region") == region]
        if not region_data:
            continue
        
        latencies = [r.get("latency_ms", 0) for r in region_data]
        uptimes = [r.get("uptime", 0) for r in region_data]  # Safely handle missing 'uptime'
        
        avg_latency = mean(latencies) if latencies else 0
        p95_latency = np.percentile(latencies, 95) if latencies else 0
        avg_uptime = mean(uptimes) if uptimes else 0
        breaches = sum(1 for l in latencies if l > request.threshold_ms)
        
        result[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
    
    if not result:
        raise HTTPException(status_code=404, detail="No data for requested regions")
    
    return result


