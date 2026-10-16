from __future__ import annotations

import json
import os

from creator_delivery.campaign_service import CampaignRequest, prepare_campaign
from creator_delivery.infrai_client import InfraiClient


request = CampaignRequest.model_validate(
    {
        "campaign_id": "drop-september-01",
        "creator_name": "Mira Studio",
        "message": "Your supporter edition is ready.",
        "asset": {
            "title": "Lightroom preset pack",
            "delivery_url": "https://downloads.example.com/orders/demo-token",
            "ready": True,
        },
        "subscribers": [
            {
                "subscriber_id": "sub-1042",
                "phone": "+15550102020",
                "first_name": "Avery",
                "sms_opted_in": True,
            }
        ],
    }
)

client = InfraiClient(os.environ.get("INFRAI_API_KEY", ""))
print(json.dumps(prepare_campaign(request, client).model_dump(), indent=2, default=str))

