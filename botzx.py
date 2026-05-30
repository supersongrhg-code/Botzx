#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BOT - REFERRAL & REWARD SYSTEM - VERSION 5.2
PRODUCTION READY • ADVANCED FRAUD DETECTION
IP + DEVICE FINGERPRINTING • PERSONAL CHAT ONLY
ENHANCED ADMIN FEATURES - FULLY WORKING
"""

import json
import os
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request
import requests
from dotenv import load_dotenv
import traceback

load_dotenv()

# ════════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN", "8812550634:AAFbL1HTz7l0IilKkD7zEADM6EsS1HFFDto")
OWNER_ID = int(os.getenv("OWNER_ID", "6362587740"))
WEB_URL = os.getenv("WEB_URL", "http://secretlifafa.xyz/verify.html")
STORAGE_FILE = "bot_data.json"
PORT = int(os.getenv("PORT", "5000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-webhook-url.com/webhook")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ════════════════════════════════════════════════════════════════════════════
# 💾 STORAGE FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════


def init_storage():
    """Initialize JSON storage if not exists"""
    if not os.path.exists(STORAGE_FILE):
        data = {
            "users": {},
            "codes": [],
            "channels": ["@legend99loots", "@Prime_Campaign"],
            "co_admins": [],
            "admin_state": {},
            "fraud_log": [],
            "ip_blacklist": [],
            "device_blacklist": [],
            "user_warnings": {},
            "ban_reasons": {},
            "referral_history": [],
            "refer_limit": 5,
            "points_per_refer": 1,
            "milestone_bonus": True,
            "bot_paused": False,
            "pause_message": "⏸️ Bot under maintenance. Back soon!",
            "welcome_msg": "🎉 *Welcome to Earn Bot!*\n\n💵 Earn by referring friends\n🎁 Redeem exclusive gift codes\n\n*Let's Start Earning!*",
            "milestones": {"5": 2, "10": 5, "25": 10, "50": 25},
            "same_device_auto_ban": True,
            "max_accounts_per_ip": 3,
            "fraud_detection_level": "strict",
            "min_referral_for_redeem": 1,
            "code_validity": 30,
            "admin_logs": [],
        }
        save_data(data)
        logger.info("✅ Storage initialized")
    return load_data()


def load_data():
    """Load data from JSON file"""
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return init_storage()


def save_data(data):
    """Save data to JSON file"""
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving data: {e}")


def get_client_ip():
    """Get client IP from request"""
    try:
        if request.headers.get("CF-Connecting-IP"):
            return request.headers.get("CF-Connecting-IP")
        if request.headers.get("X-Forwarded-For"):
            return request.headers.get("X-Forwarded-For").split(",")[0].strip()
        return request.remote_addr or "0.0.0.0"
    except:
        return "0.0.0.0"


def get_device_fingerprint(user_agent="", accept_lang="", ip=""):
    """Generate device fingerprint hash"""
    try:
        ua = user_agent or request.headers.get("User-Agent", "unknown")
        lang = accept_lang or request.headers.get("Accept-Language", "unknown")
        ip = ip or get_client_ip()
        fingerprint_str = f"{ua}|{lang}|{ip}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    except:
        return hashlib.sha256(b"unknown").hexdigest()


# ════════════════════════════════════════════════════════════════════════════
# 🤖 TELEGRAM API
# ════════════════════════════════════════════════════════════════════════════


def tg_api(method, params=None):
    """Make Telegram API request"""
    if params is None:
        params = {}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, data=params, timeout=15)
        result = response.json()
        if not result.get("ok"):
            logger.warning(f"TG API Error in {method}: {result.get('description', 'Unknown error')}")
        return result
    except Exception as e:
        logger.error(f"TG API Exception in {method}: {e}")
        return {"ok": False, "error": str(e)}


def send_msg(chat_id, text, keyboard=None, parse="Markdown"):
    """Send message"""
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse,
        "disable_web_page_preview": "true",
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard)
    return tg_api("sendMessage", params)


def edit_msg(chat_id, msg_id, text, keyboard=None):
    """Edit message"""
    params = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard)
    return tg_api("editMessageText", params)


def answer_callback(cb_id, text="", alert=False):
    """Answer callback query"""
    return tg_api(
        "answerCallbackQuery",
        {
            "callback_query_id": cb_id,
            "text": text,
            "show_alert": "true" if alert else "false",
        },
    )


def delete_msg(chat_id, msg_id):
    """Delete message"""
    return tg_api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})


# ════════════════════════════════════════════════════════════════════════════
# ✅ HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════


def check_channels(user_id, channels, data):
    """Check if user is member of all channels"""
    try:
        for ch in channels:
            try:
                result = tg_api("getChatMember", {"chat_id": ch, "user_id": user_id})
                status = result.get("result", {}).get("status", "left")
                if status not in ["member", "administrator", "creator"]:
                    return False
            except:
                return False
        return True
    except:
        return False


def is_admin(user_id, data):
    """Check if user is admin"""
    return user_id == OWNER_ID or user_id in data.get("co_admins", [])


def is_owner(user_id):
    """Check if user is owner"""
    return user_id == OWNER_ID


def is_personal_chat(chat_id):
    """Check if chat is personal (not group/channel)"""
    return chat_id > 0


def progress_bar(current, max_val, length=10):
    """Generate progress bar"""
    if max_val <= 0:
        return "░" * length
    filled = min(length, int((current / max_val) * length))
    return "█" * filled + "░" * (length - filled)


def num(n):
    """Format number with commas"""
    return f"{n:,}"


def clean_username(username):
    """Clean username"""
    return username.lstrip("@") if username else "unknown"


def log_fraud(user_id, reason, data):
    """Log fraud attempt"""
    data["fraud_log"].append(
        {
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": get_client_ip(),
            "device_hash": get_device_fingerprint(),
        }
    )
    return data


def log_admin_action(admin_id, action, target_id, data):
    """Log admin action"""
    data["admin_logs"].append(
        {
            "admin_id": admin_id,
            "action": action,
            "target_id": target_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    # Keep only last 1000 logs
    if len(data["admin_logs"]) > 1000:
        data["admin_logs"] = data["admin_logs"][-1000:]
    return data


# ════════════════════════════════════════════════════════════════════════════
# ⌨️ KEYBOARDS
# ════════════════════════════════════════════════════════════════════════════


def user_keyboard():
    """User menu keyboard"""
    return {
        "keyboard": [
            [{"text": "🔗 Share Link"}, {"text": "💰 My Balance"}],
            [{"text": "🎁 Redeem Code"}, {"text": "📊 My Stats"}],
            [{"text": "🏆 Leaderboard"}, {"text": "📋 History"}],
            [{"text": "ℹ️ Help"}, {"text": "⚙️ Settings"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def admin_keyboard():
    """Admin menu keyboard"""
    return {
        "keyboard": [
            [{"text": "➕ Add Code"}, {"text": "📦 Bulk Codes"}],
            [{"text": "📋 Code List"}, {"text": "🗑️ Clear Used"}],
            [{"text": "━━━━━━━━━━"}],
            [{"text": "🔍 Search User"}, {"text": "👁️ User Info"}],
            [{"text": "💎 Give Points"}, {"text": "💸 Take Points"}],
            [{"text": "🔨 Ban User"}, {"text": "✅ Unban User"}],
            [{"text": "⚠️ Warn User"}, {"text": "📩 Message"}],
            [{"text": "🔄 Reset User"}, {"text": "📋 Warnings"}],
            [{"text": "━━━━━━━━━━"}],
            [{"text": "📢 Broadcast"}, {"text": "👥 All Users"}],
            [{"text": "🛡️ Fraud Log"}, {"text": "⚠️ Device Blocks"}],
            [{"text": "📱 IP Manager"}, {"text": "🔐 Security"}],
            [{"text": "━━━━━━━━━━"}],
            [{"text": "📊 Dashboard"}, {"text": "📈 Analytics"}],
            [{"text": "⚙️ Set Ref Limit"}, {"text": "💡 Points/Ref"}],
            [{"text": "🏅 Milestones"}, {"text": "📡 Channels"}],
            [{"text": "👮 Manage Admins"}, {"text": "✏️ Edit Welcome"}],
            [{"text": "📤 Export CSV"}, {"text": "🗂️ Admin Logs"}],
            [{"text": "⏸️ Pause"}, {"text": "▶️ Resume"}],
            [{"text": "🏠 User Mode"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


# ════════════════════════════════════════════════════════════════════════════
# 🔐 DEVICE VERIFICATION ROUTES
# ════════════════════════════════════════════════════════════════════════════


@app.route("/verify", methods=["GET"])
def verify_device():
    """Device verification endpoint"""
    try:
        uid = request.args.get("uid", type=int, default=0)
        if uid <= 0:
            return "❌ Invalid UID", 400

        device_hash = get_device_fingerprint()
        client_ip = get_client_ip()
        data = load_data()

        if str(uid) not in data["users"]:
            return "❌ User not registered", 400

        user = data["users"][str(uid)]
        is_verified = user.get("verified", 0) == 1
        referrer_id = user.get("referred_by")
        fraud = False
        fraud_reason = ""

        if client_ip in data.get("ip_blacklist", []):
            fraud = True
            fraud_reason = "IP blacklisted"

        if device_hash in data.get("device_blacklist", []):
            fraud = True
            fraud_reason = "Device blacklisted"

        if not is_verified and not fraud:
            data["users"][str(uid)]["device_hash"] = device_hash
            data["users"][str(uid)]["ip_address"] = client_ip
            data["users"][str(uid)]["verified"] = 1
            data["users"][str(uid)]["verified_at"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            same_device_count = 0
            same_ip_count = 0

            for check_id, check_user in data["users"].items():
                if check_id != str(uid):
                    if check_user.get("device_hash") == device_hash:
                        same_device_count += 1
                    if check_user.get("ip_address") == client_ip:
                        same_ip_count += 1

            fraud_detection = data.get("fraud_detection_level", "strict")
            is_fraud = False

            if fraud_detection == "strict":
                if same_device_count > 0:
                    is_fraud = True
                if same_ip_count >= data.get("max_accounts_per_ip", 3):
                    is_fraud = True
            elif fraud_detection == "moderate":
                if same_device_count > 1:
                    is_fraud = True
                if same_ip_count > data.get("max_accounts_per_ip", 3):
                    is_fraud = True

            if is_fraud:
                fraud = True
                fraud_reason = f"Same device/IP detected ({same_device_count} devices, {same_ip_count} IPs)"
                data = log_fraud(uid, fraud_reason, data)

                if data.get("same_device_auto_ban", False):
                    data["users"][str(uid)]["status"] = "banned"
                    data["users"][str(uid)]["ban_reason"] = f"Auto-banned: {fraud_reason}"
                    send_msg(
                        OWNER_ID,
                        f"🚨 *AUTO-BAN: FRAUD DETECTED*\n\n👤 @{user.get('username')} (ID: `{uid}`)\n⚠️ Reason: {fraud_reason}\n📱 Device: `{device_hash[:16]}...`\n🌐 IP: `{client_ip}`",
                    )
                else:
                    send_msg(
                        OWNER_ID,
                        f"⚠️ *FRAUD ALERT*\n\n👤 @{user.get('username')} (ID: `{uid}`)\n🔍 Reason: {fraud_reason}",
                    )
            else:
                if referrer_id and str(referrer_id) in data["users"]:
                    ppr = data.get("points_per_refer", 1)
                    data["users"][str(referrer_id)]["referrals"] = (
                        data["users"][str(referrer_id)].get("referrals", 0) + 1
                    )
                    data["users"][str(referrer_id)]["balance"] = (
                        data["users"][str(referrer_id)].get("balance", 0) + ppr
                    )
                    data["users"][str(referrer_id)]["total_earned"] = (
                        data["users"][str(referrer_id)].get("total_earned", 0) + ppr
                    )

                    data["referral_history"].append(
                        {
                            "referrer_id": referrer_id,
                            "user_id": uid,
                            "username": user.get("username"),
                            "points": ppr,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )

                    new_count = data["users"][str(referrer_id)]["referrals"]
                    milestones = data.get("milestones", {})
                    user_ms = data["users"][str(referrer_id)].get("milestones_reached", [])

                    for ms, bonus in milestones.items():
                        ms_int = int(ms)
                        if new_count >= ms_int and ms_int not in user_ms:
                            data["users"][str(referrer_id)]["balance"] += bonus
                            data["users"][str(referrer_id)]["total_earned"] += bonus
                            data["users"][str(referrer_id)]["milestones_reached"].append(
                                ms_int
                            )

                            bal = data["users"][str(referrer_id)]["balance"]
                            send_msg(
                                referrer_id,
                                f"🏆 *MILESTONE UNLOCKED!*\n\n✨ You reached *{ms} referrals*!\n💎 Bonus: *+{bonus} points*\n💰 New Balance: *₹{num(bal)}*",
                            )

                    bal = data["users"][str(referrer_id)]["balance"]
                    refs = data["users"][str(referrer_id)]["referrals"]
                    send_msg(
                        referrer_id,
                        f"🎉 *NEW REFERRAL!*\n\n👤 @{user.get('username')} verified!\n💵 You earned *+{ppr} points*\n💰 Balance: *₹{num(bal)}*\n🔗 Total: *{refs}* referrals",
                    )

            save_data(data)

            if not fraud:
                send_msg(
                    uid,
                    "✅ *DEVICE VERIFIED!*\n\nYour account is active. Return to bot! 🚀",
                )

        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Verification</title></head>
        <body style="text-align:center; padding:50px; font-family:Arial;">
            <h1>{'Access Denied ❌' if fraud else 'Verified ✅'}</h1>
            <p>{'Fraud detected' if fraud else 'Device verified successfully!'}</p>
            <script>
                setTimeout(() => {{
                    if (window.Telegram && Telegram.WebApp) {{
                        Telegram.WebApp.close();
                    }}
                }}, 2000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Verify endpoint error: {e}\n{traceback.format_exc()}")
        return f"Error: {str(e)}", 500


# ════════════════════════════════════════════════════════════════════════════
# 🎯 WEBHOOK HANDLER
# ════════════════════════════════════════════════════════════════════════════


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming messages and callbacks"""
    try:
        update = request.get_json()
        if not update:
            return "ok"

        data = load_data()

        # Handle callback queries
        if "callback_query" in update:
            handle_callback(update["callback_query"], data)
            return "ok"

        # Handle messages
        if "message" not in update:
            return "ok"

        handle_message(update["message"], data)
        return "ok"
    except Exception as e:
        logger.error(f"Webhook error: {e}\n{traceback.format_exc()}")
        return "ok"


