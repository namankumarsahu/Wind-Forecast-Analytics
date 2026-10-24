from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_service
from ..schemas import AccuracyResponse, OverviewResponse, PeriodsResponse
from ..services.analysis import AnalysisService

router = APIRouter(prefix="/api", tags=["analysis"])



@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="KPIs, coverage and forecast-vs-actual series for one day or a range",
)
def overview(
    day: dt.date | None = Query(None, alias="date", description="Single delivery date, YYYY-MM-DD"),
    start: dt.date | None = Query(None, description="Range start (use with `end`)"),
    end: dt.date | None = Query(None, description="Range end (use with `start`)"),
    service: AnalysisService = Depends(get_service),
) -> OverviewResponse:
    if day is not None:
        if start is not None or end is not None:
            raise HTTPException(422, "Use either `date` or `start`/`end`, not both.")
        start = end = day
    elif start is None and end is None:
        start, end = service.scope_start, service.scope_end
    elif start is None or end is None:
        raise HTTPException(422, "Both `start` and `end` are required for a range.")
    return service.overview(start, end)


@router.get(
    "/periods",
    response_model=PeriodsResponse,
    summary="Every 30-minute period of one delivery date with the selected forecast, actual and error",
)
def periods(
    day: dt.date = Query(..., alias="date", description="Delivery date, YYYY-MM-DD", examples=["2026-01-15"]),
    service: AnalysisService = Depends(get_service),
) -> PeriodsResponse:
    return service.periods(day)


@router.get(
    "/accuracy",
    response_model=AccuracyResponse,
    summary="Aggregate and daily accuracy, error distribution and worst periods for a date range",
)
def accuracy(
    start: dt.date = Query(..., description="First delivery date", examples=["2026-01-01"]),
    end: dt.date = Query(..., description="Last delivery date", examples=["2026-01-31"]),
    service: AnalysisService = Depends(get_service),
) -> AccuracyResponse:
    return service.accuracy(start, end)
