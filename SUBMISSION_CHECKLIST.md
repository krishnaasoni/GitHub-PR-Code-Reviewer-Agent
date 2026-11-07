# 📝 Flip the Switch Hackathon - Submission Form Guide

Copy and paste these pre-formatted sections directly into your hackathon submission on Devpost or WeMakeDevs:

---

### Project Name
**Telegram PR & Code Reviewer Agent (Powered by Switch AI & Gemini)**

### Elevator Pitch / Tagline (1 sentence)
*An autonomous AI code review teammate that audits GitHub PRs and code snippets for security, performance, and bugs directly inside Telegram team chats within 3 seconds.*

---

### Inspiration
Solo AI coding assistants (like Cursor, Claude Code, and Copilot) operate on an "island"—isolated inside a single developer's IDE. Meanwhile, real engineering collaboration happens in messaging apps like Telegram. We wanted to "Flip the Switch" by transforming isolated code review intelligence into an active, collaborative teammate living directly in team chat rooms.

---

### What it does
- **GitHub PR Auditing**: Drop any public or private GitHub PR link into Telegram. The agent fetches the unified diff and runs a comprehensive security and quality audit.
- **5-Point Deep Analysis**:
  1. 🚨 **Security & Secrets**: Catches SQL injections, hardcoded passwords/tokens, XSS, SSRF, and unsanitized inputs.
  2. ⚡ **Performance & Big-O**: Identifies N+1 query loops, unindexed lookups, and memory leaks.
  3. 🐛 **Bugs & Edge Cases**: Flags unhandled exceptions, null pointer risks, and race conditions.
  4. 🛡️ **Code Safety Score**: Provides an objective 0–10 score with risk classification.
  5. 💡 **Drop-In Fix Snippet**: Generates syntactically correct, secure replacement code.
- **Pre-PR Snippet Review**: Developers can paste raw code snippets or Git diffs into Telegram before opening a PR to catch flaws early.
- **Telegram Native UX**: Formatted with Telegram-friendly Markdown, emoji indicators, and automatic chunking for Telegram's 4,096 character limit.

---

### How we built it
- **Switch AI Gateway**: Routes messages seamlessly between Telegram and our agent worker.
- **FastAPI (Python 3.11)**: Async high-throughput REST service handling payload normalization, GitHub diff resolution, and response dispatching.
- **Google Gemini 1.5 Flash**: Powered by Google's fastest multimodal model, featuring dual-engine integration (`google-genai` SDK + automatic fallback to direct async REST API).
- **GitHub Diff Engine**: Fetches unified diffs using `.diff` and official REST APIs with personal access token authentication for private repos.
- **Docker & Docker Compose**: Multi-container setup orchestrating the FastAPI worker and Switch Gateway.

---

### Challenges we ran into
- Handling Telegram's strict Markdown formatting constraints without causing entity parsing errors. We built a resilient auto-retry mechanism that falls back to plain text if Telegram rejects malformed Markdown entities.
- Managing oversized PR diffs. We introduced dynamic diff truncation and character bounds to ensure Gemini receives critical diff changes without latency degradation or token overflow.

---

### Accomplishments that we're proud of
- Sub-3-second end-to-end review latency from Telegram message dispatch to received audit.
- Zero-placeholder, production-ready codebase with unit tests, CI/CD GitHub Actions, and one-click cloud deployment.
- True team collaboration: an entire engineering channel can debate and approve PR reviews together in real time.

---

### Try it out (Quick GitHub Push)
```bash
git init
git add .
git commit -m "feat: Telegram GitHub PR & Code Reviewer Agent with Switch AI Gateway"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