def handle_callback(cb, data):
    """Handle callback queries"""
    try:
        cb_id = cb["id"]
        cb_data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]
        user_id = cb["from"]["id"]
        msg_id = cb["message"]["message_id"]

        if not is_personal_chat(chat_id):
            answer_callback(cb_id, "❌ This bot only works in personal messages!", True)
            return

        answer_callback(cb_id)

        if cb_data == "channels_ok":
            if check_channels(user_id, data["channels"], data):
                if data["users"].get(str(user_id), {}).get("verified", 0) == 0:
                    verify_link = f"{WEB_URL}?uid={user_id}"
                    edit_msg(
                        chat_id,
                        msg_id,
                        "✅ *Channel Verification Complete!*\n\n🔐 Now verify your device:\n",
                        {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "🛡️ Verify Device",
                                        "web_app": {"url": verify_link},
                                    }
                                ]
                            ]
                        },
                    )
                else:
                    delete_msg(chat_id, msg_id)
                    send_msg(chat_id, data["welcome_msg"], user_keyboard())
            else:
                answer_callback(cb_id, "❌ Join all channels first!", True)

        elif cb_data == "confirm_broadcast" and is_admin(user_id, data):
            bc_text = data["admin_state"].get(str(user_id), {}).get("broadcast_text", "")
            success, failed = 0, 0

            for uid, u in data["users"].items():
                if u.get("status") == "banned":
                    continue
                r = send_msg(int(uid), bc_text)
                if r.get("ok"):
                    success += 1
                else:
                    failed += 1

            data["admin_state"].pop(str(user_id), None)
            save_data(data)
            edit_msg(
                chat_id,
                msg_id,
                f"📢 *BROADCAST COMPLETE!*\n\n✅ Sent: `{success}`\n❌ Failed: `{failed}`",
            )

        elif cb_data == "cancel_broadcast" and is_admin(user_id, data):
            data["admin_state"].pop(str(user_id), None)
            save_data(data)
            edit_msg(chat_id, msg_id, "❌ Broadcast cancelled.")
    except Exception as e:
        logger.error(f"Callback error: {e}\n{traceback.format_exc()}")


