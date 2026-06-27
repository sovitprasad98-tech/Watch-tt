import os
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ── Config ──────────────────────────────────────────
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "8441549455:AAFbMkAixu4L0joOElC8pTWESTyXVDsHCA4")
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://ads-sovitx.vercel.app")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Helper ───────────────────────────────────────────
def tg(method, data):
    r = requests.post(f"{TELEGRAM_API}/{method}", json=data, timeout=10)
    return r.json()

# ── /start ───────────────────────────────────────────
def handle_start(chat_id, user):
    first_name = user.get("first_name", "User")
    user_id    = user.get("id", "")

    tg("sendMessage", {
        "chat_id": chat_id,
        "text": (
            f"👋 Hey {first_name}!\n\n"
            f"🎬 *Watch & Earn Premium*\n\n"
            f"Watch videos and earn real money!\n\n"
            f"💰 Earn ₹1 per video\n"
            f"🎁 Daily bonus rewards\n"
            f"👥 Invite friends — earn ₹3 each\n"
            f"💳 Withdraw to UPI at ₹100\n\n"
            f"👇 Tap the button below to start!"
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "🚀 Open Watch & Earn",
                    "web_app": {
                        "url": f"{MINI_APP_URL}?ref={user_id}"
                    }
                }
            ]]
        }
    })

# ── /help ────────────────────────────────────────────
def handle_help(chat_id):
    tg("sendMessage", {
        "chat_id": chat_id,
        "text": (
            "📖 *How it works:*\n\n"
            "1️⃣ Tap *Open Watch & Earn*\n"
            "2️⃣ Watch short videos — earn ₹1 each\n"
            "3️⃣ Invite friends — earn ₹3 per referral\n"
            "4️⃣ Collect ₹100 and withdraw to UPI\n\n"
            "🔗 /start — Open the app\n"
            "❓ /help — This message"
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "🚀 Open App",
                    "web_app": {"url": MINI_APP_URL}
                }
            ]]
        }
    })

# ── Webhook ──────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data    = request.get_json(force=True)
        message = data.get("message", {})

        if not message:
            return jsonify({"ok": True})

        chat_id = message.get("chat", {}).get("id")
        text    = message.get("text", "")
        user    = message.get("from", {})

        if text.startswith("/start"):
            handle_start(chat_id, user)
        elif text.startswith("/help"):
            handle_help(chat_id)
        else:
            tg("sendMessage", {
                "chat_id": chat_id,
                "text": "👇 Tap below to open Watch & Earn!",
                "reply_markup": {
                    "inline_keyboard": [[
                        {
                            "text": "🚀 Open App",
                            "web_app": {
                                "url": f"{MINI_APP_URL}?ref={user.get('id','')}"
                            }
                        }
                    ]]
                }
            })

    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"ok": True})

# ── Health check ─────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "bot": "@ads_sovitx_bot",
        "mini_app": MINI_APP_URL
    })

# ── Set Webhook (call once after deploy) ─────────────
@app.route("/set-webhook", methods=["GET"])
def set_webhook():
    host = request.host
    webhook_url = f"https://{host}/webhook"
    r = tg("setWebhook", {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"]
    })
    return jsonify(r)

if __name__ == "__main__":
    app.run(debug=False)
  
