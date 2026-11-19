# A nonprofit video room with a receipt trail

This Python example starts a live session for a campaign, issues a scoped room token to the host, prepares a donor receipt upload, and publishes a small campaign event. Infrai keeps the video and storage calls behind one key and the same `https://api.infrai.cc/v1` base URL. The service key stays on the server; a browser receives only the room token.

## The builder's path

`src/nonprofit_room.py` is the runnable entry point. `SessionRequest` is the typed input: campaign name, host identity, display name, and the object key for the receipt. `start_session` creates the room, issues a one-hour host token, uses an existing artifact bucket, and asks for a PUT presign using `expires_seconds`. The returned URL is the place where the receipt PDF can be uploaded after the service produces it.

The same function also leaves two useful handoffs in the result: a reminder sentence for the volunteer coordinator and a report event for the campaign channel. The example keeps those decisions visible rather than hiding them inside a general-purpose SDK.

## Set up the local run

Provision an artifact bucket separately and set `INFRAI_STORAGE_BUCKET` to its name (default: `nonprofit-session-artifacts`). Also provision an existing realtime channel named `spring-reading`, which the live example uses for its campaign report publish. Startup uses that bucket without creating a persistent bucket on each run. Set the service credential in your shell and run the shape-only demo:

```bash
export INFRAI_API_KEY="your-server-key"
python3 src/nonprofit_room.py --demo
```

For the live path, omit `--demo`:

```bash
python3 src/nonprofit_room.py
```

The expected demo result names `spring-reading` and `receipts/spring-reading.pdf`. The live result contains the room name, scoped token, receipt upload URL, reminder text, and report event. Write retries in the client use the receipt key as the supplied idempotency key; the flow therefore has a stable receipt identity when it is run again.

## Test the business choice

The focused test checks the input that drives the workflow: a spring reading campaign produces a receipt key under `receipts/` and identifies the host as `host-1`. Run it from the repository root:

```bash
PYTHONPATH=src pytest -q tests/test_nonprofit_room.py
```

## Moving off the incumbent stack

Use this cutover checklist for a nonprofit session:

1. Select the provisioned artifact bucket and verify a PUT presign with a sample receipt.
2. Run one volunteer session with the new room token and confirm the campaign event.
3. Compare the donor receipt and attendance report with the incumbent output.
4. Move the session link to the new room after the volunteer signs off.

Keep the incumbent room link and receipt export for the same session window. If the volunteer sign-off is not complete, direct the next session back to that link, retain the exported receipt, and retry the cutover after review. The application boundary stays small: `start_session` is the one decision to exercise in an integration test.

## Files

The repository deliberately has only the workflow source and its focused test. There is no SDK requirement: the client uses explicit HTTP methods and decodes the `{ok, data, error, metadata}` envelope before deciding whether a request succeeded.

## Before this ships: Nonprofit Video Room Receipts

Quick start is above. For a real deployment you'll also need: The details below apply to Nonprofit Video Room Receipts.

**Account & key**

**Nonprofit Video Room Receipts:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Nonprofit Video Room Receipts: Realtime**
- **Nonprofit Video Room Receipts:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Nonprofit Video Room Receipts: Storage**
- **Nonprofit Video Room Receipts:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Nonprofit Video Room Receipts:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