def handle_message(msg, data):
    """Handle text messages"""
    try:
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "").strip()
        username = msg["from"].get("username", f"user_{user_id}")
        first_name = msg["from"].get("first_name", "User")

        # Only personal chats
        if not is_personal_chat(chat_id):
            me = tg_api("getMe")
            bot_username = me.get("result", {}).get("username", "bot")
            send_msg(
                chat_id,
                f"❌ This bot only works in personal messages!\n\nMessage me directly: @{bot_username}",
            )
            return

        # Auto-register user
        if str(user_id) not in data["users"]:
            data["users"][str(user_id)] = {
                "username": username,
                "first_name": first_name,
                "referred_by": None,
                "referrals": 0,
                "balance": 0,
                "total_earned": 0,
                "claimed": 0,
                "claim_history": [],
                "device_hash": "",
                "ip_address": "",
                "verified": 0,
                "status": "active",
                "mode": "user",
                "joined_date": datetime.now().strftime("%d %b %Y"),
                "milestones_reached": [],
                "warnings": 0,
                "last_warning": None,
            }
            save_data(data)

        user = data["users"][str(user_id)]

        # Update username
        if user["username"] != username:
            data["users"][str(user_id)]["username"] = username
            data["users"][str(user_id)]["first_name"] = first_name
            save_data(data)

        # Check if banned
        if user.get("status") == "banned":
            send_msg(
                chat_id,
                f"🛑 *Account Suspended*\n\nYour account has been banned.\n\n❌ Reason: {user.get('ban_reason', 'Policy violation')}",
            )
            return

        # Check if bot paused
        if data.get("bot_paused", False) and not is_admin(user_id, data):
            send_msg(chat_id, data.get("pause_message", "⏸️ Bot under maintenance."))
            return

        # Admin state handler
        admin_state = data["admin_state"].get(str(user_id), {})
        if admin_state and is_admin(user_id, data):
            handle_admin_state(user_id, chat_id, text, admin_state, data)
            return

        # Commands
        if text.startswith("/start"):
            handle_start(user_id, chat_id, text, data)
            return

        if text == "/admin":
            if not is_admin(user_id, data):
                send_msg(chat_id, "⛔ Access denied.")
                return
            data["users"][str(user_id)]["mode"] = "admin"
            save_data(data)
            send_msg(chat_id, "🔐 *ADMIN PANEL*", admin_keyboard())
            return

        # Admin menu
        mode = user.get("mode", "user")
        if mode == "admin" and is_admin(user_id, data):
            if handle_admin_menu(user_id, chat_id, text, data):
                return

        # User menu
        if handle_user_menu(user_id, chat_id, text, data):
            return

        # Fallback
        send_msg(chat_id, "Use menu below 👇", user_keyboard())
    except Exception as e:
        logger.error(f"Message handler error: {e}\n{traceback.format_exc()}")


