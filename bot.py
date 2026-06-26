import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from aiocryptopay import AioCryptoPay, Networks

BOT_TOKEN = “8707588389:AAHyWwgBk_oiOR2EOlCiPz1U6a1AqlApZ-0”
CRYPTO_PAY_TOKEN = “558733:AAW89dDTcwiRvVWZXc4Pr2tWzJvqOXtylPG”
STANDARD_INVITE_LINK = “https://t.me/+7sLUDUEWQLZhY2Vh”
PREMIUM_INVITE_LINK = “https://t.me/+vXAfYJQFD6NhNTc5”
CHANNEL_USERNAME = “@YourChannel”  # Replace with your channel username
SUPPORT_USERNAME = “@YourSupport”  # Replace with your support username

STANDARD_PRICE = 25
PREMIUM_PRICE = 50

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)
pending_invoices = {}
user_deals = {}  # Store user deals

def main_menu_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton(“🛒 Create deal”, callback_data=“create_deal”)],
[
InlineKeyboardButton(“💼 My deals”, callback_data=“my_deals”),
InlineKeyboardButton(“🔒 Verification”, callback_data=“verification”),
],
[
InlineKeyboardButton(“🗂 Requisites”, callback_data=“requisites”),
InlineKeyboardButton(“🌐 Language”, callback_data=“language”),
],
[
InlineKeyboardButton(“🔗 Referrals”, callback_data=“referrals”),
InlineKeyboardButton(“ℹ️ More”, callback_data=“more”),
],
[
InlineKeyboardButton(“📢 Trustify Market ↗”, url=f”https://t.me/TrustifyNew”),
InlineKeyboardButton(“📁 Appeals”, callback_data=“appeals”),
],
[InlineKeyboardButton(“👥 Support ↗”, url=f”https://t.me/YourSupport”)],
[InlineKeyboardButton(“🤖 Mini-app”, callback_data=“miniapp”)],
])

def main_menu_text():
return (
“🛡 *TRUSTIFY MARKET* 🛡\n\n”
“📥 *Our advantages:*\n\n”
“• Fraud protection\n”
“• Automatic fund holding\n”
“• Transparent statistics\n”
“• 24/7 support\n”
“• Deal history\n\n”
f”📣 Channel — {CHANNEL_USERNAME}”
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
main_menu_text(),
parse_mode=“Markdown”,
reply_markup=main_menu_keyboard()
)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data

```
# --- Create Deal ---
if data == "create_deal":
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🥈 Standard - $25", callback_data="plan_standard")],
        [InlineKeyboardButton("🥇 Premium - $50", callback_data="plan_premium")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])
    await query.edit_message_text(
        "🛒 *Create Deal*\n\nChoose a plan:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# --- Plan Selection ---
elif data.startswith("plan_"):
    amount = STANDARD_PRICE if data == "plan_standard" else PREMIUM_PRICE
    plan_name = "Standard" if data == "plan_standard" else "Premium"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 USDT", callback_data=f"pay_USDT_{data}")],
        [InlineKeyboardButton("💎 TON", callback_data=f"pay_TON_{data}")],
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_BTC_{data}")],
        [InlineKeyboardButton("⟠ ETH", callback_data=f"pay_ETH_{data}")],
        [InlineKeyboardButton("🔙 Back", callback_data="create_deal")],
    ])
    await query.edit_message_text(
        f"You selected *{plan_name}* (${amount})\n\nChoose crypto to pay:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# --- Crypto Selection ---
elif data.startswith("pay_"):
    parts = data.split("_", 2)
    asset = parts[1]
    plan_key = parts[2]
    amount = STANDARD_PRICE if plan_key == "plan_standard" else PREMIUM_PRICE
    plan_name = "Standard" if plan_key == "plan_standard" else "Premium"
    await query.edit_message_text("⏳ Generating invoice...")
    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        invoice = await crypto.create_invoice(
            asset=asset,
            amount=amount,
            description=f"{plan_name} Plan Access",
            payload=f"{query.from_user.id}_{plan_key}",
            expires_in=3600
        )
        await crypto.close()
        pending_invoices[invoice.invoice_id] = {
            "user_id": query.from_user.id,
            "plan": plan_key
        }
        # Store in user deals
        uid = query.from_user.id
        if uid not in user_deals:
            user_deals[uid] = []
        user_deals[uid].append({
            "invoice_id": invoice.invoice_id,
            "plan": plan_name,
            "amount": amount,
            "asset": asset,
            "status": "pending"
        })
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Now", url=invoice.bot_invoice_url)],
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"check_{invoice.invoice_id}")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")],
        ])
        await query.edit_message_text(
            f"✅ *Invoice Created!*\n\n"
            f"Plan: *{plan_name}*\n"
            f"Amount: *${amount} ({asset})*\n\n"
            f"Tap *Pay Now*, then tap *I've Paid* after completing payment.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await query.edit_message_text(f"❌ Error creating invoice: {str(e)}")

# --- Check Payment ---
elif data.startswith("check_"):
    invoice_id = int(data.split("_")[1])
    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        await crypto.close()
        invoice = invoices[0] if invoices else None
        if invoice and invoice.status == "paid":
            plan_key = pending_invoices.get(invoice_id, {}).get("plan", "")
            invite_link = STANDARD_INVITE_LINK if plan_key == "plan_standard" else PREMIUM_INVITE_LINK
            plan_name = "Standard" if plan_key == "plan_standard" else "Premium"
            # Update deal status
            uid = query.from_user.id
            if uid in user_deals:
                for deal in user_deals[uid]:
                    if deal["invoice_id"] == invoice_id:
                        deal["status"] = "paid"
            await query.edit_message_text(
                f"🎉 *Payment Confirmed!*\n\n"
                f"Welcome to *{plan_name}*!\n\n"
                f"{invite_link}\n\n"
                f"⚠️ Do not share this link.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
                ])
            )
            pending_invoices.pop(invoice_id, None)
        elif invoice and invoice.status == "expired":
            await query.edit_message_text(
                "❌ Invoice expired. Please start again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
                ])
            )
        else:
            await query.edit_message_text(
                "⏳ Payment not confirmed yet. Complete payment and tap I've Paid again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ I've Paid", callback_data=f"check_{invoice_id}")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")],
                ])
            )
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")

# --- My Deals ---
elif data == "my_deals":
    uid = query.from_user.id
    deals = user_deals.get(uid, [])
    if not deals:
        text = "💼 *My Deals*\n\nYou have no deals yet."
    else:
        text = "💼 *My Deals*\n\n"
        for i, deal in enumerate(deals, 1):
            status_emoji = "✅" if deal["status"] == "paid" else "⏳"
            text += f"{i}. {deal['plan']} — ${deal['amount']} {deal['asset']} {status_emoji}\n"
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- Verification ---
elif data == "verification":
    await query.edit_message_text(
        "🔒 *Verification*\n\nVerification helps protect both buyers and sellers.\n\nContact support to get verified.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Contact Support ↗", url="https://t.me/YourSupport")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ])
    )

# --- Requisites ---
elif data == "requisites":
    await query.edit_message_text(
        "🗂 *Requisites*\n\nAdd your payment details to receive funds from deals.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- Language ---
elif data == "language":
    await query.edit_message_text(
        "🌐 *Language*\n\nChoose your language:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ])
    )

elif data.startswith("lang_"):
    lang = "English" if data == "lang_en" else "Russian"
    await query.edit_message_text(
        f"✅ Language set to *{lang}*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- Referrals ---
elif data == "referrals":
    uid = query.from_user.id
    await query.edit_message_text(
        f"🔗 *Referrals*\n\nShare your referral link and earn rewards!\n\n"
        f"Your link: `https://t.me/TrustifyMarketBot?start={uid}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- More ---
elif data == "more":
    await query.edit_message_text(
        "ℹ️ *More*\n\n• Version: 1.0\n• Powered by TrustifyMarketBot\n• Secure crypto escrow service",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- Appeals ---
elif data == "appeals":
    await query.edit_message_text(
        "📁 *Appeals*\n\nIf you have a dispute with a deal, contact support with your deal details.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Contact Support ↗", url="https://t.me/YourSupport")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ])
    )

# --- Mini-app ---
elif data == "miniapp":
    await query.edit_message_text(
        "🤖 *Mini-app*\n\nThe mini-app is coming soon!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])
    )

# --- Back to Main Menu ---
elif data == "back_main":
    await query.edit_message_text(
        main_menu_text(),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
```

def main():
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CallbackQueryHandler(handle_buttons))
logger.info(“TrustifyMarketBot is running…”)
app.run_polling(allowed_updates=Update.ALL_TYPES)

if **name** == “**main**”:
main()
