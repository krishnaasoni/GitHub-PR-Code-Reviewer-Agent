# 🤖 Telegram GitHub PR & Code Reviewer Agent

> **Submission for "Flip the Switch Hackathon"**  
> *Connecting isolated AI code review intelligence to collaborative Telegram team channels via Switch AI Gateway and Google Gemini 1.5 Flash.*

---

## 🌟 Overview

The **Telegram GitHub PR & Code Reviewer Agent** is a production-ready, lightweight FastAPI background worker service. It acts as an autonomous virtual teammate inside Telegram developer groups and direct chats.

Instead of navigating between GitHub, IDEs, and isolated terminal windows, developers can simply paste a **GitHub Pull Request link** (e.g. `https://github.com/owner/repo/pull/42`) or **raw code snippet/diff** directly in Telegram. The agent instantly audits the code and returns an actionable, formatted markdown review with a **Code Safety Score**, security vulnerability analysis, performance warnings, and concrete drop-in fix snippets.

```
                  ┌──────────────────────┐
                  │   Telegram User      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Switch AI Gateway   │ (Telegram Bridge / Webhook)
                  └──────────┬───────────┘
                             │  POST /webhook
                             ▼
         ┌───────────────────────────────────────────────┐
         │     FastAPI Reviewer Worker (main.py)         │
         │                                               │
         │  1. Ingests & Normalizes Payload              │
         │  2. Detects GitHub PR vs Code Snippet         │
         │  3. Fetches Raw Unified Diff (.diff / API)    │
         │  4. Gemini 1.5 Flash Deep Security Audit      │
         │  5. Chunks & Formats Telegram Markdown        │
         └───────────────┬───────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
┌────────────────┐              ┌──────────────────┐
│ Telegram Chat  │              │ Switch AI Output │
│ (via Bot API)  │              │ (REST Response)  │
└────────────────┘              └──────────────────┘
```

---

## 🚀 Key Features

- **⚡ Blazing Fast AI Analysis**: Powered by Google Gemini (`gemini-1.5-flash`), with dual-engine support: `google-genai` SDK and zero-dependency async HTTP fallback via `httpx`.
- **🔗 Automatic GitHub PR Diff Resolution**: Detects PR URLs, appends `.diff` for public repos, and seamlessly falls back to GitHub REST API with optional `GITHUB_TOKEN` for private repos and elevated rate limits.
- **🛡️ 5-Point Deep Code Audit**:
  1. **Security & Secrets**: Hardcoded tokens, SQL injection, XSS, SSRF, IDOR, unsanitized inputs.
  2. **Performance & Scalability**: N+1 queries, unindexed lookups, memory leaks, high Big-O complexity.
  3. **Bugs & Code Quality**: Unhandled exceptions, null/None dereference, race conditions, edge cases.
  4. **Code Safety Score**: Clear 0–10 rating (`Safe`, `Needs Attention`, or `High Risk`).
  5. **Recommended Fix Snippet**: Drop-in code snippet with syntax highlighting.
- **📱 Telegram Native UX**: Engineered with Markdown formatting compatible with Telegram, auto-splitting messages exceeding Telegram's 4,096 character limit, and fallback to plain text if markdown parsing fails.
- **🔌 Multi-Protocol Webhook Receiver**: Native support for **Switch AI Gateway** payloads, standard **Telegram Bot API Webhook Updates**, and direct REST testing (`/review`).

---

## 📦 Project Structure

```
├── main.py              # Single-file FastAPI worker, diff fetcher & Gemini integration
├── requirements.txt     # Minimal dependencies (fastapi, uvicorn, httpx, google-genai, pydantic)
├── docker-compose.yml   # Multi-container orchestration (FastAPI worker + Switch Gateway)
├── Dockerfile           # Multi-stage lightweight Python container
├── .env.example         # Environment variables template
├── test_reviewer.py     # Unit test suite verifying parsing, regex, and message chunking
└── README.md            # Comprehensive project documentation
```

---

## ⚙️ Quickstart Guide