def handle_start(user_id, chat_id, text, data):
    """Handle /start command"""
    try:
        param = text.replace("/start", "").strip()

        if param and param.isdigit() and int(param) != user_id:
            if (
                data["users"][str(user_id)].get("referred_by") is None
                and data["users"][str(user_id)].get("verified") == 0
            ):
                data["users"][str(user_id)]["referred_by"] = int(param)
                save_data(data)

        if not check_channels(user_id, data["channels"], data):
            buttons = []
            for i, ch in enumerate(data["channels"]):
                clean = clean_username(ch)
                buttons.append(
                    [{"text": f"📢 Join #{i + 1}", "url": f"https://t.me/{clean}"}]
                )
            buttons.append([{"text": "✅ Joined", "callback_data": "channels_ok"}])
            send_msg(
                chat_id,
                "🔒 *JOIN CHANNELS*\n\nPlease join:\n",
                {"inline_keyboard": buttons},
            )
            return

        if data["users"][str(user_id)].get("verified") == 0:
            verify_link = f"{WEB_URL}?uid={user_id}"
            send_msg(
                chat_id,
                "🛡️ *VERIFY DEVICE*\n\nSecure now:\n",
                {
                    "inline_keyboard": [
                        [{"text": "🛡️ Verify", "web_app": {"url": verify_link}}]
                    ]
                },
            )
            return

        if data["users"][str(user_id)].get("mode") == "admin" and is_admin(user_id, data):
            send_msg(chat_id, "🔐 *ADMIN PANEL*\n\nWelcome back!", admin_keyboard())
        else:
            send_msg(chat_id, data.get("welcome_msg", "Welcome!"), user_keyboard())
    except Exception as e:
        logger.error(f"Start handler error: {e}\n{traceback.format_exc()}")


