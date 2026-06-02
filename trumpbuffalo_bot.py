#!/usr/bin/env python3
import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8936595066:AAE41GZCQOxace8iVXMrsFiW-1pkUfr__ls")
BOT_USERNAME = "TrumpBuffaloMine_bot"

MINE_COOLDOWN_HOURS = 4
MINE_REWARD_BASE = 100
REFERRAL_BONUS = 500
WELCOME_BONUS = 200

SOCIAL_TASKS = {
    "twitter_follow": {
        "name": "Twitter/X Follow করো",
        "emoji": "🐦",
        "url": "https://x.com/TRUMPBUFFALO_",
        "reward": 300,
    },
    "facebook_follow": {
        "name": "Facebook Page Follow করো",
        "emoji": "📘",
        "url": "https://www.facebook.com/share/1cMyb7aPSu/",
        "reward": 300,
    },
    "telegram_channel": {
        "name": "Telegram Channel Join করো",
        "emoji": "📣",
        "url": "https://t.me/TrumpBuffalo_Official",
        "reward": 400,
    },
    "telegram_group": {
        "name": "Telegram Group Join করো",
        "emoji": "👥",
        "url": "https://t.me/TrumpBuffalo_Official",
        "reward": 400,
    },
}

DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "balance": 0,
            "last_mine": None,
            "referrals": 0,
            "referred_by": None,
            "username": "",
            "joined": datetime.now().isoformat(),
            "completed_tasks": []
        }
        save_db(db)
    return db[uid]

def update_user(user_id, data):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {}
    db[uid].update(data)
    save_db(db)

def can_mine(user_data):
    if not user_data["last_mine"]:
        return True, None
    last = datetime.fromisoformat(user_data["last_mine"])
    next_mine = last + timedelta(hours=MINE_COOLDOWN_HOURS)
    now = datetime.now()
    if now >= next_mine:
        return True, None
    remaining = next_mine - now
    h = int(remaining.total_seconds() // 3600)
    m = int((remaining.total_seconds() % 3600) // 60)
    return False, (h, m)

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⛏️ Mine TBUFF", callback_data="mine"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("👥 Referral", callback_data="referral"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🎁 Social Bonus", callback_data="social_bonus"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])

