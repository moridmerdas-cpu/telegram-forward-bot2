import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- تنظیمات اصلی ----------
BOT_TOKEN = "BOT_TOKEN"
OWNER_USER_ID = OWNER_ID  # آیدی عددی خودت
tenants = {}  # برای مدیریت مشتری‌ها و کانال‌هایشون

# ---------- دستورات مالک ----------
async def create_tenant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_USER_ID:
        await update.message.reply_text("شما اجازه‌ی این کار را ندارید ❌")
        return

    if len(context.args) < 1:
        await update.message.reply_text("مثال: /create_tenant ali")
        return

    tenant_name = context.args[0]
    tenants[tenant_name] = {"sources": [], "destinations": []}
    await update.message.reply_text(f"مستأجر '{tenant_name}' ساخته شد ✅")

async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال: /add_source ali")
        return

    tenant_name = context.args[0]
    chat_id = update.effective_chat.id

    if tenant_name in tenants:
        tenants[tenant_name]["sources"].append(chat_id)
        await update.message.reply_text(f"✅ منبع به '{tenant_name}' اضافه شد.")
    else:
        await update.message.reply_text("❌ همچین مستأجری وجود ندارد.")

async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال: /add_destination ali")
        return

    tenant_name = context.args[0]
    chat_id = update.ef_
