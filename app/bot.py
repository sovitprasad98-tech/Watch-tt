import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN    = os.environ.get("BOT_TOKEN",    "8939556158:AAF7weTKI0LTDBXc8nnsxEf8sgbxc4VPK0c")
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://dropify-exe.vercel.app/u/watch")
FB_DB_URL    = os.environ.get("FB_DB_URL",    "https://watch-1784a-default-rtdb.firebaseio.com")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Firebase REST ─────────────────────────────────
def fb_get(path):
    r = requests.get(f"{FB_DB_URL}/{path}.json", timeout=10)
    return r.json()

def fb_set(path, data):
    return requests.put(f"{FB_DB_URL}/{path}.json", json=data, timeout=10).json()

def fb_patch(path, data):
    return requests.patch(f"{FB_DB_URL}/{path}.json", json=data, timeout=10).json()

# ── Telegram API ──────────────────────────────────
def tg(method, data):
    r = requests.post(f"{TELEGRAM_API}/{method}", json=data, timeout=10)
    return r.json()

# ── Webapp URL (no params — TG passes user data via initData) ──
def webapp_url():
    return MINI_APP_URL

# ── /start ────────────────────────────────────────
def handle_start(chat_id, user, ref_code=None):
    tg_id  = str(user.get("id", ""))
    fname  = user.get("first_name", "User")
    uid    = f"TG_{tg_id}"
    import time

    is_new = False
    existing = fb_get(f"users/{uid}")

    if not existing or not isinstance(existing, dict):
        # Create user
        lname    = user.get("last_name", "")
        fullname = (fname + (" " + lname if lname else "")).strip()
        photo    = user.get("photo_url", "")

        fb_set(f"users/{uid}", {
            "uid":               uid,
            "username":          fullname,
            "photoUrl":          photo,
            "balance":           0,
            "totalWithdrawn":    0,
            "lastDailyClaim":    0,
            "dailyStreak":       0,
            "invites":           0,
            "adProgress":        0,
            "lastBalanceUpdate": int(time.time() * 1000),
            "role":              "user",
            "createdAt":         int(time.time() * 1000),
            "referredBy":        None
        })
        is_new = True

        # Credit referrer using 8-digit code
        if ref_code and len(ref_code) == 8 and ref_code.isdigit():
            code_data = fb_get(f"refCodes/{ref_code}")
            if code_data and isinstance(code_data, dict):
                referrer_uid = code_data.get("uid")
                if referrer_uid and referrer_uid != uid:
                    rd = fb_get(f"users/{referrer_uid}")
                    if rd and isinstance(rd, dict):
                        fb_patch(f"users/{referrer_uid}", {
                            "balance":           float(rd.get("balance", 0)) + 3,
                            "invites":           int(rd.get("invites", 0)) + 1,
                            "lastBalanceUpdate": int(time.time() * 1000)
                        })
                        fb_patch(f"users/{uid}", {"referredBy": referrer_uid})

    # Welcome message
    if is_new:
        intro = f"🎉 *Welcome {fname}!*\n"
    else:
        intro = f"👋 *Hey {fname}, welcome back!*\n"

    tg("sendMessage", {
        "chat_id":    chat_id,
        "parse_mode": "Markdown",
        "text": (
            f"{intro}"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Earn *₹1* per video watched\n"
            f"🎁 Daily bonus — up to *₹15/day*\n"
            f"👥 Invite friends — earn *₹3* each\n"
            f"💳 Withdraw to UPI at *₹100*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👇 Tap *Play* to start earning!"
        ),
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Play", "web_app": {"url": webapp_url()}}],
                [{"text": "🔗 My Referral Link", "callback_data": f"ref_{tg_id}"},
                 {"text": "❓ Help",             "callback_data": "help"}]
            ]
        }
    })

# ── /refer & callback ─────────────────────────────
def send_referral(chat_id, tg_id):
    uid       = f"TG_{tg_id}"
    user_data = fb_get(f"users/{uid}")
    ref_code  = user_data.get("refCode") if isinstance(user_data, dict) else None
    invites   = user_data.get("invites", 0) if isinstance(user_data, dict) else 0

    if not ref_code:
        tg("sendMessage", {"chat_id": chat_id, "text": "⚠️ Please open the app first to generate your referral code."})
        return

    ref_link = f"https://t.me/WatchEarnByEp_Bot?start={ref_code}"
    tg("sendMessage", {
        "chat_id":    chat_id,
        "parse_mode": "Markdown",
        "text": (
            f"🔗 *Your Referral Link:*\n\n"
            f"`{ref_link}`\n\n"
            f"🎯 *Your Code:* `{ref_code}`\n\n"
            f"💰 Earn *₹3* for every friend who joins!\n"
            f"👥 Total Invites: *{invites}*  •  Earned: *₹{invites * 3}*"
        ),
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📤 Share", "switch_inline_query":
                  f"🎬 Watch & Earn — earn real money!\n💰 Get ₹3 signup bonus!\n👉 {ref_link}"}],
                [{"text": "▶️ Open App", "web_app": {"url": webapp_url()}}]
            ]
        }
    })

# ── Webhook ───────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

        if data.get("callback_query"):
            cb   = data["callback_query"]
            cid  = cb["message"]["chat"]["id"]
            cbd  = cb.get("data", "")
            user = cb.get("from", {})
            tg_id = str(user.get("id", ""))

            if cbd.startswith("ref_"):
                send_referral(cid, cbd.replace("ref_", ""))
            elif cbd == "help":
                tg("sendMessage", {
                    "chat_id": cid,
                    "parse_mode": "Markdown",
                    "text": (
                        "📖 *Commands:*\n\n"
                        "/start — Open the app\n"
                        "/refer — Get referral link\n\n"
                        "💡 Open app via *Play* button only."
                    )
                })
            tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
            return jsonify({"ok": True})

        message = data.get("message", {})
        if not message:
            return jsonify({"ok": True})

        chat_id = message["chat"]["id"]
        text    = message.get("text", "")
        user    = message.get("from", {})

        if text.startswith("/start"):
            parts    = text.split(" ", 1)
            ref_code = parts[1].strip() if len(parts) > 1 else None
            handle_start(chat_id, user, ref_code)
        elif text.startswith("/refer"):
            send_referral(chat_id, str(user.get("id", "")))
        else:
            tg("sendMessage", {
                "chat_id": chat_id,
                "text":    "👇 Tap Play to open Watch & Earn!",
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "▶️ Play", "web_app": {"url": webapp_url()}}
                    ]]
                }
            })

    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running", "bot": "@WatchEarnByEp_Bot"})

@app.route("/set-webhook", methods=["GET"])
def set_webhook():
    url = f"https://{request.host}/webhook"
    return jsonify(tg("setWebhook", {"url": url, "allowed_updates": ["message", "callback_query"]}))

if __name__ == "__main__":
    app.run(debug=False)
