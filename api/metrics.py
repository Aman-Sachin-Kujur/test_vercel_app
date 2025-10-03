from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
from pathlib import Path
from statistics import mean
import numpy as np

app = FastAPI()


# Enable CORS for POST from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load telemetry data once
telemetry_path = Path(os.path.dirname(__file__)) / "q-vercel-latency.json"
with telemetry_path.open() as f:
    telemetry = json.load(f)

class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int = 180

@app.post("/metrics")
def compute_metrics(request: MetricsRequest):
    result = {}
    
    for region in request.regions:
        region_data = [r for r in telemetry if r["region"] == region]
        if not region_data:
            continue
        
        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime"] for r in region_data]
        
        avg_latency = mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        avg_uptime = mean(uptimes)
        breaches = sum(1 for l in latencies if l > request.threshold_ms)
        
        result[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
            
        }
        

    return result
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

