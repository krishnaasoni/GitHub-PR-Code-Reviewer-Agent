"""Telegram GitHub PR & Code Reviewer Agent.

FastAPI background worker integrating with Switch AI Gateway (Telegram Protocol)
and Google Gemini API (gemini-1.5-flash) for automated Pull Request & Code reviews.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_pr_reviewer")

# ---------------------------------------------------------------------------
# Automatic .env Loader (Zero-dependency fallback)
# ---------------------------------------------------------------------------
def _load_dotenv_fallback(filepath: str = ".env") -> None:
    """Reads .env into os.environ if present, without requiring python-dotenv."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception as exc:
            logger.warning("Could not auto-load .env file: %s", exc)

_load_dotenv_fallback()

# ---------------------------------------------------------------------------
# Environment Variables & Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()
MAX_DIFF_CHARS: int = int(os.getenv("MAX_DIFF_CHARS", "40000"))
PORT: int = int(os.getenv("PORT", "8000"))

# Check for google-genai SDK
GENAI_SDK_AVAILABLE = False
try:
    from google import genai
    from google.genai import types

    GENAI_SDK_AVAILABLE = True
    logger.info("google-genai SDK successfully imported.")
except ImportError:
    logger.warning("google-genai SDK not found; using direct Gemini REST API fallback via httpx.")

# ---------------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Telegram GitHub PR & Code Reviewer Agent",
    description="Production-ready Switch AI Gateway worker for Telegram code & PR reviews powered by Gemini.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------
