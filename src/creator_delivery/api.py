from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .campaign_service import CampaignDecision, CampaignRequest, DispatchRequest, dispatch_campaign, prepare_campaign
from .infrai_client import InfraiClient, InfraiError


app = FastAPI(title="Creator asset SMS delivery")


def get_client() -> InfraiClient:
    return InfraiClient(os.environ.get("INFRAI_API_KEY", ""))


@app.exception_handler(InfraiError)
async def handle_infrai_error(_: Request, exc: InfraiError) -> JSONResponse:
    client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=client_status, content={"error": exc.detail})


@app.post("/campaigns/prepare", response_model=CampaignDecision)
def prepare(request: CampaignRequest) -> CampaignDecision:
    return prepare_campaign(request, get_client())


@app.post("/campaigns/dispatch")
def dispatch(request: DispatchRequest) -> dict[str, object]:
    return dispatch_campaign(request, get_client())


@app.get("/messages/{message_id}/events")
def events(message_id: str) -> dict[str, object]:
    return get_client().message_events(message_id)

