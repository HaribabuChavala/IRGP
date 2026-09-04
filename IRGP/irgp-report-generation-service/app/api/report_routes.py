from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Report, ReportJob
from app.schemas import ReportGenerateRequest, ReportJobResponse, ReportResponse
from app.security import require_org_admin

router = APIRouter(tags=["reports"])


@router.post("/api/v1/reports/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> Report:
    job_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())

    job = ReportJob(
        id=job_id,
        organization_id=payload.organization_id,
        title=payload.title,
        data_source_id=payload.data_source_id,
        template=payload.template,
        status="queued",
    )
    report = Report(
        id=report_id,
        organization_id=payload.organization_id,
        title=payload.title,
        data_source_id=payload.data_source_id,
        job_id=job_id,
        status="queued",
    )
    db.add(job)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/api/v1/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/api/v1/reports/jobs/{job_id}/status", response_model=ReportJobResponse)
def get_report_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> ReportJob:
    job = db.get(ReportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found")
    return job
