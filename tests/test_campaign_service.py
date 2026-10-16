from creator_delivery.campaign_service import CampaignRequest, DispatchRequest, dispatch_campaign, prepare_campaign


class RecordingClient:
    def __init__(self) -> None:
        self.queued = []
        self.sent = []

    def publish_campaign(self, queue, messages, campaign_id):
        self.queued.append((queue, messages, campaign_id))
        return {"published": len(messages)}

    def send_sms_batch(self, messages, campaign_id):
        self.sent.append((messages, campaign_id))
        return {"accepted": len(messages)}


def campaign_payload(asset_ready=True):
    return {
        "campaign_id": "drop-42",
        "creator_name": "Mira Studio",
        "message": "  Your   purchased pack is ready. ",
        "asset": {
            "title": "Editing pack",
            "delivery_url": "https://downloads.example.com/order/42",
            "ready": asset_ready,
        },
        "subscribers": [
            {"subscriber_id": "active", "phone": "+15550101010", "first_name": "Avery", "sms_opted_in": True},
            {"subscriber_id": "paused", "phone": "+15550101011", "first_name": "Sam", "sms_opted_in": False},
        ],
    }


def test_prepare_queues_only_consented_subscribers_for_ready_asset():
    client = RecordingClient()
    decision = prepare_campaign(CampaignRequest.model_validate(campaign_payload()), client)

    assert decision.queued_subscriber_ids == ["active"]
    assert decision.skipped_subscriber_ids == ["paused"]
    queue, messages, campaign_id = client.queued[0]
    assert queue == "creator-asset-delivery"
    assert campaign_id == "drop-42"
    assert messages[0]["payload"]["to"] == "+15550101010"
    assert "Your purchased pack is ready." in messages[0]["payload"]["body"]


def test_dispatch_preserves_only_sms_request_fields():
    client = RecordingClient()
    request = DispatchRequest(campaign_id="drop-42", messages=[{"to": "+15550101010", "body": "Asset ready"}])

    assert dispatch_campaign(request, client) == {"accepted": 1}
    assert client.sent == [([{"to": "+15550101010", "body": "Asset ready"}], "drop-42")]