def social_kb(completed):
    rows = []
    for tid, task in SOCIAL_TASKS.items():
        if tid in completed:
            rows.append([InlineKeyboardButton(f"✅ {task['name']}", callback_data=f"done_{tid}")])
        else:
            rows.append([InlineKeyboardButton(f"{task['emoji']} {task['name']} → +{task['reward']} TBUFF", url=task["url"])])
            rows.append([InlineKeyboardButton("✔️ করেছি, বোনাস নাও!", callback_data=f"claim_{tid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    return InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    udata = get_user(uid)
    bonus_msg = ""

    if context.args and context.args[0].startswith("ref_"):
        ref_id = context.args[0].replace("ref_", "")
        if ref_id != uid and not udata["referred_by"]:
            update_user(uid, {
                "balance": udata["balance"] + WELCOME_BONUS,
                "referred_by": ref_id,
                "username": user.username or user.first_name
            })
            ref_data = get_user(ref_id)
            update_user(ref_id, {
                "balance": ref_data["balance"] + REFERRAL_BONUS,
                "referrals": ref_data["referrals"] + 1
            })
            bonus_msg = f"\n\n🎁 রেফারেল বোনাস: +{WELCOME_BONUS} TBUFF পেয়েছো!"
            try:
                await context.bot.send_message(
                    chat_id=int(ref_id),
                    text=f"🎉 {user.first_name} তোমার লিংক দিয়ে জয়েন করেছে!\n💰 +{REFERRAL_BONUS} TBUFF পেয়েছো!"
                )
            except:
                pass
    else:
        update_user(uid, {"username": user.username or user.first_name})

    text = f"""🦬 *TRUMPBUFFALO Mining Bot-এ স্বাগতম!*

হ্যালো *{user.first_name}*! 👋

🇧🇩 বাংলাদেশের ভাইরাল সাদা মহিষ এখন মিম কয়েন!

━━━━━━━━━━━━━━━
⛏️ প্রতি *{MINE_COOLDOWN_HOURS} ঘণ্টায়* একবার মাইন করো
💰 প্রতিবার *{MINE_REWARD_BASE} TBUFF* পাও
👥 রেফারেল করলে *{REFERRAL_BONUS} TBUFF* বোনাস
🎁 সোশ্যাল মিডিয়া ফলো করে *১,৪০০ TBUFF* পাও
━━━━━━━━━━━━━━━{bonus_msg}

নিচের বাটন থেকে শুরু করো! 👇"""

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_kb())

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    uid = str(user.id)
    d = q.data

    if d == "mine":
        udata = get_user(uid)
        ok, rem = can_mine(udata)
        if ok:
            nb = udata["balance"] + MINE_REWARD_BASE
            update_user(uid, {"balance": nb, "last_mine": datetime.now().isoformat()})
            text = f"⛏️ *মাইনিং সফল!*\n\n💰 পেয়েছো: *+{MINE_REWARD_BASE} TBUFF*\n🏦 মোট: *{nb:,} TBUFF*\n\n⏰ পরের মাইন: *{MINE_COOLDOWN_HOURS} ঘণ্টা পর*\n\n🚀 Make Crypto Great Again! 🦬"
        else:
            h, m = rem
            text = f"⏳ *এখনো মাইন করা যাবে না!*\n\n🕐 অপেক্ষা করো: *{h} ঘণ্টা {m} মিনিট*\n\n💡 এই সময়ে বন্ধুদের রেফার করো!"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())

    elif d == "balance":
        udata = get_user(uid)
        ok, rem = can_mine(udata)
        mine_st = "✅ এখনই মাইন করতে পারবে!" if ok else f"⏳ {rem[0]}ঘণ্টা {rem[1]}মিনিট পর"
        text = f"💰 *তোমার TBUFF ব্যালেন্স*\n\n👤 নাম: *{user.first_name}*\n🏦 ব্যালেন্স: *{udata['balance']:,} TBUFF*\n👥 রেফারেল: *{udata['referrals']}* জন\n⛏️ পরের মাইন: {mine_st}\n\n🦬 *$TRUMPBUFFALO — Moon Soon!* 🚀"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())

    elif d == "referral":
        udata = get_user(uid)
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        text = f"👥 *রেফারেল প্রোগ্রাম*\n\nতোমার লিংক:\n`{link}`\n\n━━━━━━━━━━━━━━━\n🎁 তুমি পাবে: *+{REFERRAL_BONUS} TBUFF*\n🎁 বন্ধু পাবে: *+{WELCOME_BONUS} TBUFF*\n\n📊 রেফারেল: *{udata['referrals']}* জন\n💰 রেফারেল আয়: *{udata['referrals']*REFERRAL_BONUS:,} TBUFF*\n\nলিংক কপি করে বন্ধুদের পাঠাও! 🚀"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())

    elif d == "leaderboard":
        db = load_db()
        top = sorted(db.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:10]
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        text = "🏆 *Top 10 TBUFF Miners*\n━━━━━━━━━━━━━━━\n"
        for i, (tid, td) in enumerate(top):
            name = td.get("username") or f"User_{tid[:4]}"
            text += f"{medals[i]} *{name}* — {td.get('balance',0):,} TBUFF\n"
        text += f"\n━━━━━━━━━━━━━━━\n👥 মোট মাইনার: *{len(db)}* জন"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())

    elif d == "social_bonus":
        udata = get_user(uid)
        completed = udata.get("completed_tasks", [])
        earned = sum(SOCIAL_TASKS[t]["reward"] for t in completed if t in SOCIAL_TASKS)
        total = sum(t["reward"] for t in SOCIAL_TASKS.values())
        text = f"🎁 *Social Media Bonus*\n\nসোশ্যাল মিডিয়া ফলো করো এবং TBUFF পাও!\n\n━━━━━━━━━━━━━━━\n✅ সম্পন্ন: *{len(completed)}/{len(SOCIAL_TASKS)}* টাস্ক\n💰 আয়: *{earned:,} TBUFF*\n🎯 বাকি: *{total-earned:,} TBUFF*\n━━━━━━━━━━━━━━━"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=social_kb(completed))

    elif d.startswith("claim_"):
        tid = d.replace("claim_", "")
        udata = get_user(uid)
        completed = udata.get("completed_tasks", [])
        if tid in completed:
            await q.answer("❌ এই বোনাস আগেই নেওয়া হয়েছে!", show_alert=True)
        elif tid in SOCIAL_TASKS:
            task = SOCIAL_TASKS[tid]
            completed.append(tid)
            update_user(uid, {"balance": udata["balance"] + task["reward"], "completed_tasks": completed})
            await q.answer(f"🎉 +{task['reward']} TBUFF পেয়েছো!", show_alert=True)
            udata2 = get_user(uid)
            completed2 = udata2.get("completed_tasks", [])
            earned = sum(SOCIAL_TASKS[t]["reward"] for t in completed2 if t in SOCIAL_TASKS)
            total = sum(t["reward"] for t in SOCIAL_TASKS.values())
            text = f"🎁 *Social Media Bonus*\n\nসোশ্যাল মিডিয়া ফলো করো এবং TBUFF পাও!\n\n━━━━━━━━━━━━━━━\n✅ সম্পন্ন: *{len(completed2)}/{len(SOCIAL_TASKS)}* টাস্ক\n💰 আয়: *{earned:,} TBUFF*\n🎯 বাকি: *{total-earned:,} TBUFF*\n━━━━━━━━━━━━━━━"
            await q.edit_message_text(text, parse_mode="Markdown", reply_markup=social_kb(completed2))

    elif d.startswith("done_"):
        await q.answer("✅ এই টাস্ক আগেই সম্পন্ন!", show_alert=True)

    elif d == "about":
        text = "🦬 *TRUMPBUFFALO ($TBUFF)*\n\nবাংলাদেশের ভাইরাল সাদা মহিষ এখন মিম কয়েন!\n\n━━━━━━━━━━━━━━━\n🇧🇩 Made in Bangladesh\n🚀 Mission: Make Crypto Great Again\n💎 Symbol: TBUFF\n⛏️ Mining: প্রতি ৪ ঘণ্টায়\n━━━━━━━━━━━━━━━\n\n📱 Twitter: @TRUMPBUFFALO_\n📘 Facebook: TrumpBuffalo Official\n\n🌙 To The Moon! 🦬🚀"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())

    elif d == "menu":
        text = f"🦬 *TRUMPBUFFALO Mining Bot*\n\nহ্যালো *{user.first_name}*! নিচের বাটন ব্যবহার করো 👇"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_kb())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn))
    print("🦬 TrumpBuffalo Bot চালু হচ্ছে...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
