import uuid
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiocryptopay import AioCryptoPay, Networks
import uuid

# ============================================================
# PASTE YOUR TOKENS HERE (keep these private)
# ============================================================
BOT_TOKEN = "8707588389:AAHyWwgBk_oiOR2EOlCiPz1U6a1AqlApZ-0"
CRYPTO_PAY_TOKEN = "558733:AAMBFhSntY6e4xrPT9VpbU4btRHNO3eYWna"

STANDARD_INVITE_LINK = "https://t.me/+7sLUDUEWQLZhY2Vh"
PREMIUM_INVITE_LINK = "https://t.me/+vXAfYJQFD6NhNTc5"
# ============================================================

STANDARD_PRICE = 25  # USD
PREMIUM_PRICE = 50   # USD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

# Store pending invoices: {invoice_id: {"user_id": ..., "plan": ...}}
pending_invoices = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🥈 Standard - $25", callback_data="plan_standard")],
        [InlineKeyboardButton("🥇 Premium - $50", callback_data="plan_premium")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Choose a plan to get access:\n\n"
        "🥈 *Standard - $25*\n"
        "Access to the Standard channel\n\n"
        "🥇 *Premium - $50*\n"
        "Access to the Premium channel\n\n"
        "Select a plan below to continue:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan = query.data  # "plan_standard" or "plan_premium"
    user_id = query.from_user.id

    if plan == "plan_standard":
        amount = STANDARD_PRICE
        plan_name = "Standard"
    else:
        amount = PREMIUM_PRICE
        plan_name = "Premium"

    # Choose crypto options
    keyboard = [
        [InlineKeyboardButton("💵 USDT", callback_data=f"pay_USDT_{plan}")],
        [InlineKeyboardButton("💎 TON", callback_data=f"pay_TON_{plan}")],
        [InlineKeyboardButton("₿ BTC", callback_data=f"pay_BTC_{plan}")],
        [InlineKeyboardButton("⟠ ETH", callback_data=f"pay_ETH_{plan}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"You selected *{plan_name}* (${amount})\n\n"
        f"Choose your preferred crypto to pay:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, asset, plan = query.data.split("_", 2)  # e.g. pay_USDT_plan_standard
    plan_key = plan  # "plan_standard" or "plan_premium"
    user_id = query.from_user.id

    amount = STANDARD_PRICE if plan_key == "plan_standard" else PREMIUM_PRICE
    plan_name = "Standard" if plan_key == "plan_standard" else "Premium"

    await query.edit_message_text("⏳ Generating your invoice, please wait...")

    try:
        invoice = await crypto.create_invoice(
            asset=asset,
            amount=amount,
            description=f"{plan_name} Plan Access",
            payload=f"{user_id}_{plan_key}",
            allow_comments=False,
            allow_anonymous=False,
            expires_in=3600  # 1 hour to pay
        )

        pending_invoices[invoice.invoice_id] = {
            "user_id": user_id,
            "plan": plan_key
        }

        keyboard = [
            [InlineKeyboardButton("💳 Pay Now", url=invoice.pay_url)],
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"check_{invoice.invoice_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ *Invoice Created!*\n\n"
            f"Plan: *{plan_name}*\n"
            f"Amount: *${amount} ({asset})*\n\n"
            f"1. Tap *Pay Now* to complete payment\n"
            f"2. Come back and tap *I've Paid* to get your access\n\n"
            f"⚠️ Invoice expires in 1 hour.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Invoice creation error: {e}")
        await query.edit_message_text("❌ Error creating invoice. Please try again with /start")


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    invoice_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    try:
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        invoice = invoices[0] if invoices else None

        if invoice and invoice.status == "paid":
            plan_key = pending_invoices.get(invoice_id, {}).get("plan", "")

            if plan_key == "plan_standard":
                invite_link = STANDARD_INVITE_LINK
                plan_name = "Standard"
            else:
                invite_link = PREMIUM_INVITE_LINK
                plan_name = "Premium"

            await query.edit_message_text(
                f"🎉 *Payment Confirmed!*\n\n"
                f"Welcome to {plan_name}!\n\n"
                f"👇 Here is your exclusive invite link:\n"
                f"{invite_link}\n\n"
                f"⚠️ Do not share this link with others.",
                parse_mode="Markdown"
            )

            # Clean up
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
    app.run_polling()


if __name__ == "__main__":
    main()
