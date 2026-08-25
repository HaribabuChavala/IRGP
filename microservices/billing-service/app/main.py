from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel, Field

from app.security import require_platform_admin

app = FastAPI(title="Billing Service", version="1.0.0")

_invoices: list[dict[str, Any]] = []


class InvoiceCreate(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: str = Field(default="pending", min_length=1, max_length=32)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "billing-service"}


@app.get("/api/v1/billing/invoices")
async def list_invoices(
    organization_id: str = Query(...),
    _: dict = Depends(require_platform_admin),
) -> dict[str, list[dict[str, Any]]]:
    return {"invoices": [invoice for invoice in _invoices if invoice["organization_id"] == organization_id]}


@app.post("/api/v1/billing/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    _: dict = Depends(require_platform_admin),
) -> dict[str, Any]:
    invoice = {
        "id": str(uuid.uuid4()),
        "organization_id": payload.organization_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "status": payload.status,
    }
    _invoices.append(invoice)
    return invoice
