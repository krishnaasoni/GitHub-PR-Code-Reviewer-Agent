# 🌐 Live Telegram Webhook & Tunneling Guide

To connect your local FastAPI Reviewer Agent to Telegram in real-time for live hackathon demos, your local server must be reachable via a public HTTPS URL.

Here are the 2 fastest ways to do it:

---

## Option 1: Using `ngrok` (Recommended - 30 seconds)

### Step 1: Start your FastAPI Reviewer
In Terminal 1:
```bash
python main.py
```
*(Server runs at http://localhost:8000)*

### Step 2: Open an HTTPS Tunnel
In Terminal 2:
```bash
ngrok http 8000
```
`ngrok` will provide an HTTPS forwarding URL, for example:
`https://a1b2-34-56-78-90.ngrok-free.app`

### Step 3: Register the Webhook with Telegram
Run this single curl command (replace `<YOUR_BOT_TOKEN>` and the ngrok URL):
```bash
curl -F "url=https://a1b2-34-56-78-90.ngrok-free.app/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

Telegram will reply:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

### Step 4: Test in Telegram!
Open your bot in Telegram and send:
- `https://github.com/fastapi/fastapi/pull/12`
- Or `/help`

---

## Option 2: Using Cloudflare Tunnels (`cloudflared`) - Free & No Account Needed

### Step 1: Start your FastAPI Reviewer
```bash
python main.py
```

### Step 2: Run Cloudflare Quick Tunnel
```bash
cloudflared tunnel --url http://localhost:8000
```
Cloudflare will give you a temporary `.trycloudflare.com` URL (e.g., `https://random-words.trycloudflare.com`).

### Step 3: Register with Telegram
```bash
curl -F "url=https://random-words.trycloudflare.com/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

---

## How to Check Webhook Status & Reset
To check if Telegram is successfully delivering messages to your webhook:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

To delete the webhook (e.g. to switch back to polling mode in Switch Gateway):
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
```