GITHUB_PR_REGEX = re.compile(
    r"https?://github\.com/(?P<owner>[\w\-\.]+)/(?P<repo>[\w\-\.]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)

CODE_SNIPPET_INDICATORS = [
    "def ",
    "class ",
    "import ",
    "from ",
    "return ",
    "function",
    "const ",
    "let ",
    "var ",
    "public ",
    "private ",
    "void ",
    "async ",
    "await ",
    "fn ",
    "struct ",
    "impl ",
    "package ",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "diff --git",
    "--- a/",
    "+++ b/",
    "@@ -",
]

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_REVIEW_PROMPT = """You are an elite Senior Staff Security & Code Review Engineer.
Analyze the provided code diff or snippet with precision.

Structure your review strictly following this Telegram-compatible Markdown format:

🔍 *CODE REVIEW & SECURITY AUDIT*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 *Scope:* <Brief 1-line summary of what this code or PR change does>
🛡️ *Code Safety Score:* <Score>/10 (<Safe | Needs Attention | High Risk>)

🚨 *1. Security & Secrets Analysis*
• <Identify potential vulnerabilities: hardcoded credentials/tokens, SQL injection, XSS, SSRF, IDOR, unsanitized inputs, insecure crypto, or "✅ No immediate security vulnerabilities detected.">

⚡ *2. Performance & Scalability*
• <Identify computational bottlenecks: N+1 queries, unindexed lookups, unbounded loops, memory leaks, high Big-O complexity, or "✅ Performance characteristics look solid.">

🐛 *3. Bugs & Code Quality*
• <Identify logic flaws: unhandled exceptions, null/None dereference, race conditions, resource leaks, edge cases, or "✅ Code quality is robust.">

💡 *4. Recommended Fix Snippet*
```<language>
// Concrete drop-in fix snippet addressing the highest-severity issue found
```

📋 *Verdict:* <✅ APPROVED | ⚠️ CHANGES REQUESTED> - <One sentence concise rationale>

Formatting Guidelines for Telegram compatibility:
- Use single asterisks for bold (e.g. *bold*).
- Use backticks for inline code (`code`) and triple backticks for code blocks.
- Keep bullet points punchy, direct, and actionable. Avoid filler commentary.
"""

HELP_MESSAGE = """👋 *Welcome to the Telegram GitHub PR & Code Reviewer Agent!*

I am an AI code review specialist connected via *Switch AI Gateway* and powered by *Google Gemini 1.5 Flash*.

🚀 *How to use me:*

1️⃣ *Review a GitHub Pull Request:*
Send any GitHub PR URL directly in the chat:
👉 `https://github.com/owner/repo/pull/42`

2️⃣ *Review a Code Snippet or Raw Diff:*
Send your code or unified diff wrapped in backticks or code blocks:
```python
def query_user(user_id):
    return db.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

🔍 *What I audit:*
• 🚨 *Security & Secrets* (SQLi, exposed keys, XSS, SSRF)
• ⚡ *Performance & Big-O* (N+1 queries, unindexed lookups)
• 🐛 *Bugs & Edge Cases* (unhandled exceptions, nulls)
• 🛡️ *Code Safety Score* (0 to 10 rating)
• 💡 *Actionable Code Fixes* (drop-in code snippet)

Paste a GitHub PR link or code snippet to get started!"""


# ---------------------------------------------------------------------------
# Pydantic Models for Endpoints
# ---------------------------------------------------------------------------
class ReviewRequest(BaseModel):
    """Direct review request payload."""

    url: Optional[str] = Field(None, description="GitHub Pull Request URL")
    code: Optional[str] = Field(None, description="Raw code snippet or unified diff")
    chat_id: Optional[str | int] = Field(None, description="Optional Telegram Chat ID")


class ReviewResponse(BaseModel):
    """Review response model."""

    status: str
    target_type: str
    target: str
    review: str
    chat_id: Optional[str | int] = None


# ---------------------------------------------------------------------------
# Helper Functions: Diff Fetching & Detection
# ---------------------------------------------------------------------------
def extract_github_pr_url(text: str) -> Optional[Tuple[str, str, str, str]]:
    """Detects and parses a GitHub Pull Request URL.

    Returns: (full_match, owner, repo, pr_number) or None.
    """
    match = GITHUB_PR_REGEX.search(text)
    if match:
        return (
            match.group(0),
            match.group("owner"),
            match.group("repo"),
            match.group("number"),
        )
    return None


def is_code_or_diff(text: str) -> bool:
    """Heuristic check to determine if incoming text is code or diff."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return True
    if any(stripped.startswith(prefix) for prefix in ["diff --git", "--- a/", "+++ b/", "@@"]):
        return True

    # Count matching code indicator keywords
    matches = sum(1 for indicator in CODE_SNIPPET_INDICATORS if indicator in text)
    if matches >= 2:
        return True

    # Check for multi-line block with indentation / brackets / braces
    lines = stripped.splitlines()
    if len(lines) >= 3 and any(char in stripped for char in ("{", "}", ";", "()", "->", "=>")):
        return True

    return False


def clean_code_snippet(text: str) -> str:
    """Cleans markdown code fences if wrapped by the user."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            # Drop the opening line (```python) and closing line (```)
            return "\n".join(lines[1:-1]).strip()
    return stripped


async def fetch_github_pr_diff(owner: str, repo: str, pr_number: str) -> str:
    """Fetches the unified diff for a GitHub Pull Request.

    Uses standard HTTP request with `.diff` extension, with fallback to GitHub API.
    """
    diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {
        "User-Agent": "Telegram-PR-Reviewer-Agent/1.0",
        "Accept": "application/vnd.github.v3.diff",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # 1. Attempt fetching via public .diff URL
        try:
            resp = await client.get(diff_url, headers=headers)
            if resp.status_code == 200 and resp.text.strip():
                return resp.text
        except httpx.RequestError as exc:
            logger.warning("Error fetching from .diff URL: %s. Trying GitHub REST API...", exc)

        # 2. Attempt fetching via official GitHub REST API with diff Accept header
        try:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200 and resp.text.strip():
                return resp.text
            elif resp.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"GitHub PR #{pr_number} on {owner}/{repo} was not found. Please verify the URL or ensure GITHUB_TOKEN is configured for private repos.",
                )
            elif resp.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"GitHub API rate limit exceeded or access forbidden for {owner}/{repo}. Set GITHUB_TOKEN in your environment to resolve.",
                )
            else:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Failed to fetch PR diff from GitHub (HTTP {resp.status_code}): {resp.text[:200]}",
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Network error connecting to GitHub: {exc}",
            )


