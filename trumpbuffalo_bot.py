#!/usr/bin/env python3
"""
🦬 TRUMPBUFFALO Mining Bot
Telegram Bot for TRUMPBUFFALO ($TBUFF) token mining
"""

import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ============================================================
# ⚙️ CONFIGURATION — তোমার BOT TOKEN এখানে বসাও
# ============================================================
BOT_TOKEN = "8936595066:AAE41GZCQOxace8iVXMrsFiW-1pkUfr__ls"
BOT_USERNAME = "TrumpBuffaloMine_bot"

# Mining Settings
MINE_COOLDOWN_HOURS = 4            # কত ঘণ্টা পর পর মাইন করা যাবে
MINE_REWARD_BASE = 100             # প্রতিবার মাইনে কত TBUFF
REFERRAL_BONUS = 500               # রেফারেল করলে কত TBUFF বোনাস
WELCOME_BONUS = 200                # নতুন ইউজার জয়েন করলে বোনাস

# Social Media Bonus Settings
SOCIAL_TASKS = {
    "twitter_follow": {
        "name": "Twitter/X Follow করো",
        "emoji": "🐦",
        "url": "https://x.com/TRUMPBUFFALO_",
        "reward": 300,
        "instruction": "@TRUMPBUFFALO_ ফলো করো"
    },
    "facebook_follow": {
        "name": "Facebook Page Follow করো",
        "emoji": "📘",
        "url": "https://www.facebook.com/share/1cMyb7aPSu/",
        "reward": 300,
        "instruction": "TrumpBuffalo Official পেজ ফলো করো"
    },
    "telegram_channel": {
        "name": "Telegram Channel Join করো",
        "emoji": "📣",
        "url": "https://t.me/TrumpBuffalo_Official",
        "reward": 400,
        "instruction": "অফিসিয়াল Telegram চ্যানেল জয়েন করো"
    },
    "telegram_group": {
        "name": "Telegram Group Join করো",
        "emoji": "👥",
        "url": "https://t.me/TrumpBuffalo_Official",  # গ্রুপ লিংক থাকলে পরিবর্তন করো
        "reward": 400,
        "instruction": "TrumpBuffalo Community গ্রুপে জয়েন করো"
    },
}

# Database file (simple JSON — পরে real DB দিয়ে replace করো)
DB_FILE = "users.json"

# ============================================================
# 📦 DATABASE FUNCTIONS
# ============================================================

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {
            "balance": 0,
            "last_mine": None,
            "referrals": 0,
            "referred_by": None,
            "username": "",
            "joined": datetime.now().isoformat(),
            "completed_tasks": []   # সোশ্যাল মিডিয়া টাস্ক ট্র্যাক করবে
        }
        save_db(db)
    return db[user_id]

def update_user(user_id: str, data: dict):
    db = load_db()
    if user_id not in db:
        db[user_id] = {}
    db[user_id].update(data)
    save_db(db)

def get_total_users():
    return len(load_db())

def get_leaderboard(top=10):
    db = load_db()
    sorted_users = sorted(db.items(), key=lambda x: x[1].get("balance", 0), reverse=True)
    return sorted_users[:top]

# ============================================================
# ⏱️ MINING LOGIC
# ============================================================

def can_mine(user_data: dict):
    if user_data["last_mine"] is None:
        return True, 0
    last = datetime.fromisoformat(user_data["last_mine"])
    next_mine = last + timedelta(hours=MINE_COOLDOWN_HOURS)
    now = datetime.now()
    if now >= next_mine:
        return True, 0
    remaining = next_mine - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return False, (hours, minutes)

# ============================================================
# 🎨 KEYBOARDS
# ============================================================

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⛏️ Mine TBUFF", callback_data="mine"),
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("👥 Referral", callback_data="referral"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
        ],
        [
            InlineKeyboardButton("🎁 Social Bonus", callback_data="social_bonus"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])

