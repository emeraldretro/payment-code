import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiocryptopay import AioCryptoPay, Networks

BOT_TOKEN = "8707588389:AAHyWwgBk_oiOR2EOlCiPz1U6a1AqlApZ-0"
CRYPTO_PAY_TOKEN = "558733:AAW89dDTcwiRvVWZXc4Pr2tWzJvqOXtylPG"
STANDARD_INVITE_LINK = "https://t.me/+7sLUDUEWQLZhY2Vh"
PREMIUM_INVITE_LINK = "https://t.me/+vXAfYJQFD6NhNTc5"

STANDARD_PRICE = 25
PREMIUM_PRICE = 50

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
pending_invoices = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🥈 Standard - $25", callback_data="plan_standard")],
        [InlineKeyboardButton("🥇 Premium - $50", callback_data="plan_premium")],
    ]
    await update.message.reply_text(
        "👋 Welcome!\n\nChoose a plan:\n\n🥈 *Standard - $25*\n🥇 *Premium - $50*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data
    amount = STANDARD_PRICE if plan == "plan_standard" else PREMIUM_PRICE
    plan_name = "Standard" if plan == "plan_standard" else "Premium"
    keyboard = [
        [InlineKeyboardButton("💵 USDT", callback_data=f"pay_USDT_{plan}")],
        [InlineKeyboardButton("💎 TON", callback_data=f"pay_TON_{plan}")],
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_BTC_{plan}")],
        [InlineKeyboardButton("⟠ ETH", callback_data=f"pay_ETH_{plan}")],
    ]
    await query.edit_message_text(
        f"You selected *{plan_name}* (${amount})\n\nChoose crypto to pay:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_", 2)
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
        pending_invoices[invoice.invoice_id] = {"user_id": query.from_user.id, "plan": plan_key}
        keyboard = [
            [InlineKeyboardButton("💳 Pay Now", url=invoice.bot_invoice_url)],
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"check_{invoice.invoice_id}")]
        ]
        await query.edit_message_text(
            f"✅ *Invoice Created!*\n\nPlan: *{plan_name}*\nAmount: *${amount} ({asset})*\n\nTap Pay Now, then tap I've Paid after.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    invoice_id = int(query.data.split("_")[1])
    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        await crypto.close()
        invoice = invoices[0] if invoices else None
        if invoice and invoice.status == "paid":
            plan_key = pending_invoices.get(invoice_id, {}).get("plan", "")
            invite_link = STANDARD_INVITE_LINK if plan_key == "plan_standard" else PREMIUM_INVITE_LINK
            plan_name = "Standard" if plan_key == "plan_standard" else "Premium"
            await query.edit_message_text(
                f"🎉 *Payment Confirmed!*\n\nWelcome to {plan_name}!\n\n{invite_link}\n\n⚠️ Do not share this link.",
                parse_mode="Markdown"
            )
            pending_invoices.pop(invoice_id, None)
        elif invoice and invoice.status == "expired":
            await query.edit_message_text("❌ Invoice expired. Please /start again.")
        else:
            await query.edit_message_text("⏳ Payment not confirmed yet. Please complete payment and tap I've Paid again.")
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_plan_selection, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(handle_crypto_selection, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_"))
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