### 1. Prerequisites
- Python 3.10+ or Docker installed
- A [Google AI Studio Gemini API Key](https://aistudio.google.com/)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Configure Environment
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials:
```env
GEMINI_API_KEY=AIzaSy...
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
GITHUB_TOKEN=ghp_...                # Optional, for private repos
PORT=8000
```

### 3. Running Locally with Python
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the worker
python main.py
```
The server will start at `http://0.0.0.0:8000`. Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

---

## 🐳 Running with Docker & Switch AI Gateway

### Option A: Complete Docker Compose Stack
Spin up both the FastAPI Reviewer Worker and the Switch AI Gateway:
```bash
docker compose up --build -d
```
Check the status:
```bash
docker compose ps
docker compose logs -f reviewer-agent
```

### Option B: Running Switch AI Gateway via CLI
If you run Switch AI Gateway standalone or via its CLI:
```bash
# Launch Switch Gateway pointing to the local FastAPI worker
switch gateway --channel telegram \
               --token "$TELEGRAM_BOT_TOKEN" \
               --target "http://localhost:8000/webhook"
```

---

## 🧪 Testing the Service

### 1. Health Check
```bash
curl http://localhost:8000/health
```
Response:
```json
{
  "status": "healthy",
  "gemini_configured": true,
  "telegram_configured": true
}
```

### 2. Direct Review API (`/review`)
Review a GitHub Pull Request:
```bash
curl -X POST http://localhost:8000/review \
     -H "Content-Type: application/json" \
     -d '{"url": "https://github.com/fastapi/fastapi/pull/12"}'
```

Review a raw code snippet:
```bash
curl -X POST http://localhost:8000/review \
     -H "Content-Type: application/json" \
     -d '{
       "code": "def get_user(uid): return db.execute(f\"SELECT * FROM users WHERE id = {uid}\")"
     }'
```

### 3. Simulate Switch AI Gateway Webhook (`/webhook`)
```bash
curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "chat_id": 987654321,
       "message": "https://github.com/tiangolo/fastapi/pull/12"
     }'
```

---

## 📱 Sample Telegram Review Output

When a user shares a PR link or code snippet in Telegram, the agent replies:

```markdown
🔍 *CODE REVIEW & SECURITY AUDIT*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 *Scope:* Direct SQL query parameter concatenation in user lookup handler
🛡️ *Code Safety Score:* 2.5/10 (High Risk)

🚨 *1. Security & Secrets Analysis*
• Critical SQL Injection vulnerability: `uid` parameter is interpolated directly into raw SQL string without sanitization or parameter binding.
• An attacker can supply `uid = "1 OR 1=1"` or execute destructive queries.

⚡ *2. Performance & Scalability*
• Missing index check on `users.id` could cause full table scans on large user tables.
• Lack of query result caching.

🐛 *3. Bugs & Code Quality*
• Unhandled database connection errors.
• Missing type annotations and input validation.

💡 *4. Recommended Fix Snippet*
```python
from sqlalchemy import text

def get_user(uid: int):
    # Use parameterized query to completely mitigate SQL injection
    query = text("SELECT id, username, email FROM users WHERE id = :uid")
    return db.execute(query, {"uid": uid}).fetchone()
```

📋 *Verdict:* ⚠️ CHANGES REQUESTED - High severity SQL injection risk must be patched before merging.
```

---

## 🔒 Security & Reliability Design

- **Zero Secret Exposure**: Tokens and API keys are injected solely through environment variables.
- **Diff Truncation Safeguard**: Configurable `MAX_DIFF_CHARS` (default 40,000 characters) protects against oversized PR diffs that could trigger token overflow or high latency.
- **Dual AI Engine**: If `google-genai` encounters any environment discrepancies, the worker automatically transitions to direct HTTP calls to the Gemini REST API with zero downtime.
- **Message Chunking**: Safely splits review reports across paragraphs if exceeding Telegram's 4,096 character limit.
- **Plaintext Fallback**: If Telegram rejects Markdown entities, automatically retransmits the message in plain text to ensure the developer always receives their review.

---

## 🏆 Hackathon Alignment ("Flip the Switch")

- **Transforms Solo AI into Collaborative Teammate**: Instead of developers running local linters in isolation, the entire team can tag the reviewer bot in group threads to debate and verify PRs collaboratively.
- **Zero Friction**: Works natively inside Telegram without requiring browser extension or IDE plugin installation.
- **High Speed**: Built on `gemini-1.5-flash` with sub-3-second end-to-end review latency.

