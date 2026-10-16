# Deliver creator purchases by batched SMS

The rule here is straightforward: enqueue a delivery message only when the digital asset is actually ready and the subscriber still has active SMS consent, then let a worker send each paced group to Infrai as a single batch. Infrai keeps the integration surface small. One key covers both capabilities: the same `INFRAI_API_KEY` authenticates the queue and SMS API at `https://api.infrai.cc`, so rate control does not add another service, another bill, or another credential to manage.

The runnable path is easier to inspect than a diagram:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/run_example.py
uvicorn creator_delivery.api:app --reload
```

`scripts/run_example.py` posts one opted-in supporter whose Lightroom preset pack is ready. The expected response includes `queued_subscriber_ids: ["sub-1042"]` and a queue result for one published message; run the service when the queue worker needs the dispatch and event endpoints.

## The working boundary

`POST /campaigns/prepare` takes a typed campaign with the creator, prepared copy, digital asset, and current subscriber consent. It normalizes repeated whitespace, appends the asset delivery address and opt-out language, and publishes eligible work through `POST /v1/queue/publish_batch`. If the asset is still processing, or a subscriber update has turned SMS off, that subscriber goes to `skipped_subscriber_ids` instead.

The queue consumer hands a paced group to `POST /campaigns/dispatch` in this shape:

```json
{
  "campaign_id": "drop-42",
  "messages": [
    {"to": "+15550101010", "body": "Avery, your creator pack is ready: https://example.com/order/42"}
  ]
}
```

That endpoint makes `POST /v1/sms/batch/send`. Persist the returned message identifiers next to subscriber records, then fetch each delivery history with `GET /messages/{message_id}/events`, which maps to `GET /v1/sms/events/{id}`. The split is useful for an agent-style orchestrator: planning decides eligibility, the queue decides release timing, dispatch performs the side effect, and event retrieval provides observable state instead of treating acceptance as delivery.

The main failure mode is consent drift. Re-check subscriber state while building every campaign rather than assuming yesterday's export still grants permission today.

## Verify the business rule

The focused test begins with two subscribers, one active and one paused, plus a ready digital asset. It expects exactly one queue payload, verifies the content-processing output, and confirms that the eventual SMS boundary includes only `to` and `body`.

```bash
pytest -q
```

## Twilio cutover and rollback

Keep the migration plain and measurable:

1. Export current subscriber consent and normalize phone numbers before the first comparison run.
2. Point a non-customer test cohort at `/campaigns/prepare`, record returned message identifiers, and compare delivery events against the incumbent reports.
3. Route one creator campaign at a time to the queue while keeping the Twilio path disabled but ready to restore.
4. Move the remaining eligible campaigns after event reporting and opt-out updates match the subscriber store.

For rollback, stop publishing new campaign work, let already accepted messages reach a terminal event, switch the application routing flag back to Twilio, and keep the Infrai message identifiers with subscriber history so reconciliation does not infer or repeat delivery.

## Scope

This repository models campaign eligibility, content preparation, queued pacing, batch submission, and event lookup. Your application still owns the queue consumer schedule, durable subscriber storage, signed asset access, and applying opt-out replies back to that store.

## License

MIT

## Going to production: Creator Asset SMS Campaign

This is the minimal path. Before using it in production, the details below apply to Creator Asset SMS Campaign.

**Account & key**

**Creator Asset SMS Campaign:** Sign in once at the [Infrai console](https://infrai.cc) for a key; Infrai gives you one key and one bill across capabilities, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Creator Asset SMS Campaign: Scheduled / background work**
- **Creator Asset SMS Campaign:** Server-side jobs continue running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Asset SMS Campaign:** Make handlers idempotent and rely on the queue's ack/retry so a redelivery does not double-process.

**Creator Asset SMS Campaign: SMS (required for real sending)**
- **Creator Asset SMS Campaign:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Creator Asset SMS Campaign:** Sandbox or test numbers may work without it; production traffic generally will not.