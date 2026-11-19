from nonprofit_room import SessionRequest, demo_request


def test_demo_request_keeps_receipt_in_campaign_bucket() -> None:
    request = demo_request()
    assert isinstance(request, SessionRequest)
    assert request.campaign == "spring-reading"
    assert request.receipt_key.startswith("receipts/")
    assert request.host_identity == "host-1"


def test_start_session_uses_existing_bucket_without_creating_one() -> None:
    from nonprofit_room import start_session

    class Client:
        def __init__(self):
            self.calls = []

        def request(self, method, path, body=None):
            self.calls.append((method, path))
            return {"data": {"name": "spring-reading", "token": "host-token", "url": "https://upload.example"}}

    client = Client()
    result = start_session(client, demo_request(), "existing-artifacts")
    assert result.token == "host-token"
    assert client.calls == [
        ("POST", "/rtc/room/create"),
        ("POST", "/rtc/token/issue"),
        ("POST", "/storage/object/presign/existing-artifacts/receipts/spring-reading.pdf"),
        ("POST", "/realtime/publish"),
    ]
