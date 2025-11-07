# Telegram Forward Bot
# Single-file Python implementation (python-telegram-bot v20+)
# Features:
# - Forwards incoming channel posts to multiple destination chats (groups/channels)
# - Admin commands to add/remove/list destinations per "tenant" (seller / buyer)
# - Simple licensing: owner creates activation tokens for buyers; buyers activate and then
#   can add their own source channel and destination chats.
# - SQLite for persistence
# - Dockerfile + README notes included at bottom
#
# Requirements:
#   pip install python-telegram-bot==20.6 aiosqlite
#
# Usage:
# - Create a bot via @BotFather, get BOT_TOKEN
# - Put bot into the source channel as an administrator (so it receives channel_post updates)
# - Put bot into destination groups/channels and ensure it can send messages
# - Run the script
#
# Security notes:
# - The bot forwards any received channel_post from a registered source channel id
# - Keep your BOT_TOKEN secret
#
# ---------------------------------------------------------------------------------
# Implementation

import asyncio
import os
import secrets
import logging
import sqlite3
from typing import List, Optional
from pathlib import Path

from telegram import Update, Message, Chat
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Config
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'REPLACE_WITH_YOUR_TOKEN')
DB_PATH = os.environ.get('DB_PATH', 'forward_bot.db')
OWNER_USER_ID = int(os.environ.get('OWNER_USER_ID', '0'))  # your Telegram numeric user id as owner

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB helpers
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tenants (
        tenant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER NOT NULL,
        name TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS activations (
        token TEXT PRIMARY KEY,
        tenant_id INTEGER,
        used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        chat_title TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS destinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        chat_title TEXT
    )
    ''')
    conn.commit()
    conn.close()

def db_conn():
    return sqlite3.connect(DB_PATH)

# Tenant & activation management

def create_tenant(owner_user_id:int, name:Optional[str]=None) -> int:
    conn = db_conn(); cur = conn.cursor()
    cur.execute('INSERT INTO tenants (owner_user_id, name) VALUES (?,?)', (owner_user_id, name))
    tid = cur.lastrowid
    conn.commit(); conn.close()
    return tid

def create_activation_token(tenant_id:int) -> str:
    token = secrets.token_urlsafe(12)
    conn = db_conn(); cur = conn.cursor()
    cur.execute('INSERT INTO activations (token, tenant_id, used) VALUES (?,?,0)', (token, tenant_id))
    conn.commit(); conn.close()
    return token

def use_activation_token(token:str) -> Optional[int]:
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id, used FROM activations WHERE token=?', (token,))
    row = cur.fetchone()
    if not row:
        conn.close(); return None
    tenant_id, used = row
    if used:
        conn.close(); return None
    cur.execute('UPDATE activations SET used=1 WHERE token=?', (token,))
    conn.commit(); conn.close()
    return tenant_id

# Sources & Destinations

def add_source(tenant_id:int, chat_id:int, chat_title:str=None):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('INSERT INTO sources (tenant_id, chat_id, chat_title) VALUES (?,?,?)', (tenant_id, chat_id, chat_title))
    conn.commit(); conn.close()

def remove_source(tenant_id:int, chat_id:int):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('DELETE FROM sources WHERE tenant_id=? AND chat_id=?', (tenant_id, chat_id))
    conn.commit(); conn.close()

def get_sources_for_chat(chat_id:int) -> List[dict]:
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id, chat_id, chat_title FROM sources WHERE chat_id=?', (chat_id,))
    rows = cur.fetchall(); conn.close()
    return [{'tenant_id':r[0],'chat_id':r[1],'chat_title':r[2]} for r in rows]

def add_destination(tenant_id:int, chat_id:int, chat_title:str=None):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('INSERT INTO destinations (tenant_id, chat_id, chat_title) VALUES (?,?,?)', (tenant_id, chat_id, chat_title))
    conn.commit(); conn.close()

def remove_destination(tenant_id:int, chat_id:int):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('DELETE FROM destinations WHERE tenant_id=? AND chat_id=?', (tenant_id, chat_id))
    conn.commit(); conn.close()

def list_destinations(tenant_id:int):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT chat_id, chat_title FROM destinations WHERE tenant_id=?', (tenant_id,))
    rows = cur.fetchall(); conn.close()
    return rows

# Helper: map a source chat to tenant(s)

def get_tenant_ids_by_source(chat_id:int) -> List[int]:
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM sources WHERE chat_id=?', (chat_id,))
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]

# Bot command handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! من ربات فوروارد هستم. اگر شما مالک/فروشنده هستید از /create_tenant استفاده کنید. برای فعالسازی از /activate <token> استفاده کنید.'
    )

# Only owner creates tenant and activation tokens
async def create_tenant_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if OWNER_USER_ID and user.id != OWNER_USER_ID:
        await update.message.reply_text('فقط مالک می‌تواند تِنانت جدید ایجاد کند.')
        return
    name = ' '.join(context.args) if context.args else None
    tid = create_tenant(user.id, name)
    token = create_activation_token(tid)
    await update.message.reply_text(f'Tenant ایجاد شد. شناسه: {tid}\nتوکن فعالسازی یکبار مصرف: {token}')

async def activate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # user provides token, bot assigns tenant_id to this user by returning tenant info
    if not context.args:
        await update.message.reply_text('لطفاً توکن را بفرستید: /activate <token>')
        return
    token = context.args[0]
    tid = use_activation_token(token)
    if not tid:
        await update.message.reply_text('توکن نامعتبر یا قبلاً استفاده شده.')
        return
    # save mapping user_id -> tenant by creating a tenant-owner mapping? Simpler: create a tenant-owner record
    conn = db_conn(); cur = conn.cursor()
    cur.execute('UPDATE tenants SET owner_user_id=? WHERE tenant_id=?', (update.effective_user.id, tid))
    conn.commit(); conn.close()
    await update.message.reply_text(f'فعال شد. Tenant شما شناسه {tid} می‌باشد. حالا می‌توانید منبع و مقصدها را اضافه کنید.')

# Admin commands for tenant owners
async def add_source_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM tenants WHERE owner_user_id=?', (user.id,))
    row = cur.fetchone(); conn.close()
    if not row:
        await update.message.reply_text('شما مالکِ هیچ تِنانتی نیستید. ابتدا /activate یا از فروشنده توکن بگیرید.')
        return
    tenant_id = row[0]
    # Accept either chat_id (numeric) or invite link or channel username; we'll try to use the chat info from the message reply
    if update.message.reply_to_message and update.message.reply_to_message.forward_from_chat:
        source_chat = update.message.reply_to_message.forward_from_chat
        chat_id = source_chat.id
        title = source_chat.title or source_chat.username
    elif context.args:
        arg = context.args[0]
        # attempt to parse numeric
        try:
            chat_id = int(arg)
            title = None
        except ValueError:
            # username like @channelusername
            chat_id = None
            title = arg
    else:
        await update.message.reply_text('لطفا شناسه عددی چت یا نام کاربری کانال را بدهید یا پیام کانال را reply کنید.')
        return
    # If chat_id unknown, bot can't convert username to id without API call — ask user to forward a message from the channel to the bot
    if chat_id is None:
        await update.message.reply_text('اگر شناسه عددی ندارید، لطفاً یک پیام از کانال مبدا به این ربات فوروارد کنید و بعد دوباره /add_source را اجرا کنید.')
        return
    add_source(tenant_id, chat_id, title)
    await update.message.reply_text(f'منبع افزوده شد: {chat_id} {title or ""}')

async def add_destination_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM tenants WHERE owner_user_id=?', (user.id,))
    row = cur.fetchone(); conn.close()
    if not row:
        await update.message.reply_text('شما مالکِ هیچ تِنانتی نیستید.')
        return
    tenant_id = row[0]
    # Allow reply to message from destination chat (forwarded) or numeric id
    if update.message.reply_to_message and update.message.reply_to_message.forward_from_chat:
        dest_chat = update.message.reply_to_message.forward_from_chat
        chat_id = dest_chat.id
        title = dest_chat.title or dest_chat.username
    elif context.args:
        try:
            chat_id = int(context.args[0]); title=None
        except ValueError:
            await update.message.reply_text('لطفاً شناسه عددی چت را بفرستید یا پیامی از آن فوروارد کنید.')
            return
    else:
        await update.message.reply_text('لطفاً شناسه مقصد را بفرستید یا پیام گروه/کانال مقصد را reply کنید.')
        return
    add_destination(tenant_id, chat_id, title)
    await update.message.reply_text(f'مقصد افزوده شد: {chat_id} {title or ""}')

async def list_destinations_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM tenants WHERE owner_user_id=?', (user.id,))
    row = cur.fetchone(); conn.close()
    if not row:
        await update.message.reply_text('شما مالکِ هیچ تِنانتی نیستید.')
        return
    tenant_id = row[0]
    rows = list_destinations(tenant_id)
    if not rows:
        await update.message.reply_text('لیست مقصدها خالی است.')
        return
    text = 'مقصدها:\n' + '\n'.join([f'{r[0]} {r[1] or ""}' for r in rows])
    await update.message.reply_text(text)

async def remove_destination_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM tenants WHERE owner_user_id=?', (user.id,))
    row = cur.fetchone(); conn.close()
    if not row:
        await update.message.reply_text('شما مالکِ هیچ تِنانتی نیستید.')
        return
    tenant_id = row[0]
    if not context.args:
        await update.message.reply_text('لطفاً شناسه عددی مقصد را وارد کنید: /remove_destination <chat_id>')
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text('شناسه باید عددی باشد.')
        return
    remove_destination(tenant_id, chat_id)
    await update.message.reply_text('مقصد حذف شد اگر وجود داشت.')

# Handler for channel posts
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This is called for channel_post updates
    post = update.channel_post
    if not post:
        return
    source_chat = post.chat
    tenant_ids = get_tenant_ids_by_source(source_chat.id)
    if not tenant_ids:
        # not a registered source
        return
    # For each tenant, forward/copy to its destinations
    for tid in tenant_ids:
        dests = list_destinations(tid)
        for dest_chat_id, _ in dests:
            try:
                # Use copy_message to preserve original author and avoid 'forwarded from' header if needed
                await context.bot.copy_message(chat_id=dest_chat_id, from_chat_id=source_chat.id, message_id=post.message_id)
            except Exception as e:
                logger.exception(f'Error forwarding to {dest_chat_id}: {e}')

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception('Exception while handling an update: %s', context.error)

# Setup & run
async def main():
    init_db()
    if BOT_TOKEN == 'REPLACE_WITH_YOUR_TOKEN' or not BOT_TOKEN:
        print('Set BOT_TOKEN environment variable')
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('create_tenant', create_tenant_cmd))
    app.add_handler(CommandHandler('activate', activate_cmd))
    app.add_handler(CommandHandler('add_source', add_source_cmd))
    app.add_handler(CommandHandler('add_destination', add_destination_cmd))
    app.add_handler(CommandHandler('list_destinations', list_destinations_cmd))
    app.add_handler(CommandHandler('remove_destination', remove_destination_cmd))

    # channel_post handler
    app.add_handler(MessageHandler(filters.CHANNEL_POST, channel_post_handler))

    app.add_error_handler(error_handler)

    print('Bot started...')
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())

# ---------------------------------------------------------------------------------
# Dockerfile (put this text in Dockerfile)
#
# FROM python:3.11-slim
# WORKDIR /app
# COPY . /app
# RUN pip install --no-cache-dir python-telegram-bot==20.6 aiosqlite
# ENV BOT_TOKEN=""
# ENV OWNER_USER_ID=0
# CMD ["python","/app/Telegram_forward_bot.py"]
#
# ---------------------------------------------------------------------------------
# README / quick guide (short):
# 1) Create bot token via @BotFather and set BOT_TOKEN env var
# 2) Start the bot locally or via Docker
# 3) As owner (OWNER_USER_ID env var set to your numeric Telegram id) run /create_tenant to make a tenant
#    The bot replies with an activation token. Give that token to the buyer.
# 4) Buyer runs /activate <token> to claim the tenant. After activation, buyer becomes tenant owner.
# 5) Buyer must add the source channel: either forward a message from the source channel to this bot
#    then run /add_source (reply to the forwarded message with /add_source) OR provide numeric chat id.
# 6) Buyer adds destinations by forwarding a message from the destination group/channel to the bot
#    then replying with /add_destination. Alternatively use numeric chat ids.
# 7) When a channel_post arrives from a registered source channel the bot will copy it into each
#    destination configured for that tenant.
#
# Notes and possible improvements (you can ask me to implement any of these):
# - Web UI for buyers to manage their tenants
# - Payment gateway integration (Stripe, Zarinpal, etc.) to sell licenses automatically
# - White-labeling: allow custom bot token per tenant so each buyer gets their own bot token
# - Webhook deployment for scale
# - Better handling of private channels (need to invite bot and/or use channel admin rights)
# - Retry and backoff for failed sends, admin notifications, logs
# - More granular permissions (multiple admins per tenant)
# - UI to let buyer paste channel links and the bot resolve them to IDs automatically
#
# If you want, می‌تونم: 
# - این پروژه رو برات کامل دپلوی کنم با Docker و systemd یا سرویس ابری
# - یک پنل ساده وب برای مدیریت خریدارها و تِنانت‌ها بسازم
# - قابلیت وایت‌لبل (هر خریدار توکن خودش) اضافه کنم
#
# End of file