def handle_admin_menu(user_id, chat_id, text, data):
    """Handle admin menu items"""
    try:
        if text == "➕ Add Code":
            data["admin_state"][str(user_id)] = {"step": "add_code"}
            save_data(data)
            send_msg(chat_id, "📝 Send code:")
            return True

        if text == "📦 Bulk Codes":
            data["admin_state"][str(user_id)] = {"step": "bulk_codes"}
            save_data(data)
            send_msg(chat_id, "📝 Send codes (one per line):")
            return True

        if text == "📋 Code List":
            avail = [c for c in data["codes"] if c["status"] == "available"]
            used = [c for c in data["codes"] if c["status"] == "claimed"]
            msg = f"📋 *CODE VAULT*\n\n✅ Available: `{len(avail)}`\n🔓 Used: `{len(used)}`\n📦 Total: `{len(data['codes'])}`\n\n"
            if avail:
                msg += "📝 *Next 5*:\n"
                for c in avail[:5]:
                    msg += f"• `{c['text'][:20]}...`\n"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "🗑️ Clear Used":
            before = len(data["codes"])
            data["codes"] = [c for c in data["codes"] if c["status"] == "available"]
            after = len(data["codes"])
            save_data(data)
            send_msg(
                chat_id, f"🗑️ *CLEARED!*\n\nRemoved: `{before - after}`", admin_keyboard()
            )
            return True

        if text == "🔍 Search User":
            data["admin_state"][str(user_id)] = {"step": "search_user"}
            save_data(data)
            send_msg(chat_id, "🔍 Enter username or ID:")
            return True

        if text == "👁️ User Info":
            data["admin_state"][str(user_id)] = {"step": "user_info"}
            save_data(data)
            send_msg(chat_id, "👁️ Enter user ID:")
            return True

        if text == "💎 Give Points":
            data["admin_state"][str(user_id)] = {"step": "give_points_id"}
            save_data(data)
            send_msg(chat_id, "💎 Enter user ID:")
            return True

        if text == "💸 Take Points":
            data["admin_state"][str(user_id)] = {"step": "take_points_id"}
            save_data(data)
            send_msg(chat_id, "💸 Enter user ID:")
            return True

        if text == "🔨 Ban User":
            data["admin_state"][str(user_id)] = {"step": "ban_user"}
            save_data(data)
            send_msg(chat_id, "🔨 Enter user ID:")
            return True

        if text == "✅ Unban User":
            data["admin_state"][str(user_id)] = {"step": "unban_user"}
            save_data(data)
            send_msg(chat_id, "✅ Enter user ID:")
            return True

        if text == "⚠️ Warn User":
            data["admin_state"][str(user_id)] = {"step": "warn_user"}
            save_data(data)
            send_msg(chat_id, "⚠️ Enter user ID:")
            return True

        if text == "📩 Message":
            data["admin_state"][str(user_id)] = {"step": "msg_user_id"}
            save_data(data)
            send_msg(chat_id, "📩 Enter user ID:")
            return True

        if text == "🔄 Reset User":
            data["admin_state"][str(user_id)] = {"step": "reset_user"}
            save_data(data)
            send_msg(chat_id, "🔄 Enter user ID:")
            return True

        if text == "📋 Warnings":
            warned = {
                uid: u for uid, u in data["users"].items() if u.get("warnings", 0) > 0
            }
            if not warned:
                send_msg(chat_id, "📋 *WARNINGS*\n\nNo warnings.", admin_keyboard())
                return True
            msg = "📋 *WARNINGS*\n\n"
            sorted_warned = sorted(
                warned.items(), key=lambda x: x[1].get("warnings", 0), reverse=True
            )
            for uid, u in sorted_warned[:10]:
                msg += f"• @{u['username']} - `{u.get('warnings', 0)}/3`\n"
            if len(warned) > 10:
                msg += f"\n... and {len(warned) - 10} more"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "📢 Broadcast":
            data["admin_state"][str(user_id)] = {"step": "broadcast"}
            save_data(data)
            send_msg(chat_id, "📢 Write message:")
            return True

        if text == "👥 All Users":
            users = data["users"]
            total = len(users)
            verified = len([u for u in users.values() if u.get("verified") == 1])
            banned = len([u for u in users.values() if u.get("status") == "banned"])
            total_bal = sum(u.get("balance", 0) for u in users.values())
            total_ref = sum(u.get("referrals", 0) for u in users.values())
            msg = f"👥 *USER OVERVIEW*\n\n📊 Total: `{total}`\n✅ Verified: `{verified}`\n🔨 Banned: `{banned}`\n💰 Balance: `₹{num(total_bal)}`\n🔗 Refs: `{num(total_ref)}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "🛡️ Fraud Log":
            logs = data.get("fraud_log", [])
            if not logs:
                send_msg(chat_id, "📋 *FRAUD LOG*\n\nNo cases.", admin_keyboard())
                return True
            msg = "📋 *FRAUD LOG*\n\n"
            for log in reversed(logs[-5:]):
                msg += f"🚨 User: `{log['user_id']}`\n   Reason: {log['reason']}\n   Time: `{log['timestamp']}`\n\n"
            msg += f"📊 Total: `{len(logs)}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "⚠️ Device Blocks":
            blocked = data.get("device_blacklist", [])
            if not blocked:
                send_msg(chat_id, "📱 *DEVICE BLOCKS*\n\nNone.", admin_keyboard())
                return True
            msg = "📱 *BLOCKED DEVICES*\n\n"
            for device in blocked[:10]:
                msg += f"🚫 `{device[:16]}...`\n"
            if len(blocked) > 10:
                msg += f"\n... and {len(blocked) - 10} more"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "📱 IP Manager":
            blacklist = data.get("ip_blacklist", [])
            msg = f"📱 *IP MANAGEMENT*\n\n🚫 Blacklisted: `{len(blacklist)}`\n\n"
            for ip in blacklist[:10]:
                msg += f"• `{ip}`\n"
            if len(blacklist) > 10:
                msg += f"... and {len(blacklist) - 10} more\n"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "🔐 Security":
            msg = f"🔐 *SECURITY*\n\n🛡️ Detection: `{data.get('fraud_detection_level', 'strict')}`\n📱 Max/IP: `{data.get('max_accounts_per_ip', 3)}`\n⛔ Auto-Ban: {'✅' if data.get('same_device_auto_ban', True) else '❌'}\n\n📊 Fraud: `{len(data.get('fraud_log', []))}`\n🔗 IPs: `{len(data.get('ip_blacklist', []))}`\n📱 Devices: `{len(data.get('device_blacklist', []))}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "📊 Dashboard":
            users = data["users"]
            total = len(users)
            verified = len([u for u in users.values() if u.get("verified") == 1])
            total_bal = sum(u.get("balance", 0) for u in users.values())
            msg = f"📊 *DASHBOARD*\n\n👥 Users: `{total}` | Verified: `{verified}`\n💰 Balance: `₹{num(total_bal)}`\n📦 Codes: `{len(data.get('codes', []))}`\n🛡️ Fraud: `{len(data.get('fraud_log', []))}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "📈 Analytics":
            users = data["users"]
            total_refs = sum(u.get("referrals", 0) for u in users.values())
            total_earned = sum(u.get("total_earned", 0) for u in users.values())
            total_claimed = sum(u.get("claimed", 0) for u in users.values())
            msg = f"📈 *ANALYTICS*\n\n🔗 Total Refs: `{num(total_refs)}`\n💎 Earned: `₹{num(total_earned)}`\n🎁 Claimed: `{num(total_claimed)}`\n📊 Ref History: `{len(data.get('referral_history', []))}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "⚙️ Set Ref Limit":
            data["admin_state"][str(user_id)] = {"step": "set_refer_limit"}
            save_data(data)
            current = data.get("refer_limit", 5)
            send_msg(chat_id, f"Current: `{current}`\nNew value:")
            return True

        if text == "💡 Points/Ref":
            data["admin_state"][str(user_id)] = {"step": "set_ppr"}
            save_data(data)
            current = data.get("points_per_refer", 1)
            send_msg(chat_id, f"Current: `{current}`\nNew value:")
            return True

        if text == "🏅 Milestones":
            msg = "🏅 *MILESTONES*\n\n"
            for refs, bonus in data.get("milestones", {}).items():
                msg += f"• {refs} referrals → +{bonus} points\n"
            msg += (
                f"\n{'✅ Enabled' if data.get('milestone_bonus', True) else '❌ Disabled'}"
            )
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "📡 Channels":
            msg = "📡 *CHANNELS*\n\n"
            for i, ch in enumerate(data.get("channels", [])):
                msg += f"{i + 1}. `{ch}`\n"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "👮 Manage Admins":
            cos = data.get("co_admins", [])
            msg = "👮 *CO-ADMINS*\n\n"
            if not cos:
                msg += "None."
            else:
                for co_id in cos:
                    u = data["users"].get(str(co_id), {})
                    msg += f"• @{u.get('username')}\n"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "✏️ Edit Welcome":
            data["admin_state"][str(user_id)] = {"step": "edit_welcome"}
            save_data(data)
            send_msg(chat_id, "✏️ Send new message:")
            return True

        if text == "📤 Export CSV":
            csv = "ID,Username,Balance,Earned,Referrals,Claimed,Verified,Status,Warnings,Joined\n"
            for uid, u in data["users"].items():
                csv += f"{uid},{u['username']},{u.get('balance', 0)},{u.get('total_earned', 0)},{u.get('referrals', 0)},{u.get('claimed', 0)},{u.get('verified', 0)},{u.get('status', 'active')},{u.get('warnings', 0)},{u.get('joined_date', '')}\n"
            send_msg(chat_id, "📤 *EXPORT READY*", admin_keyboard())
            return True

        if text == "🗂️ Admin Logs":
            logs = data.get("admin_logs", [])
            if not logs:
                send_msg(chat_id, "🗂️ *ADMIN LOGS*\n\nNo logs.", admin_keyboard())
                return True
            msg = "🗂️ *ADMIN LOGS*\n\n"
            for log in reversed(logs[-5:]):
                msg += f"• {log['action']} by `{log['admin_id']}`\n  Time: `{log['timestamp']}`\n\n"
            msg += f"📊 Total: `{len(logs)}`"
            send_msg(chat_id, msg, admin_keyboard())
            return True

        if text == "⏸️ Pause":
            data["bot_paused"] = True
            save_data(data)
            send_msg(chat_id, "⏸️ *PAUSED*", admin_keyboard())
            return True

        if text == "▶️ Resume":
            data["bot_paused"] = False
            save_data(data)
            send_msg(chat_id, "▶️ *RESUMED*", admin_keyboard())
            return True

        if text == "🏠 User Mode":
            data["users"][str(user_id)]["mode"] = "user"
            save_data(data)
            send_msg(chat_id, "🏠 *USER MODE*", user_keyboard())
            return True

        return False
    except Exception as e:
        logger.error(f"Admin menu error: {e}\n{traceback.format_exc()}")
        return False


