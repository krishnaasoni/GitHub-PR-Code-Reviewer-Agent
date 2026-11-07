# 🏆 Hackathon Submission Pitch & Demo Script
**Project:** Telegram GitHub PR & Code Reviewer Agent  
**Event:** Flip the Switch Hackathon (Switch AI & DevTools Academy)  
**Track:** Collaborative AI Teammates in Team Messaging (Telegram)

---

## 🎯 1. The Problem: "The Solo Developer Island"
Today, AI coding assistants (Cursor, Claude Code, GitHub Copilot) are fundamentally **solo, isolated tools**. They sit inside a single developer's IDE or terminal. 

When a developer submits a Pull Request:
1. Reviewers must stop what they are doing, switch windows, and open GitHub.
2. Context, security review, and performance checks happen late in the development cycle.
3. Discussions are fragmented across GitHub comments and private direct messages.
4. Junior developers or busy teams frequently merge critical flaws (SQL injections, exposed API tokens, O(N^2) bottlenecks) because thorough manual reviews take too much time.

---

## 💡 2. The Solution: "Flipping the Switch"
We used **Switch AI Gateway** to bring AI code review intelligence straight into the team's natural communication flow: **Telegram**.

Instead of switching tabs, anyone in the team Telegram group—or a developer on mobile—can simply drop a **GitHub PR URL** (e.g. `https://github.com/org/repo/pull/42`) or **raw code diff**. 

Within **sub-3 seconds**, our agent:
- Pulls the raw unified diff via GitHub's API.
- Runs a multi-stage audit using **Google Gemini 1.5 Flash**.
- Computes an objective **Code Safety Score (0–10)**.
- Flags critical security vulnerabilities and performance bottlenecks.
- Generates a concrete, drop-in replacement fix snippet.
- Posts the result back directly to Telegram in formatted Markdown with warning badges.

The entire team sees the review simultaneously, turning code review from a private chore into a transparent, collaborative team workflow.

---

## 🏗️ 3. Architecture & Tech Stack

```
[ Telegram Chat / Team Room ]
             │
             ▼
[ Switch AI Gateway (Telegram Bridge) ]  <-- Port 3000
             │  POST /webhook
             ▼
[ FastAPI Reviewer Worker (Python 3.11) ] <-- Port 8000
   ├── Diff Extractor (.diff URL + GitHub API Fallback)
   ├── Code Snippet Classifier (Heuristic syntax engine)
   ├── Google Gemini 1.5 Flash (google-genai SDK + Async REST Fallback)
   ├── Telegram Formatter & Message Chunker (4,096 char bounds)
   └── Direct Telegram Dispatcher (Fallback to Plaintext on entities)
```

- **Gateway:** Switch AI Gateway (`sandbox-quantum/switch`) Telegram bridge.
- **Worker:** Python FastAPI + Uvicorn + Pydantic v2.
- **AI Core:** Google Gemini 1.5 Flash via `google-genai` / Gemini REST API.
- **Diff Resolver:** Async HTTP client (`httpx`) resolving `.diff` endpoints with tokenized private repo support.
- **Deployment:** Docker & Docker Compose.

---

## 🎬 4. Live Demo Walkthrough (2-Minute Script)

### Step 1: Show the Problem (30s)
> *"Here is a typical PR where a developer wrote an authentication handler. Notice the hardcoded database password and unsanitized SQL query. In a busy sprint, this might slip through."*

### Step 2: Drop the Link in Telegram (30s)
> *"Instead of waiting hours for a senior reviewer, we paste the PR link directly into our team Telegram group. Switch AI Gateway routes the message to our FastAPI background worker."*

### Step 3: Reveal the Review (45s)
> *"In less than 3 seconds, Gemini 1.5 Flash returns a Telegram review:*
> - *Code Safety Score: 2.5/10 (High Risk)*
> - *Security Alert: Explains the exact SQL injection vector and warns of the hardcoded secret.*
> - *Performance Alert: Warns of missing table indexing.*
> - *Drop-In Fix: Supplies parameterized SQLAlchemy code ready to copy-paste.*
> *The entire team now has shared context instantly."*

### Step 4: Show Code Snippet Capability (15s)
> *"You don't even need a published PR. Any developer can paste a raw snippet or Git diff directly in chat to get immediate feedback before even opening a PR."*

---

## 🌟 5. What Makes This Submission Stand Out
1. **Zero Disruption / Multi-Protocol Support**: Seamlessly supports Switch AI Gateway payloads, standard Telegram Webhook Updates, and direct REST testing (`/review`).
2. **Dual AI Engine**: Primary integration with `google-genai` SDK, with an automatic, zero-dependency async REST fallback so the agent never drops a review.
3. **Telegram-Tuned UX**: Safe Markdown rendering, automatic paragraph chunking under Telegram's 4,096 character limit, and fallback plain-text recovery.
4. **Production-Ready**: Healthchecks, Docker Compose orchestration, and unit test suite included out-of-the-box.

