from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_service
from ..schemas import ConfigResponse
from ..services.analysis import AnalysisService

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", summary="Liveness probe (does not call Elexon)")
def health(service: AnalysisService = Depends(get_service)) -> dict:
    return {
        "status": "ok",
        "analysis_start": service.scope_start.isoformat(),
        "analysis_end": service.scope_end.isoformat(),
    }


@router.get("/config", response_model=ConfigResponse, summary="Analysis scope and decision-cutoff policy")
def config(service: AnalysisService = Depends(get_service)) -> ConfigResponse:
    return service.config()