def handle_admin_state(user_id, chat_id, text, admin_state, data):
    """Handle admin state steps"""
    try:
        step = admin_state.get("step", "")

        if step == "add_code":
            data["codes"].append(
                {
                    "text": text,
                    "status": "available",
                    "added": datetime.now().strftime("%d %b %Y %H:%M"),
                }
            )
            data["admin_state"].pop(str(user_id), None)
            data = log_admin_action(user_id, "add_code", 0, data)
            save_data(data)
            avail_count = len([c for c in data["codes"] if c["status"] == "available"])
            send_msg(
                chat_id,
                f"✅ *Code Added!*\n\n`{text}`\n\n📊 Available: `{avail_count}`",
                admin_keyboard(),
            )
            return

        if step == "bulk_codes":
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                data["codes"].append(
                    {
                        "text": line,
                        "status": "available",
                        "added": datetime.now().strftime("%d %b %Y %H:%M"),
                    }
                )
            added = len(lines)
            data["admin_state"].pop(str(user_id), None)
            data = log_admin_action(user_id, "bulk_codes", added, data)
            save_data(data)
            avail_count = len([c for c in data["codes"] if c["status"] == "available"])
            send_msg(
                chat_id,
                f"✅ *Bulk Upload Done!*\n\n➕ Added: `{added}`\n📊 Available: `{avail_count}`",
                admin_keyboard(),
            )
            return

        if step == "broadcast":
            data["admin_state"][str(user_id)]["broadcast_text"] = text
            save_data(data)
            total = len(data["users"])
            send_msg(
                chat_id,
                f"📢 *BROADCAST PREVIEW*\n\n{text}\n\n─────────────\n\nSend to `{total}` users?",
                {
                    "inline_keyboard": [
                        [
                            {
                                "text": f"✅ Send ({total})",
                                "callback_data": "confirm_broadcast",
                            },
                            {"text": "❌ Cancel", "callback_data": "cancel_broadcast"},
                        ]
                    ]
                },
            )
            return

        if step == "ban_user":
            target_id = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            if target_id == OWNER_ID:
                send_msg(chat_id, "❌ Cannot ban owner.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["status"] = "banned"
            data["users"][str(target_id)]["banned_at"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            data = log_admin_action(user_id, "ban_user", target_id, data)
            save_data(data)
            target_user = data["users"][str(target_id)]
            send_msg(
                chat_id,
                f"🔨 *USER BANNED!*\n\n@{target_user['username']} (`{target_id}`)",
                admin_keyboard(),
            )
            return

        if step == "unban_user":
            target_id = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["status"] = "active"
            data = log_admin_action(user_id, "unban_user", target_id, data)
            save_data(data)
            target_user = data["users"][str(target_id)]
            send_msg(
                chat_id,
                f"✅ *USER UNBANNED!*\n\n@{target_user['username']}",
                admin_keyboard(),
            )
            return

        if step == "warn_user":
            target_id = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            if target_id == OWNER_ID:
                send_msg(chat_id, "❌ Cannot warn owner.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["warnings"] = (
                data["users"][str(target_id)].get("warnings", 0) + 1
            )
            data["users"][str(target_id)]["last_warning"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            if data["users"][str(target_id)]["warnings"] >= 3:
                data["users"][str(target_id)]["status"] = "banned"
                data["users"][str(target_id)]["ban_reason"] = (
                    "Auto-banned: 3 warnings reached"
                )
                msg_text = (
                    "⚠️ *FINAL WARNING!*\n\nYou've received 3 warnings and have been banned."
                )
            else:
                remaining = 3 - data["users"][str(target_id)]["warnings"]
                msg_text = f"⚠️ *WARNING!*\n\nYou have received a warning.\n\n⏳ Warnings: `{data['users'][str(target_id)]['warnings']}/3`\n\n⛔ Ban after 3 warnings!"

            data = log_admin_action(user_id, "warn_user", target_id, data)
            save_data(data)
            target_user = data["users"][str(target_id)]
            send_msg(
                chat_id,
                f"⚠️ *WARNING ISSUED!*\n\n@{target_user['username']}\nWarnings: `{target_user['warnings']}/3`",
                admin_keyboard(),
            )
            send_msg(target_id, msg_text)
            return

        if step == "give_points_id":
            target_id = int(text) if text.isdigit() else 0
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                data["admin_state"].pop(str(user_id), None)
                save_data(data)
                return
            data["admin_state"][str(user_id)]["give_target"] = target_id
            data["admin_state"][str(user_id)]["step"] = "give_points_amount"
            save_data(data)
            tu = data["users"][str(target_id)]
            send_msg(chat_id, f"💎 *Giving Points to @{tu['username']}*\n\nEnter amount:")
            return

        if step == "give_points_amount":
            target_id = data["admin_state"][str(user_id)].get("give_target", 0)
            amount = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if amount < 1 or str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ Invalid amount.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["balance"] = (
                data["users"][str(target_id)].get("balance", 0) + amount
            )
            data["users"][str(target_id)]["total_earned"] = (
                data["users"][str(target_id)].get("total_earned", 0) + amount
            )
            data = log_admin_action(user_id, "give_points", target_id, data)
            save_data(data)
            tu = data["users"][str(target_id)]
            new_bal = data["users"][str(target_id)]["balance"]
            send_msg(
                chat_id,
                f"✅ *POINTS GIVEN!*\n\n@{tu['username']}\n➕ `{amount}` points",
                admin_keyboard(),
            )
            send_msg(
                target_id,
                f"💎 *Points Added!*\n\n✨ Admin credited `{amount}` points\n💰 Balance: `₹{num(new_bal)}`",
            )
            return

        if step == "take_points_id":
            target_id = int(text) if text.isdigit() else 0
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                data["admin_state"].pop(str(user_id), None)
                save_data(data)
                return
            data["admin_state"][str(user_id)]["take_target"] = target_id
            data["admin_state"][str(user_id)]["step"] = "take_points_amount"
            save_data(data)
            tu = data["users"][str(target_id)]
            send_msg(chat_id, f"💸 *Taking Points from @{tu['username']}*\n\nEnter amount:")
            return

        if step == "take_points_amount":
            target_id = data["admin_state"][str(user_id)].get("take_target", 0)
            amount = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if amount < 1 or str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ Invalid amount.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["balance"] = max(
                0, data["users"][str(target_id)].get("balance", 0) - amount
            )
            data = log_admin_action(user_id, "take_points", target_id, data)
            save_data(data)
            tu = data["users"][str(target_id)]
            new_bal = data["users"][str(target_id)]["balance"]
            send_msg(
                chat_id,
                f"✅ *POINTS DEDUCTED!*\n\n@{tu['username']}\n➖ `{amount}` points",
                admin_keyboard(),
            )
            send_msg(target_id, f"⚠️ *Points Deducted*\n\nAdmin removed `{amount}` points")
            return

        if step == "search_user":
            data["admin_state"].pop(str(user_id), None)
            save_data(data)
            query = text.lower().lstrip("@")
            found = None
            for uid, u in data["users"].items():
                if u["username"].lower() == query or uid == text:
                    found = {"id": uid, "data": u}
                    break
            if not found:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
            else:
                u = found["data"]
                uid = found["id"]
                msg = f"🔍 *USER FOUND*\n\n👤 Name: `{u['first_name']}`\n🔖 @{u['username']}\n🆔 ID: `{uid}`\n━━━━━━━━━━━━━\n💰 Balance: `₹{num(u.get('balance', 0))}`\n💎 Earned: `₹{num(u.get('total_earned', 0))}`\n🔗 Referrals: `{u.get('referrals', 0)}`\n🎁 Codes: `{u.get('claimed', 0)}`\n⚠️ Warnings: `{u.get('warnings', 0)}/3`"
                send_msg(chat_id, msg, admin_keyboard())
            return

        if step == "user_info":
            target_id = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            u = data["users"][str(target_id)]
            status_str = "🔨 *BANNED*" if u.get("status") == "banned" else "✅ Active"
            msg = f"👁️ *FULL USER INFO*\n\n─── PROFILE ───\n👤 `{u['first_name']}`\n🔖 `@{u['username']}`\n🆔 `{target_id}`\n📅 `{u.get('joined_date', '')}`\n\n─── EARNINGS ───\n💰 Balance: `₹{num(u.get('balance', 0))}`\n💎 Total: `₹{num(u.get('total_earned', 0))}`\n🔗 Referrals: `{u.get('referrals', 0)}`\n🎁 Claimed: `{u.get('claimed', 0)}`\n\n─── SAFETY ───\n✅ Verified: {'Yes' if u.get('verified') else 'No'}\n⚠️ Warnings: `{u.get('warnings', 0)}/3`\n📊 Status: {status_str}"
            save_data(data)
            send_msg(chat_id, msg, admin_keyboard())
            return

        if step == "msg_user_id":
            target_id = int(text) if text.isdigit() else 0
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                data["admin_state"].pop(str(user_id), None)
                save_data(data)
                return
            data["admin_state"][str(user_id)]["msg_target"] = target_id
            data["admin_state"][str(user_id)]["step"] = "msg_user_text"
            save_data(data)
            tu = data["users"][str(target_id)]
            send_msg(chat_id, f"📩 *Send Message to @{tu['username']}*\n\nEnter message:")
            return

        if step == "msg_user_text":
            target_id = data["admin_state"][str(user_id)].get("msg_target", 0)
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            save_data(data)
            r = send_msg(target_id, f"📬 *Admin Message*\n\n{text}")
            if r.get("ok"):
                send_msg(chat_id, "✅ *Message Sent!*", admin_keyboard())
            else:
                send_msg(chat_id, "❌ Failed to send.", admin_keyboard())
            return

        if step == "reset_user":
            target_id = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if str(target_id) not in data["users"]:
                send_msg(chat_id, "❌ User not found.", admin_keyboard())
                save_data(data)
                return
            if target_id == OWNER_ID:
                send_msg(chat_id, "❌ Cannot reset owner.", admin_keyboard())
                save_data(data)
                return
            data["users"][str(target_id)]["referrals"] = 0
            data["users"][str(target_id)]["balance"] = 0
            data["users"][str(target_id)]["claimed"] = 0
            data["users"][str(target_id)]["total_earned"] = 0
            data["users"][str(target_id)]["claim_history"] = []
            data["users"][str(target_id)]["milestones_reached"] = []
            data["users"][str(target_id)]["warnings"] = 0
            data = log_admin_action(user_id, "reset_user", target_id, data)
            save_data(data)
            tu = data["users"][str(target_id)]
            send_msg(
                chat_id,
                f"🔄 *USER RESET!*\n\n@{tu['username']} stats cleared.",
                admin_keyboard(),
            )
            return

        if step == "set_refer_limit":
            n = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if n < 1:
                send_msg(chat_id, "❌ Must be ≥ 1.", admin_keyboard())
                save_data(data)
                return
            data["refer_limit"] = n
            save_data(data)
            send_msg(
                chat_id, f"⚙️ *LIMIT SET!*\n\nUsers need `{n}` points.", admin_keyboard()
            )
            return

        if step == "set_ppr":
            n = int(text) if text.isdigit() else 0
            data["admin_state"].pop(str(user_id), None)
            if n < 1:
                send_msg(chat_id, "❌ Must be ≥ 1.", admin_keyboard())
                save_data(data)
                return
            data["points_per_refer"] = n
            save_data(data)
            send_msg(
                chat_id, f"💡 *PPR UPDATED!*\n\nEach ref = `{n}` pts", admin_keyboard()
            )
            return

        if step == "edit_welcome":
            data["admin_state"].pop(str(user_id), None)
            data["welcome_msg"] = text
            save_data(data)
            send_msg(chat_id, "✏️ *WELCOME UPDATED!*", admin_keyboard())
            return
    except Exception as e:
        logger.error(f"Admin state error: {e}\n{traceback.format_exc()}")


def handle_user_menu(user_id, chat_id, text, data):
    """Handle user menu items"""
    try:
        def require_auth():
            if (
                not check_channels(user_id, data["channels"], data)
                or data["users"][str(user_id)].get("verified") == 0
            ):
                send_msg(chat_id, "⚠️ *LOCKED*\n\nType /start")
                return False
            return True

        if text == "🔗 Share Link":
            if not require_auth():
                return True
            me = tg_api("getMe")
            bot_username = me.get("result", {}).get("username", "bot")
            ref_link = f"https://t.me/{bot_username}?start={user_id}"
            limit = data.get("refer_limit", 5)
            ppr = data.get("points_per_refer", 1)
            refs = data["users"][str(user_id)].get("referrals", 0)
            bal = data["users"][str(user_id)].get("balance", 0)
            msg = f"🚀 *EARN*\n\n💵 Get `{ppr}` point/ref\n🎁 Redeem at `{limit}`\n\n🔗 Link: `{ref_link}`\n\n📊 Progress:\n🔗 Refs: `{refs}`\n💰 Balance: `₹{num(bal)}`\n{progress_bar(bal, limit)} `{bal}/{limit}`"
            send_msg(chat_id, msg)
            return True

        if text == "💰 My Balance":
            if not require_auth():
                return True
            limit = data.get("refer_limit", 5)
            bal = data["users"][str(user_id)].get("balance", 0)
            earned = data["users"][str(user_id)].get("total_earned", 0)
            msg = f"💰 *BALANCE*\n\n💵 Current: `₹{num(bal)}`\n💎 Total: `₹{num(earned)}`\n\n{progress_bar(bal, limit)}\n`{bal}/{limit}`"
            send_msg(chat_id, msg)
            return True

        if text == "🎁 Redeem Code":
            if not require_auth():
                return True
            limit = data.get("refer_limit", 5)
            bal = data["users"][str(user_id)].get("balance", 0)

            if bal < limit:
                need = limit - bal
                send_msg(
                    chat_id,
                    f"❌ *NOT ENOUGH!*\n\n💰 Have: `{bal}`\n🎯 Need: `{limit}`\n⏳ Missing: `{need}`",
                )
                return True

            code = None
            code_idx = None
            for idx, c in enumerate(data["codes"]):
                if c["status"] == "available":
                    code = c["text"]
                    code_idx = idx
                    break

            if not code:
                send_msg(chat_id, "📦 *OUT OF STOCK!*")
                return True

            data["codes"][code_idx]["status"] = "claimed"
            data["users"][str(user_id)]["balance"] -= limit
            data["users"][str(user_id)]["claimed"] = (
                data["users"][str(user_id)].get("claimed", 0) + 1
            )
            data["users"][str(user_id)]["claim_history"].append(
                {"code": code, "date": datetime.now().strftime("%d %b %Y %H:%M")}
            )
            save_data(data)

            new_bal = data["users"][str(user_id)]["balance"]
            msg = f"🎉 *REDEEMED!*\n\n🎁 Code: `{code}`\n\n💰 Balance: `₹{num(new_bal)}`\n🏆 Claimed: `{data['users'][str(user_id)]['claimed']}`"
            send_msg(chat_id, msg)
            return True

        if text == "📊 My Stats":
            if not require_auth():
                return True
            user = data["users"][str(user_id)]
            msg = f"📊 *STATS*\n\n👤 `{user['first_name']}`\n💰 Balance: `₹{num(user.get('balance', 0))}`\n💎 Total: `₹{num(user.get('total_earned', 0))}`\n🔗 Refs: `{user.get('referrals', 0)}`\n🎁 Codes: `{user.get('claimed', 0)}`"
            send_msg(chat_id, msg)
            return True

        if text == "🏆 Leaderboard":
            if not require_auth():
                return True
            users_list = list(data["users"].items())
            users_list.sort(key=lambda x: x[1].get("referrals", 0), reverse=True)
            msg = "🏆 *TOP EARNERS*\n\n"
            for i, (uid, u) in enumerate(users_list[:10]):
                if u.get("referrals", 0) < 1:
                    break
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
                msg += f"{medal} #{i + 1} `{u['referrals']}` @{u['username']}\n"
            send_msg(chat_id, msg)
            return True

        if text == "📋 History":
            if not require_auth():
                return True
            history = data["users"][str(user_id)].get("claim_history", [])
            if not history:
                send_msg(chat_id, "📋 *HISTORY*\n\nNone yet.")
                return True
            msg = "📋 *CLAIMS*\n\n"
            for h in reversed(history):
                msg += f"• `{h['code']}` - {h['date']}\n"
            send_msg(chat_id, msg)
            return True

        if text == "ℹ️ Help":
            limit = data.get("refer_limit", 5)
            ppr = data.get("points_per_refer", 1)
            msg = f"ℹ️ *HOW IT WORKS*\n\n1️⃣ Join channels\n2️⃣ Verify device\n3️⃣ Share link\n4️⃣ Earn `{ppr}` point/ref\n5️⃣ Get `{limit}` → redeem code"
            send_msg(chat_id, msg)
            return True

        if text == "⚙️ Settings":
            msg = f"⚙️ *SETTINGS*\n\n👤 @{data['users'][str(user_id)]['username']}\n🆔 `{user_id}`\n📅 `{data['users'][str(user_id)].get('joined_date', '')}`"
            send_msg(chat_id, msg)
            return True

        return False
    except Exception as e:
        logger.error(f"User menu error: {e}\n{traceback.format_exc()}")
        return False


# ════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ════════════════════════════════════════════════════════════════════════════


@app.route("/", methods=["GET"])
def index():
    return "✅ Bot is running!"


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}, 200


if __name__ == "__main__":
    logger.info("🚀 Starting Telegram Bot...")
    logger.info(f"Bot Token: {BOT_TOKEN[:20]}...")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info(f"Web URL: {WEB_URL}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    init_storage()
    logger.info(f"💾 Storage initialized")
    logger.info(f"📌 Bot listening on 0.0.0.0:{PORT}")
    
    app.run(host="0.0.0.0", port=PORT, debug=False)