def social_bonus_keyboard(completed_tasks: list):
    keyboard = []
    for task_id, task in SOCIAL_TASKS.items():
        if task_id in completed_tasks:
            # ইতিমধ্যে করা হয়েছে — ✅ দেখাবে
            btn_text = f"✅ {task['name']} (+{task['reward']} TBUFF)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"task_done_{task_id}")])
        else:
            # এখনো করা হয়নি
            btn_text = f"{task['emoji']} {task['name']} → +{task['reward']} TBUFF"
            keyboard.append([InlineKeyboardButton(btn_text, url=task["url"])])
            keyboard.append([InlineKeyboardButton(f"✔️ করেছি, বোনাস নাও!", callback_data=f"claim_{task_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# 🤖 COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_data = get_user(user_id)

    # রেফারেল চেক করো
    referral_msg = ""
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        if referrer_id != user_id and user_data["referred_by"] is None:
            # নতুন ইউজারকে welcome bonus দাও
            new_balance = user_data["balance"] + WELCOME_BONUS
            update_user(user_id, {
                "balance": new_balance,
                "referred_by": referrer_id,
                "username": user.username or user.first_name
            })

            # রেফারারকে বোনাস দাও
            referrer_data = get_user(referrer_id)
            referrer_balance = referrer_data["balance"] + REFERRAL_BONUS
            referrer_refs = referrer_data["referrals"] + 1
            update_user(referrer_id, {
                "balance": referrer_balance,
                "referrals": referrer_refs
            })

            referral_msg = f"\n\n🎁 *রেফারেল বোনাস:* তুমি +{WELCOME_BONUS} TBUFF পেয়েছো!"

            # রেফারারকে নোটিফাই করো
            try:
                await context.bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"🎉 নতুন রেফারেল!\n\n👤 *{user.first_name}* তোমার লিংক দিয়ে জয়েন করেছে!\n💰 তুমি *+{REFERRAL_BONUS} TBUFF* পেয়েছো!",
                    parse_mode="Markdown"
                )
            except:
                pass
    else:
        update_user(user_id, {"username": user.username or user.first_name})

    welcome_text = f"""
🦬 *TRUMPBUFFALO Mining Bot-এ স্বাগতম!*

হ্যালো *{user.first_name}*! 👋

🇧🇩 বাংলাদেশের ভাইরাল সাদা মহিষ এখন মিম কয়েন!

━━━━━━━━━━━━━━━
⛏️ প্রতি *{MINE_COOLDOWN_HOURS} ঘণ্টায়* একবার মাইন করো
💰 প্রতিবার *{MINE_REWARD_BASE} TBUFF* পাও
👥 রেফারেল করলে *{REFERRAL_BONUS} TBUFF* বোনাস
🎁 সোশ্যাল মিডিয়া ফলো করে *১,৪০০ TBUFF* পাও
━━━━━━━━━━━━━━━{referral_msg}

নিচের বাটন থেকে শুরু করো! 👇
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = str(user.id)
    data = query.data

    # ⛏️ MINE
    if data == "mine":
        user_data = get_user(user_id)
        can, remaining = can_mine(user_data)

        if can:
            reward = MINE_REWARD_BASE
            new_balance = user_data["balance"] + reward
            update_user(user_id, {
                "balance": new_balance,
                "last_mine": datetime.now().isoformat()
            })
            text = f"""
⛏️ *মাইনিং সফল!*

🦬 *TRUMPBUFFALO* মাইন করা হয়েছে!

💰 পেয়েছো: *+{reward} TBUFF*
🏦 মোট ব্যালেন্স: *{new_balance:,} TBUFF*

⏰ পরের মাইনিং: *{MINE_COOLDOWN_HOURS} ঘণ্টা পর*

🚀 *Make Crypto Great Again!* 🦬🇧🇩
"""
        else:
            hours, minutes = remaining
            text = f"""
⏳ *এখনো মাইন করা যাবে না!*

🕐 অপেক্ষা করো: *{hours} ঘণ্টা {minutes} মিনিট*

💡 এই সময়ে বন্ধুদের রেফার করো!
👥 প্রতি রেফারেলে *{REFERRAL_BONUS} TBUFF* বোনাস!
"""
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    # 💰 BALANCE
    elif data == "balance":
        user_data = get_user(user_id)
        can, remaining = can_mine(user_data)

        if can:
            mine_status = "✅ এখনই মাইন করতে পারবে!"
        else:
            hours, minutes = remaining
            mine_status = f"⏳ {hours}ঘণ্টা {minutes}মিনিট পর"

        text = f"""
💰 *তোমার TBUFF ব্যালেন্স*

👤 নাম: *{user.first_name}*
🏦 ব্যালেন্স: *{user_data['balance']:,} TBUFF*
👥 রেফারেল: *{user_data['referrals']}* জন
⛏️ পরের মাইন: {mine_status}

━━━━━━━━━━━━━━━
🦬 *$TRUMPBUFFALO — Moon Soon!* 🚀
"""
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    # 👥 REFERRAL
    elif data == "referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        user_data = get_user(user_id)
        text = f"""
👥 *রেফারেল প্রোগ্রাম*

তোমার রেফারেল লিংক:
`{ref_link}`

━━━━━━━━━━━━━━━
🎁 *বোনাস:*
• তুমি পাবে: *+{REFERRAL_BONUS} TBUFF*
• বন্ধু পাবে: *+{WELCOME_BONUS} TBUFF*

📊 *তোমার রেফারেল:* {user_data['referrals']} জন
💰 *রেফারেল আয়:* {user_data['referrals'] * REFERRAL_BONUS:,} TBUFF

━━━━━━━━━━━━━━━
লিংকটা কপি করে বন্ধুদের পাঠাও! 🚀
"""
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    # 🏆 LEADERBOARD
    elif data == "leaderboard":
        leaders = get_leaderboard(10)
        total = get_total_users()
        text = "🏆 *Top 10 TBUFF Miners*\n━━━━━━━━━━━━━━━\n"

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, (uid, udata) in enumerate(leaders):
            name = udata.get("username") or f"User_{uid[:4]}"
            balance = udata.get("balance", 0)
            text += f"{medals[i]} *{name}* — {balance:,} TBUFF\n"

        text += f"\n━━━━━━━━━━━━━━━\n👥 মোট মাইনার: *{total}* জন"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    # ℹ️ ABOUT
    elif data == "about":
        text = """
🦬 *TRUMPBUFFALO ($TBUFF)*

বাংলাদেশের ভাইরাল সাদা মহিষ এখন মিম কয়েন!

━━━━━━━━━━━━━━━
🇧🇩 *Made in Bangladesh*
🚀 *Mission:* Make Crypto Great Again
💎 *Symbol:* TBUFF
⛏️ *Mining:* প্রতি ৪ ঘণ্টায়
━━━━━━━━━━━━━━━

📱 Follow us:
• Twitter: @TRUMPBUFFALO_
• Facebook: TrumpBuffalo Official

🌙 *To The Moon!* 🦬🚀
"""
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())

    # 🎁 SOCIAL BONUS মেনু
    elif data == "social_bonus":
        user_data = get_user(user_id)
        completed = user_data.get("completed_tasks", [])
        total_possible = sum(t["reward"] for t in SOCIAL_TASKS.values())
        total_earned = sum(SOCIAL_TASKS[t]["reward"] for t in completed if t in SOCIAL_TASKS)
        remaining = total_possible - total_earned

        text = f"""
🎁 *Social Media Bonus*

আমাদের সোশ্যাল মিডিয়া ফলো করো এবং বোনাস TBUFF পাও!

━━━━━━━━━━━━━━━
✅ সম্পন্ন: *{len(completed)}/{len(SOCIAL_TASKS)}* টাস্ক
💰 আয় করেছো: *{total_earned:,} TBUFF*
🎯 বাকি আছে: *{remaining:,} TBUFF*
━━━━━━━━━━━━━━━

নিচের লিংকে গিয়ে ফলো/জয়েন করো, তারপর *"করেছি"* বাটন চাপো!
"""
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=social_bonus_keyboard(completed)
        )

    # ✔️ CLAIM SOCIAL BONUS
    elif data.startswith("claim_"):
        task_id = data.replace("claim_", "")
        user_data = get_user(user_id)
        completed = user_data.get("completed_tasks", [])

        if task_id in completed:
            await query.answer("❌ এই বোনাস আগেই নেওয়া হয়েছে!", show_alert=True)
        elif task_id in SOCIAL_TASKS:
            task = SOCIAL_TASKS[task_id]
            new_balance = user_data["balance"] + task["reward"]
            completed.append(task_id)
            update_user(user_id, {
                "balance": new_balance,
                "completed_tasks": completed
            })
            await query.answer(f"🎉 +{task['reward']} TBUFF পেয়েছো!", show_alert=True)

            # আপডেট করা মেনু দেখাও
            total_possible = sum(t["reward"] for t in SOCIAL_TASKS.values())
            total_earned = sum(SOCIAL_TASKS[t]["reward"] for t in completed if t in SOCIAL_TASKS)
            remaining = total_possible - total_earned

            text = f"""
🎁 *Social Media Bonus*

আমাদের সোশ্যাল মিডিয়া ফলো করো এবং বোনাস TBUFF পাও!

━━━━━━━━━━━━━━━
✅ সম্পন্ন: *{len(completed)}/{len(SOCIAL_TASKS)}* টাস্ক
💰 আয় করেছো: *{total_earned:,} TBUFF*
🎯 বাকি আছে: *{remaining:,} TBUFF*
━━━━━━━━━━━━━━━

নিচের লিংকে গিয়ে ফলো/জয়েন করো, তারপর *"করেছি"* বাটন চাপো!
"""
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=social_bonus_keyboard(completed)
            )

    # ইতিমধ্যে করা টাস্কে ক্লিক করলে
    elif data.startswith("task_done_"):
        await query.answer("✅ এই টাস্ক আগেই সম্পন্ন হয়েছে!", show_alert=True)

    # 🔙 MENU
    elif data == "menu":
        text = f"🦬 *TRUMPBUFFALO Mining Bot*\n\nহ্যালো *{user.first_name}*! নিচের বাটন ব্যবহার করো 👇"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

# ============================================================
# 🚀 MAIN — বট চালু করো
# ============================================================

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🦬 TrumpBuffalo Bot চালু হচ্ছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
