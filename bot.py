import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiocryptopay import AioCryptoPay, Networks

# ============================================================
# PASTE YOUR TOKENS HERE (keep these private)
# ============================================================
BOT_TOKEN = "8707588389:AAHyWwgBk_oiOR2EOlCiPz1U6a1AqlApZ-0"
CRYPTO_PAY_TOKEN = "558733:AAW89dDTcwiRvVWZXc4Pr2tWzJvqOXtylPG"
STANDARD_INVITE_LINK = "https://t.me/+7sLUDUEWQLZhY2Vh"
PREMIUM_INVITE_LINK = "https://t.me/+vXAfYJQFD6NhNTc5"
# ============================================================

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
        "👋 Welcome!\n\n"
        "Choose a plan to get access:\n\n"
        "🥈 *Standard - $25*\n"
        "Access to the Standard channel\n\n"
        "🥇 *Premium - $50*\n"
        "Access to the Premium channel\n\n"
        "Select a plan below to continue:",
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
        f"You selected *{plan_name}* (${amount})\n\n"
        f"Choose your preferred crypto to pay:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 2)
    asset = parts[1]
    plan_key = parts[2]
    user_id = query.from_user.id

    amount = STANDARD_PRICE if plan_key == "plan_standard" else PREMIUM_PRICE
    plan_name = "Standard" if plan_key == "plan_standard" else "Premium"

    await query.edit_message_text("⏳ Generating your invoice, please wait...")

    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        invoice = await crypto.create_invoice(
            asset=asset,
            amount=amount,
            description=f"{plan_name} Plan Access",
            payload=f"{user_id}_{plan_key}",
            expires_in=3600
        )
        await crypto.close()

        pending_invoices[invoice.invoice_id] = {
            "user_id": user_id,
            "plan": plan_key
        }

        keyboard = [
            [InlineKeyboardButton("💳 Pay Now", url=invoice.pay_url)],
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"check_{invoice.invoice_id}")]
        ]
        await query.edit_message_text(
            f"✅ *Invoice Created!*\n\n"
            f"Plan: *{plan_name}*\n"
            f"Amount: *${amount} ({asset})*\n\n"
            f"1. Tap *Pay Now* to complete payment\n"
            f"2. Come back and tap *I've Paid* to get your access\n\n"
            f"⚠️ Invoice expires in 1 hour.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
     except Exception as e:
        logger.error(f"Invoice creation error: {e}")
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
                f"🎉 *Payment Confirmed!*\n\n"
                f"Welcome to {plan_name}!\n\n"
                f"👇 Here is your exclusive invite link:\n"
                f"{invite_link}\n\n"
                f"⚠️ Do not share this link with others.",
                parse_mode="Markdown"
            )
            pending_invoices.pop(invoice_id, None)

        elif invoice and invoice.status == "expired":
            await query.edit_message_text(
                "❌ Your invoice has expired. Please start again with /start"
            )
        else:
            await query.edit_message_text(
                "⏳ Payment not confirmed yet.\n\n"
                "Please complete the payment and tap *I've Paid* again.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await query.edit_message_text("❌ Error checking payment. Please try again.")


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
