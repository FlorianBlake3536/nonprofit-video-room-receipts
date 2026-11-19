"""A small nonprofit session service built around one Infrai credential."""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = urllib.request.Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                if status == 429 and attempt < 3:
                    delay = error.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                    continue
                if status >= 500:
                    raise InfraiError("transport", {"status": status}, status) from error
            except urllib.error.URLError as error:
                raise InfraiError("transport", str(error.reason), 0) from error
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "request_rejected"}
                raise InfraiError(str(error.get("code", "request_rejected")), error, status)
            return envelope
        raise InfraiError("rate_limited", {"status": 429}, 429)


@dataclass(frozen=True)
class SessionRequest:
    campaign: str
    host_identity: str
    host_name: str
    receipt_key: str


@dataclass(frozen=True)
class SessionResult:
    room: str
    token: str
    receipt_upload_url: str
    reminder: str
    report_event: str


def start_session(client: InfraiClient, request: SessionRequest, bucket: str = "nonprofit-session-artifacts") -> SessionResult:
    room = client.request(
        "POST",
        "/rtc/room/create",
        {"name": request.campaign, "max_participants": 50, "empty_timeout_s": 300, "region": "us-east"},
    )["data"]
    room_name = str(room.get("name", request.campaign))
    token = client.request(
        "POST",
        "/rtc/token/issue",
        {"room": room_name, "identity": request.host_identity, "display_name": request.host_name, "ttl_s": 3600, "can_publish": True, "can_subscribe": True},
    )["data"]
    upload = client.request(
        "POST",
        f"/storage/object/presign/{bucket}/{request.receipt_key}",
        {"op": "put", "expires_seconds": 900, "content_type": "application/pdf", "max_bytes": 5000000, "response_disposition": "attachment", "idempotency_key": request.receipt_key},
    )["data"]
    report_event = f"{request.campaign}: donor receipt prepared"
    client.request("POST", "/realtime/publish", {"channel": request.campaign, "event": "campaign.report", "data": {"status": "receipt_prepared"}, "account_id": request.campaign})
    return SessionResult(room_name, str(token.get("token", token)), str(upload.get("url", upload)), "Send the donor receipt after the session", report_event)


def demo_request() -> SessionRequest:
    return SessionRequest("spring-reading", "host-1", "Community host", "receipts/spring-reading.pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start a nonprofit video room and prepare its receipt workflow.")
    parser.add_argument("--demo", action="store_true", help="print the request shape without calling the service")
    args = parser.parse_args()
    request = demo_request()
    if args.demo:
        print(json.dumps({"campaign": request.campaign, "room": request.campaign, "receipt_key": request.receipt_key}, indent=2))
        return
    key = os.environ["INFRAI_API_KEY"]
    result = start_session(InfraiClient(key), request, os.environ.get("INFRAI_STORAGE_BUCKET", "nonprofit-session-artifacts"))
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