# ---------------------------------------------------------------------------
# Core AI Analysis: Google Gemini Integration
# ---------------------------------------------------------------------------
async def analyze_with_gemini(content: str, context_label: str) -> str:
    """Analyzes the code or diff using Google Gemini.

    Prefers `google-genai` SDK and falls back automatically to direct Gemini REST API.
    """
    if not GEMINI_API_KEY:
        return (
            "⚠️ *Gemini API Key Missing*\n\n"
            "Please configure the `GEMINI_API_KEY` environment variable in your deployment to activate automated reviews."
        )

    # Truncate content safely if exceeding threshold
    if len(content) > MAX_DIFF_CHARS:
        logger.info("Diff size (%d chars) exceeds limit. Truncating to %d chars.", len(content), MAX_DIFF_CHARS)
        content = (
            content[:MAX_DIFF_CHARS]
            + f"\n\n... [DIFF TRUNCATED: Exceeded {MAX_DIFF_CHARS} characters. Reviewing primary changes above.] ..."
        )

    full_prompt = (
        f"{SYSTEM_REVIEW_PROMPT}\n\n"
        f"Target context: {context_label}\n\n"
        f"--- BEGIN CODE / DIFF CONTENT ---\n"
        f"{content}\n"
        f"--- END CODE / DIFF CONTENT ---\n"
    )

    # Strategy 1: google-genai SDK
    if GENAI_SDK_AVAILABLE:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=3500,
                ),
            )
            if response and response.text:
                return response.text.strip()
        except Exception as exc:
            logger.warning("google-genai SDK call failed (%s). Falling back to Gemini REST API.", exc)

    # Strategy 2: Direct Gemini REST API via httpx
    rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 3500,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(rest_url, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini REST API returned HTTP %s: %s", resp.status_code, resp.text)
                return f"⚠️ *Gemini Analysis Error:* Failed to analyze code (HTTP {resp.status_code})."

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text_part:
                    return text_part.strip()
            return "⚠️ *Gemini Analysis Error:* No response candidates returned by model."
    except Exception as exc:
        logger.exception("Failed to query Gemini REST API: %s", exc)
        return f"⚠️ *Gemini Connection Error:* {exc}"


# ---------------------------------------------------------------------------
# Telegram Utilities: Chunking & Dispatching
# ---------------------------------------------------------------------------
def split_telegram_message(text: str, max_length: int = 4000) -> List[str]:
    """Splits a response message to respect Telegram's 4096 character limit."""
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current_chunk = ""

    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            current_chunk = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(paragraph) > max_length:
                # Break large single paragraphs by line
                lines = paragraph.splitlines()
                sub_chunk = ""
                for line in lines:
                    if len(sub_chunk) + len(line) + 1 <= max_length:
                        sub_chunk = f"{sub_chunk}\n{line}" if sub_chunk else line
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = line
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def send_telegram_message(chat_id: str | int, text: str) -> None:
    """Dispatches message back to Telegram via official Bot API.

    Gracefully falls back to plain text if Markdown entity parsing fails.
    """
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.info("TELEGRAM_BOT_TOKEN or chat_id omitted; skipping direct Telegram dispatch.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = split_telegram_message(text)

    async with httpx.AsyncClient(timeout=20.0) as client:
        for chunk in chunks:
            # 1. Try sending with Markdown parse mode
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    continue

                # If Telegram reports Markdown parsing error, retry in plain text mode
                logger.warning(
                    "Telegram rejected Markdown (HTTP %s: %s). Retrying plain text.",
                    resp.status_code,
                    resp.text,
                )
                payload.pop("parse_mode", None)
                await client.post(url, json=payload)
            except Exception as exc:
                logger.error("Failed to send message to Telegram chat %s: %s", chat_id, exc)


# ---------------------------------------------------------------------------
# Business Logic: Input Processing Pipeline
# ---------------------------------------------------------------------------
async def process_user_input(
    raw_text: str, chat_id: Optional[str | int] = None
) -> Tuple[str, str, str]:
    """Processes incoming user text and returns (response_markdown, target_type, target_name)."""
    text = raw_text.strip()

    # 1. Check for Telegram commands or help requests
    if text in ("/start", "/help") or not text:
        return HELP_MESSAGE, "help", "help_command"

    # 2. Check for GitHub Pull Request URL
    pr_info = extract_github_pr_url(text)
    if pr_info:
        pr_url, owner, repo, pr_number = pr_info
        target_name = f"{owner}/{repo}#pull/{pr_number}"
        logger.info("Detected GitHub PR request: %s", target_name)

        try:
            diff_content = await fetch_github_pr_diff(owner, repo, pr_number)
            if not diff_content.strip():
                return (
                    f"⚠️ *Empty PR Diff*\n\nPR #{pr_number} in `{owner}/{repo}` contains no diff or changes.",
                    "github_pr",
                    target_name,
                )

            review = await analyze_with_gemini(
                diff_content,
                context_label=f"GitHub PR {target_name} ({pr_url})",
            )
            return review, "github_pr", target_name
        except HTTPException as exc:
            return f"⚠️ *Error fetching PR diff:*\n\n{exc.detail}", "error", target_name
        except Exception as exc:
            logger.exception("Unexpected error fetching PR diff: %s", exc)
            return f"⚠️ *Unexpected error fetching PR:* {exc}", "error", target_name

    # 3. Check for Code Snippet or Raw Diff
    if is_code_or_diff(text):
        cleaned_code = clean_code_snippet(text)
        logger.info("Detected code snippet / diff (%d characters)", len(cleaned_code))
        review = await analyze_with_gemini(
            cleaned_code,
            context_label="Direct Code Snippet / Diff Submission",
        )
        return review, "code_snippet", "user_code"

    # 4. If neither, return informative help guide
    logger.info("Non-code message received. Returning help guide.")
    return HELP_MESSAGE, "help", "unrecognized_input"


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["General"])
async def root():
    """Service status and quick info."""
    return {
        "service": "Telegram GitHub PR & Code Reviewer Agent",
        "status": "operational",
        "gemini_sdk_enabled": GENAI_SDK_AVAILABLE,
        "gemini_model": GEMINI_MODEL,
        "telegram_integration": bool(TELEGRAM_BOT_TOKEN),
        "docs": "/docs",
    }


@app.get("/health", tags=["General"])
async def health():
    """Health check endpoint for Docker and Switch Gateway probes."""
    return {
        "status": "healthy",
        "gemini_configured": bool(GEMINI_API_KEY),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
    }


@app.post("/review", response_model=ReviewResponse, tags=["Review"])
async def direct_review(request: ReviewRequest, background_tasks: BackgroundTasks):
    """Direct REST endpoint to review a GitHub PR URL or raw code snippet.

    Useful for CI/CD pipelines, curl tests, or automated agent calls.
    """
    input_text = request.url or request.code or ""
    if not input_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'url' (GitHub PR link) or 'code' (code snippet/diff).",
        )

    review_text, target_type, target_name = await process_user_input(
        input_text, chat_id=request.chat_id
    )

    if request.chat_id and TELEGRAM_BOT_TOKEN:
        background_tasks.add_task(send_telegram_message, request.chat_id, review_text)

    return ReviewResponse(
        status="success",
        target_type=target_type,
        target=target_name,
        review=review_text,
        chat_id=request.chat_id,
    )


