from datetime import datetime
import logging
import os
import sqlite3
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# 1. SETUP FLASK UNTUK RENDER WEB SERVICE
app_flask = Flask(__name__)


@app_flask.route("/")
def home():
  return "Bot Telegram Sedang Berjalan!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app_flask.run(host="0.0.0.0", port=port, use_reloader=False)


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
admin_env = os.environ.get("ADMIN_ID")
ADMIN_ID = int(admin_env) if admin_env and admin_env.isdigit() else 0

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def check_admin(update: Update) -> bool:
  user_id = update.effective_user.id
  if user_id != ADMIN_ID:
    await update.message.reply_text(
        "⛔ Maaf, anda tidak mempunyai kebenaran untuk menggunakan bot ini."
    )
    return False
  return True


def init_db():
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS syif_petang 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT)"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS overtime 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, start_time TEXT, end_time TEXT, hours REAL)"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS hari_cuti 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT)"""
  )
  conn.commit()
  conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  await update.message.reply_text(
      "👋 Selamat datang ke **Aeonbot - Sistem Rekod Staf**!\n\n"
      "Sila guna arahan berikut:\n"
      "👉 `/syif YYYY-MM-DD` - Rekod Syif Petang\n"
      "👉 `/ot YYYY-MM-DD HH:MM HH:MM` - Rekod OT\n"
      "👉 `/cuti YYYY-MM-DD` - Rekod Hari Cuti\n"
      "📊 `/laporan` - Lihat Laporan & ID\n"
      "🗑️ `/delsyif [ID]`, `/delot [ID]`, `/delcuti [ID]` - Padam rekod",
      parse_mode="Markdown",
  )


async def record_syif(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if not context.args:
    await update.message.reply_text(
        "⚠️ Sila masukkan tarikh.\nFormat: `/syif 2026-11-12`",
        parse_mode="Markdown",
    )
    return
  date_str = context.args[0]
  try:
    datetime.strptime(date_str, "%Y-%m-%d")
  except ValueError:
    await update.message.reply_text(
        "❌ Format tarikh salah. Gunakan format `YYYY-MM-DD`.",
        parse_mode="Markdown",
    )
    return
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute("INSERT INTO syif_petang (date) VALUES (?)", (date_str,))
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"✅ Berjaya rekod **Syif Petang** untuk tarikh: `{date_str}`",
      parse_mode="Markdown",
  )


async def record_ot(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if len(context.args) < 3:
    await update.message.reply_text(
        "⚠️ Maklumat tidak lengkap.\nFormat: `/ot 2026-11-12 17:00 21:00`",
        parse_mode="Markdown",
    )
    return
  date_str = context.args[0]
  start_str = context.args[1]
  end_str = context.args[2]
  try:
    datetime.strptime(date_str, "%Y-%m-%d")
    t1 = datetime.strptime(start_str, "%H:%M")
    t2 = datetime.strptime(end_str, "%H:%M")
    diff = t2 - t1
    hours = diff.total_seconds() / 3600
    if hours < 0:
      hours += 24
  except ValueError:
    await update.message.reply_text(
        "❌ Format masa atau tarikh salah. Gunakan `YYYY-MM-DD` dan `HH:MM`.",
        parse_mode="Markdown",
    )
    return
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO overtime (date, start_time, end_time, hours) VALUES (?, ?,"
      " ?, ?)",
      (date_str, start_str, end_str, hours),
  )
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"✅ Berjaya rekod **OT**:\n📅 Tarikh: `{date_str}`\n⏰ Masa: `{start_str}"
      f" - {end_str}`\n⏱️ Tempoh: `{hours:.1f} Jam`",
      parse_mode="Markdown",
  )


async def record_cuti(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if not context.args:
    await update.message.reply_text(
        "⚠️ Sila masukkan tarikh.\nFormat: `/cuti 2026-11-15`",
        parse_mode="Markdown",
    )
    return
  date_str = context.args[0]
  try:
    datetime.strptime(date_str, "%Y-%m-%d")
  except ValueError:
    await update.message.reply_text(
        "❌ Format tarikh salah. Gunakan format `YYYY-MM-DD`.",
        parse_mode="Markdown",
    )
    return
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute("INSERT INTO hari_cuti (date) VALUES (?)", (date_str,))
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"✅ Berjaya rekod **Kerja Hari Cuti** untuk tarikh: `{date_str}`",
      parse_mode="Markdown",
  )


async def delete_syif(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(
