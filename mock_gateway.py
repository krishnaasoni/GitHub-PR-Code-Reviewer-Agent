"""Switch AI Gateway Simulator / Demo CLI.

Simulates incoming Telegram messages routed through Switch AI Gateway to test
the FastAPI Reviewer Worker locally without requiring an active Telegram Bot Token.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error

DEFAULT_WEBHOOK_URL = "http://localhost:8000/webhook"

SAMPLE_SNIPPETS = {
    "1": {
        "title": "SQL Injection & Hardcoded Credential Flaw",
        "content": """```python
import os
import psycopg2

DATABASE_PASSWORD = "super_secret_production_password_123!"

def authenticate_user(username, raw_password):
    conn = psycopg2.connect(f"dbname=prod user=admin password={DATABASE_PASSWORD} host=127.0.0.1")
    cur = conn.cursor()
    # Direct string formatting - critical SQL injection
    query = f"SELECT id, role FROM users WHERE username = '{username}' AND password_hash = '{raw_password}'"
    cur.execute(query)
    return cur.fetchone()
```""",
    },
    "2": {
        "title": "O(N^2) Performance Bottleneck & Memory Leak",
        "content": """```python
def find_common_transactions(list_a, list_b):
    # O(N*M) nested loop causing severe latency spikes on large transaction batches
    common = []
    for item_a in list_a:
        for item_b in list_b:
            if item_a['id'] == item_b['id']:
                common.append(item_a)
    return common
```""",
    },
    "3": {
        "title": "GitHub PR: FastAPI Pull Request #12",
        "content": "https://github.com/fastapi/fastapi/pull/12",
    },
    "4": {
        "title": "Help / Onboarding Request",
        "content": "/help",
    },
}


def send_to_webhook(url: str, message: str, chat_id: int = 99887766) -> dict:
    """Dispatches a mock Switch Gateway Telegram payload to the worker."""
    payload = {
        "chat_id": chat_id,
        "message": message,
        "sender": "HackathonJudge",
        "platform": "telegram",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Switch-Gateway-Simulator/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"\n❌ Error connecting to worker at {url}: {exc}")
        print("👉 Make sure your FastAPI worker is running: python main.py")
        sys.exit(1)


def main():
    print("=" * 70)
    print(" 🚀 Switch AI Gateway - Telegram Reviewer Simulator")
    print("=" * 70)
    print(f"Target Endpoint: {DEFAULT_WEBHOOK_URL}\n")

    print("Select a demo test case:")
    for key, val in SAMPLE_SNIPPETS.items():
        print(f"  [{key}] {val['title']}")
    print("  [C] Custom GitHub PR URL or Code Snippet")
    print("  [Q] Quit\n")

    choice = input("Enter choice [1-4, C, Q]: ").strip().upper()

    if choice == "Q":
        print("Goodbye!")
        return

    if choice in SAMPLE_SNIPPETS:
        selected = SAMPLE_SNIPPETS[choice]
        print(f"\n▶ Sending: {selected['title']} ...")
        message = selected["content"]
    elif choice == "C":
        print("\nEnter custom input (GitHub PR link or code):")
        message = input("> ").strip()
        if not message:
            print("No input provided. Exiting.")
            return
    else:
        print("Invalid option.")
        return

    print("\n⏳ Dispatching to FastAPI /webhook through Switch Gateway...")
    result = send_to_webhook(DEFAULT_WEBHOOK_URL, message)

    print("\n" + "=" * 70)
    print(" 📨 RESPONSE FROM REVIEWER AGENT (Telegram Markdown):")
    print("=" * 70)
    print(result.get("response", json.dumps(result, indent=2)))
    print("=" * 70)
    print(f"Target Type: {result.get('target_type')} | Target: {result.get('target')}")
    print("Status: SUCCESS ✔")


if __name__ == "__main__":
    main()