@app.post("/webhook", tags=["Switch AI Gateway & Telegram"])
async def switch_telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Entry point for Switch AI Gateway (Telegram Protocol) or direct Telegram Webhooks.

    Accepts diverse payload schemas:
    1. Switch Gateway format: {"message": "...", "chat_id": "...", "sender": "..."}
    2. Direct Telegram Update: {"update_id": ..., "message": {"chat": {"id": ...}, "text": "..."}}
    3. Generic agent payload: {"text": "...", "chat_id": ...}
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as exc:
        logger.error("Invalid JSON received at /webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")

    logger.info("Webhook received payload keys: %s", list(payload.keys()))

    extracted_text: Optional[str] = None
    chat_id: Optional[str | int] = None

    # Schema 1: Standard Telegram Bot API Update format
    if "message" in payload and isinstance(payload["message"], dict):
        msg = payload["message"]
        extracted_text = msg.get("text") or msg.get("caption")
        chat_info = msg.get("chat", {})
        chat_id = chat_info.get("id")

    # Schema 2: Switch AI Gateway message format
    elif "text" in payload:
        extracted_text = str(payload.get("text"))
        chat_id = payload.get("chat_id") or payload.get("channel_id")
    elif "message" in payload and isinstance(payload["message"], str):
        extracted_text = payload.get("message")
        chat_id = payload.get("chat_id")
    elif "content" in payload:
        extracted_text = str(payload.get("content"))
        chat_id = payload.get("chat_id")
    elif "query" in payload:
        extracted_text = str(payload.get("query"))
        chat_id = payload.get("chat_id")

    # Fallback: Empty or non-text message (e.g. sticker, photo without caption)
    if not extracted_text:
        logger.info("No text content found in webhook payload.")
        return JSONResponse(
            status_code=200,
            content={
                "status": "ignored",
                "reason": "Payload contained no reviewable text content.",
            },
        )

    # Process through review pipeline
    review_text, target_type, target_name = await process_user_input(extracted_text, chat_id=chat_id)

    # If chat_id is present and token configured, dispatch to Telegram asynchronously
    if chat_id and TELEGRAM_BOT_TOKEN:
        background_tasks.add_task(send_telegram_message, chat_id, review_text)

    # Also return payload synchronously for Switch Gateway / caller
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "chat_id": chat_id,
            "target_type": target_type,
            "target": target_name,
            "response": review_text,
            "parse_mode": "Markdown",
        },
    )


# ---------------------------------------------------------------------------
# Main Entry Point for Local Development
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Telegram PR Reviewer Agent on port %d...", PORT)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

