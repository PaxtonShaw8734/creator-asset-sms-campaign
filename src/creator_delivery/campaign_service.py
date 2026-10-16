from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Subscriber(BaseModel):
    subscriber_id: str
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    first_name: str = Field(min_length=1, max_length=60)
    sms_opted_in: bool


class DigitalAsset(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    delivery_url: HttpUrl
    ready: bool


class CampaignRequest(BaseModel):
    campaign_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{3,64}$")
    creator_name: str = Field(min_length=1, max_length=60)
    message: str = Field(min_length=1, max_length=240)
    asset: DigitalAsset
    subscribers: list[Subscriber] = Field(min_length=1, max_length=500)


class CampaignDecision(BaseModel):
    campaign_id: str
    queued_subscriber_ids: list[str]
    skipped_subscriber_ids: list[str]
    queue_result: dict[str, Any]


class SmsMessage(BaseModel):
    to: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    body: str = Field(min_length=1, max_length=500)


class DispatchRequest(BaseModel):
    campaign_id: str
    messages: list[SmsMessage] = Field(min_length=1, max_length=500)


def prepare_campaign(request: CampaignRequest, client: Any) -> CampaignDecision:
    """Queue only consented subscribers when their purchased asset is ready."""
    eligible = request.subscribers if request.asset.ready else []
    eligible = [subscriber for subscriber in eligible if subscriber.sms_opted_in]
    queued_ids = [subscriber.subscriber_id for subscriber in eligible]
    skipped_ids = [
        subscriber.subscriber_id
        for subscriber in request.subscribers
        if subscriber.subscriber_id not in set(queued_ids)
    ]
    queue_messages = [
        {
            "payload": {
                "campaign_id": request.campaign_id,
                "subscriber_id": subscriber.subscriber_id,
                "to": subscriber.phone,
                "body": render_delivery_message(request, subscriber),
            }
        }
        for subscriber in eligible
    ]
    result = (
        client.publish_campaign("creator-asset-delivery", queue_messages, request.campaign_id)
        if queue_messages
        else {"published": 0}
    )
    return CampaignDecision(
        campaign_id=request.campaign_id,
        queued_subscriber_ids=queued_ids,
        skipped_subscriber_ids=skipped_ids,
        queue_result=result,
    )


def dispatch_campaign(request: DispatchRequest, client: Any) -> dict[str, Any]:
    messages = [{"to": item.to, "body": item.body} for item in request.messages]
    return client.send_sms_batch(messages, request.campaign_id)


def render_delivery_message(request: CampaignRequest, subscriber: Subscriber) -> str:
    clean_copy = re.sub(r"\s+", " ", request.message).strip()
    return (
        f"{subscriber.first_name}, {clean_copy} "
        f"{request.asset.title}: {request.asset.delivery_url} - {request.creator_name}. Reply STOP to opt out."
    )
