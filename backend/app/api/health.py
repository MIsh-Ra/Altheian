import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional

import redis
import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceStatus(BaseModel):
    status: str = Field(..., description="up, degraded, or down")
    latency_ms: Optional[float] = None
    details: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    timestamp: str
    environment: str
    services: Dict[str, ServiceStatus]


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
def check_system_health(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Real-time health check diagnostic for all Alethian backend subsystems:
    1. PostgreSQL Relational Store
    2. Redis Broker & Event Bus
    3. Qdrant Vector Search Engine
    4. Celery Ingestion/CPU Worker
    5. Celery Neural GPU AI Worker
    """
    services: Dict[str, ServiceStatus] = {}

    # 1. PostgreSQL Check
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["database"] = ServiceStatus(
            status="up",
            latency_ms=latency,
            details="PostgreSQL database operational",
            metadata={"engine": "postgresql"},
        )
    except Exception as e:
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["database"] = ServiceStatus(
            status="down",
            latency_ms=latency,
            details=f"PostgreSQL unreachable: {str(e)[:120]}",
        )

    # 2. Redis & Queue Length Check
    t0 = time.perf_counter()
    redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    try:
        r = redis.Redis.from_url(redis_url, socket_timeout=2.0)
        r.ping()
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        q_default = r.llen("celery")
        q_ai = r.llen("ai_detection")
        q_esc = r.llen("ai_escalation")
        services["redis"] = ServiceStatus(
            status="up",
            latency_ms=latency,
            details="Redis broker responsive",
            metadata={
                "queues": {
                    "general_ingestion": q_default,
                    "ai_detection": q_ai,
                    "ai_escalation": q_esc,
                }
            },
        )
    except Exception as e:
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["redis"] = ServiceStatus(
            status="down",
            latency_ms=latency,
            details=f"Redis unreachable: {str(e)[:120]}",
        )

    # 3. Qdrant Vector Engine Check
    t0 = time.perf_counter()
    try:
        from app.core.similarity import _get_qdrant
        qm = _get_qdrant()
        collections_resp = qm.client.get_collections()
        col_names = [c.name for c in collections_resp.collections]
        points_count = 0
        if qm.collection_name in col_names:
            info = qm.client.get_collection(qm.collection_name)
            points_count = info.points_count or 0
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["vector_db"] = ServiceStatus(
            status="up",
            latency_ms=latency,
            details="Qdrant vector engine operational",
            metadata={
                "collection": qm.collection_name,
                "points_count": points_count,
            },
        )
    except Exception as e:
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["vector_db"] = ServiceStatus(
            status="down",
            latency_ms=latency,
            details=f"Qdrant unreachable: {str(e)[:120]}",
        )

    # 4. Celery General / CPU Worker Check
    t0 = time.perf_counter()
    try:
        from celery_worker import celery_app
        insp = celery_app.control.inspect(timeout=1.2)
        ping_res = insp.ping() if insp else None
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        if ping_res:
            workers = list(ping_res.keys())
            services["celery_cpu_worker"] = ServiceStatus(
                status="up",
                latency_ms=latency,
                details=f"{len(workers)} CPU worker(s) active",
                metadata={"workers": workers},
            )
        else:
            services["celery_cpu_worker"] = ServiceStatus(
                status="down",
                latency_ms=latency,
                details="No Celery CPU workers responded to ping",
            )
    except Exception as e:
        services["celery_cpu_worker"] = ServiceStatus(
            status="down",
            details=f"Failed to inspect CPU worker: {str(e)[:120]}",
        )

    # 5. Celery GPU AI Forensics Worker Check
    t0 = time.perf_counter()
    try:
        from celery_ai_worker import celery_ai_app
        insp_ai = celery_ai_app.control.inspect(timeout=1.2)
        ping_ai = insp_ai.ping() if insp_ai else None
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        if ping_ai:
            workers = list(ping_ai.keys())
            services["celery_ai_worker"] = ServiceStatus(
                status="up",
                latency_ms=latency,
                details=f"{len(workers)} GPU AI worker(s) active (V100 SDPA)",
                metadata={"workers": workers},
            )
        else:
            services["celery_ai_worker"] = ServiceStatus(
                status="down",
                latency_ms=latency,
                details="No Celery GPU AI workers active on queue ai_detection",
            )
    except Exception as e:
        services["celery_ai_worker"] = ServiceStatus(
            status="down",
            details=f"Failed to inspect GPU worker: {str(e)[:120]}",
        )

    # 6. Web Dragnet Search Gateway Check
    t0 = time.perf_counter()
    try:
        from app.core.web_dragnet import SerperClient
        client = SerperClient()
        engine_type = client.engine_type
        api_key = client.api_key
        has_key = bool(api_key and api_key not in ("", "PASTE_YOUR_KEY_HERE"))
        
        if has_key:
            try:
                # Fast check against the search endpoint
                resp = requests.post(
                    client.endpoint,
                    headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
                    data='{"q":"ping","num":1}',
                    timeout=4.0
                ) if engine_type == "serper" else requests.get(
                    client.endpoint,
                    params={"q": "ping", "api_key": api_key, "num": 1},
                    timeout=4.0
                )
                latency = round((time.perf_counter() - t0) * 1000.0, 2)
                if resp.status_code == 200:
                    services["web_dragnet"] = ServiceStatus(
                        status="up",
                        latency_ms=latency,
                        details=f"Live search gateway ({engine_type}) operational",
                        metadata={
                            "engine": engine_type,
                            "endpoint": client.endpoint,
                            "api_key_configured": True,
                            "masked_key": f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***",
                        },
                    )
                else:
                    services["web_dragnet"] = ServiceStatus(
                        status="degraded",
                        latency_ms=latency,
                        details=f"{engine_type} returned HTTP {resp.status_code}; fallback ready",
                        metadata={"engine": engine_type, "api_key_configured": True, "http_status": resp.status_code},
                    )
            except Exception as net_err:
                latency = round((time.perf_counter() - t0) * 1000.0, 2)
                services["web_dragnet"] = ServiceStatus(
                    status="degraded",
                    latency_ms=latency,
                    details=f"Search endpoint probe error: {str(net_err)[:80]}; fallback ready",
                    metadata={"engine": "ddgs_fallback", "api_key_configured": True},
                )
        else:
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            services["web_dragnet"] = ServiceStatus(
                status="up",
                latency_ms=latency,
                details="Zero-key DuckDuckGo search fallback active",
                metadata={"engine": "duckduckgo", "api_key_configured": False},
            )
    except Exception as e:
        latency = round((time.perf_counter() - t0) * 1000.0, 2)
        services["web_dragnet"] = ServiceStatus(
            status="down",
            latency_ms=latency,
            details=f"Failed to inspect Web Dragnet engine: {str(e)[:120]}",
        )

    # Compute overall composite status
    critical_services = ["database", "redis"]
    if any(services.get(s) and services[s].status == "down" for s in critical_services):
        overall = "unhealthy"
    elif any(s.status == "down" for s in services.values()):
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        environment=os.getenv("ENVIRONMENT", "production"),
        services=services,
    )
