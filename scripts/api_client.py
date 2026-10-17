"""HTTP sender shared by simulate.py and replay.py."""
import time

import requests


def send_events(events, base_url, token):
    session = requests.Session()
    headers = {"INTERNAL-TOKEN": token}
    for event in events:
        started = time.perf_counter()
        try:
            response = session.post(f"{base_url}/pix/transaction", json=event["payload"],
                                    headers=headers, timeout=30)
            status_code = response.status_code
            body = response.json() if response.ok else None
        except (requests.RequestException, ValueError):
            status_code, body = 0, None
        event["latency_ms"] = (time.perf_counter() - started) * 1000
        event["http_status"] = status_code
        event["response"] = body
