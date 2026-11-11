from datetime import datetime
import logging
import os
import sqlite3
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 1. SETUP FLASK UNTUK PATUHI SYARAT WEB SERVICE RENDER
app_flask = Flask(__name__)


@app_flask.route("/")
def home():
  return "Bot Telegram Sedang Berjalan!"


def run_flask():
  # Render akan beri port secara automatik, default ke 10000 jika tiada
  port = int(os.environ.get("PORT", 10000))
  app_flask.run(host="0.0.0.0", port=port)


# 2. AMBIL KUNCI RAHSIA DARI RENDER ENVIRONMENT VARIABLES
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
admin_env = os.environ.get("ADMIN_ID")
ADMIN_ID = int(admin_env) if admin_env and admin_env.isdigit() else 0

# Konfigurasi Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# 3. FUNGSI SEMAKAN ADMIN
async def check_admin(update: Update) -> bool:
  user_id = update.effective_user.id
  if user_id != ADMIN_ID:
    await update.message.reply_text(
        "⛔ Maaf, anda tidak mempunyai kebenaran untuk menggunakan bot ini."
    )
    return False
  return True


# 4. SETUP DATABASE SQLITE
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


# 5. REKOD SYIF PETANG (/syif YYYY-MM-DD)
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


# 6. REKOD OT (/ot YYYY-MM-DD HH:MM HH:MM)
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


# 7. REKOD HARI CUTI (/cuti YYYY-MM-DD)
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


# 8. FUNGSI DELETE REKOD
async def delete_syif(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if not context.args:
    await update.message.reply_text(
        "⚠️ Sila masukkan ID.\nFormat: `/delsyif [ID]`", parse_mode="Markdown"
    )
    return
  record_id = context.args[0]
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM syif_petang WHERE id = ?", (record_id,))
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"🗑️ Rekod Syif Petang dengan ID `{record_id}` telah dipadam.",
      parse_mode="Markdown",
  )


async def delete_ot(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if not context.args:
    await update.message.reply_text(
        "⚠️ Sila masukkan ID.\nFormat: `/delot [ID]`", parse_mode="Markdown"
    )
    return
  record_id = context.args[0]
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM overtime WHERE id = ?", (record_id,))
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"🗑️ Rekod OT dengan ID `{record_id}` telah dipadam.",
      parse_mode="Markdown",
  )


async def delete_cuti(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return
  if not context.args:
    await update.message.reply_text(
        "⚠️ Sila masukkan ID.\nFormat: `/delcuti [ID]`", parse_mode="Markdown"
    )
    return
  record_id = context.args[0]
  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM hari_cuti WHERE id = ?", (record_id,))
  conn.commit()
  conn.close()
  await update.message.reply_text(
      f"🗑️ Rekod Hari Cuti dengan ID `{record_id}` telah dipadam.",
      parse_mode="Markdown",
  )


# 9. FUNGSI LAPORAN DENGAN PAPARAN ID (/laporan)
async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not await check_admin(update):
    return

  conn = sqlite3.connect("staff_record.db")
  cursor = conn.cursor()

  cursor.execute("SELECT id, date FROM syif_petang ORDER BY date ASC")
  syif_rows = cursor.fetchall()
  total_syif = len(syif_rows)

  cursor.execute(
      "SELECT id, date, start_time, end_time, hours FROM overtime ORDER BY"
      " date ASC"
  )
  ot_rows = cursor.fetchall()
  total_ot_hours = sum(row[4] for row in ot_rows)

  cursor.execute("SELECT id, date FROM hari_cuti ORDER BY date ASC")
  cuti_rows = cursor.fetchall()
  total_cuti = len(cuti_rows)

  conn.close()

  report = "📊 **LAPORAN REKOD STAF** 📊\n"
  report += "----------------------------------\n\n"

  report += f"🌙 **Syif Petang:** `{total_syif} Hari`\n"
  if syif_rows:
    for row in syif_rows:
      report += f"   • [ID: {row[0]}] `{row[1]}`\n"
  else:
    report += "   • Tiada rekod.\n"
  report += "\n"

  report += f"⏱️ **Overtime (OT):** `{total_ot_hours:.1f} Jam Keseluruhan`\n"
  if ot_rows:
    for row in ot_rows:
      report += f"   • [ID: {row[0]}] `{row[1]}` ({row[2]} - {row[3]}) ➔ **{row[4]:.1f} jam**\n"
  else:
    report += "   • Tiada rekod OT.\n"
  report += "\n"

  report += f"🏖️ **Kerja Hari Cuti:** `{total_cuti} Hari`\n"
  if cuti_rows:
    for row in cuti_rows:
      report += f"   • [ID: {row[0]}] `{row[1]}`\n"
  else:
    report += "   • Tiada rekod.\n"

  await update.message.reply_text(report, parse_mode="Markdown")


# 10. MAIN FUNCTION
def main():
  if not TOKEN:
    print("Ralat: TELEGRAM_BOT_TOKEN tidak dijumpai!")
    return

  # Jalankan Flask dalam latar belakang (background thread) supaya Render detect port
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  init_db()
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("syif", record_syif))
  app.add_handler(CommandHandler("ot", record_ot))
  app.add_handler(CommandHandler("cuti", record_cuti))
  app.add_handler(CommandHandler("delsyif", delete_syif))
  app.add_handler(CommandHandler("delot", delete_ot))
  app.add_handler(CommandHandler("delcuti", delete_cuti))
  app.add_handler(CommandHandler("laporan", generate_report))

  print("Bot dan pelayan web Flask sedang berjalan...")
  app.run_polling()


if __name__ == "__main__":
  main()

