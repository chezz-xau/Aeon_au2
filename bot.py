from datetime import datetime
import os
import flask
from flask import Flask, request
import psycopg2
import requests

# 1. SETUP FLASK UNTUK RENDER WEB SERVICE
app_flask = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
admin_env = os.environ.get("ADMIN_ID")
ADMIN_ID = int(admin_env) if admin_env and admin_env.isdigit() else 0

DATABASE_URL = os.environ.get("DATABASE_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"


@app_flask.route("/")
def home():
  return "Bot Telegram & Neon DB Sedang Berjalan!"


# SAMBUNGAN KE NEON POSTGRESQL
def get_db_connection():
  conn = psycopg2.connect(DATABASE_URL, sslmode="require")
  return conn


# BINA TABLE DALAM POSTGRESQL
def init_db():
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS syif_petang 
                    (id SERIAL PRIMARY KEY, date TEXT)"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS overtime 
                    (id SERIAL PRIMARY KEY, date TEXT, start_time TEXT, end_time TEXT, hours REAL)"""
  )
  cursor.execute(
      """CREATE TABLE IF NOT EXISTS hari_cuti 
                    (id SERIAL PRIMARY KEY, date TEXT)"""
  )
  conn.commit()
  cursor.close()
  conn.close()


def send_message(chat_id, text):
  url = f"{TELEGRAM_API_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
  requests.post(url, json=payload)


# 2. WEBHOOK ENDPOINT
@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  update = request.get_json()
  if "message" in update:
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    # Semak Admin
    if user_id != ADMIN_ID:
      send_message(
          chat_id, "⛔ Maaf, anda tidak mempunyai kebenaran untuk menggunakan bot ini."
      )
      return "OK", 200

    parts = text.split(" ")
    command = parts[0]
    args = parts[1:]

    conn = get_db_connection()
    cursor = conn.cursor()

    if command == "/start":
      reply = (
          "👋 Selamat datang ke **Aeonbot - Sistem Rekod Staf**!\n\n"
          "Sila guna arahan berikut:\n"
          "👉 `/syif YYYY-MM-DD` - Rekod Syif Petang\n"
          "👉 `/ot YYYY-MM-DD HH:MM HH:MM` - Rekod OT\n"
          "👉 `/cuti YYYY-MM-DD` - Rekod Hari Cuti\n"
          "📊 `/laporan` - Lihat Laporan & ID\n"
          "🗑️ `/delsyif [ID]`, `/delot [ID]`, `/delcuti [ID]` - Padam rekod"
      )
      send_message(chat_id, reply)

    elif command == "/syif":
      if not args:
        send_message(
            chat_id, "⚠️ Sila masukkan tarikh.\nFormat: `/syif 2026-11-12`"
        )
      else:
        date_str = args[0]
        try:
          datetime.strptime(date_str, "%Y-%m-%d")
          cursor.execute(
              "INSERT INTO syif_petang (date) VALUES (%s)", (date_str,)
          )
          conn.commit()
          send_message(
              chat_id,
              f"✅ Berjaya rekod **Syif Petang** untuk tarikh: `{date_str}`",
          )
        except ValueError:
          send_message(
              chat_id, "❌ Format tarikh salah. Gunakan format `YYYY-MM-DD`."
          )

    elif command == "/ot":
      if len(args) < 3:
        send_message(
            chat_id,
            "⚠️ Maklumat tidak lengkap.\nFormat: `/ot 2026-11-12 17:00 21:00`",
        )
      else:
        date_str, start_str, end_str = args[0], args[1], args[2]
        try:
          datetime.strptime(date_str, "%Y-%m-%d")
          t1 = datetime.strptime(start_str, "%H:%M")
          t2 = datetime.strptime(end_str, "%H:%M")
          diff = t2 - t1
          hours = diff.total_seconds() / 3600
          if hours < 0:
            hours += 24
          cursor.execute(
              "INSERT INTO overtime (date, start_time, end_time, hours) VALUES"
              " (%s, %s, %s, %s)",
              (date_str, start_str, end_str, hours),
          )
          conn.commit()
          send_message(
              chat_id,
              f"✅ Berjaya rekod **OT**:\n📅 Tarikh:"
              f" `{date_str}`\n⏰ Masa: `{start_str} - {end_str}`\n⏱️ Tempoh:"
              f" `{hours:.1f} Jam`",
          )
        except ValueError:
          send_message(
              chat_id,
              "❌ Format masa atau tarikh salah. Gunakan `YYYY-MM-DD` dan `HH:MM`.",
          )

    elif command == "/cuti":
      if not args:
        send_message(
            chat_id, "⚠️ Sila masukkan tarikh.\nFormat: `/cuti 2026-11-15`"
        )
      else:
        date_str = args[0]
        try:
          datetime.strptime(date_str, "%Y-%m-%d")
          cursor.execute(
              "INSERT INTO hari_cuti (date) VALUES (%s)", (date_str,)
          )
          conn.commit()
          send_message(
              chat_id,
              f"✅ Berjaya rekod **Kerja Hari Cuti** untuk tarikh: `{date_str}`",
          )
        except ValueError:
          send_message(
              chat_id, "❌ Format tarikh salah. Gunakan format `YYYY-MM-DD`."
          )

    elif command in ["/delsyif", "/delot", "/delcuti"]:
      if not args:
        send_message(
            chat_id, f"⚠️ Sila masukkan ID untuk dipadam. Contoh: `{command} 1`"
        )
      else:
        record_id = args[0]
        if command == "/delsyif":
          cursor.execute("DELETE FROM syif_petang WHERE id = %s", (record_id,))
          msg_del = f"🗑️ Rekod Syif Petang dengan ID `{record_id}` telah dipadam."
        elif command == "/delot":
          cursor.execute("DELETE FROM overtime WHERE id = %s", (record_id,))
          msg_del = f"🗑️ Rekod OT dengan ID `{record_id}` telah dipadam."
        elif command == "/delcuti":
          cursor.execute("DELETE FROM hari_cuti WHERE id = %s", (record_id,))
          msg_del = f"🗑️ Rekod Hari Cuti dengan ID `{record_id}` telah dipadam."

        conn.commit()
        send_message(chat_id, msg_del)

    elif command == "/laporan":
      cursor.execute("SELECT id, date FROM syif_petang ORDER BY date ASC")
      syif_rows = cursor.fetchall()
      total_syif = len(syif_rows)

      cursor.execute(
          "SELECT id, date, start_time, end_time, hours FROM overtime ORDER"
          " BY date ASC"
      )
      ot_rows = cursor.fetchall()
      total_ot_hours = sum(row[4] for row in ot_rows)

      cursor.execute("SELECT id, date FROM hari_cuti ORDER BY date ASC")
      cuti_rows = cursor.fetchall()
      total_cuti = len(cuti_rows)

      report = "📊 **LAPORAN REKOD STAF** 📊\n----------------------------------\n\n"
      report += f"🌙 **Syif Petang:** `{total_syif} Hari`\n"
      for r in syif_rows:
        report += f"   • [ID: {r[0]}] `{r[1]}`\n"
      report += (
          f"\n⏱️ **Overtime (OT):** `{total_ot_hours:.1f} Jam Keseluruhan`\n"
      )
      for r in ot_rows:
        report += (
            f"   • [ID: {r[0]}] `{r[1]}` ({r[2]} - {r[3]}) ➔ **{r[4]:.1f} jam**\n"
        )
      report += f"\n🏖️ **Kerja Hari Cuti:** `{total_cuti} Hari`\n"
      for r in cuti_rows:
        report += f"   • [ID: {r[0]}] `{r[1]}`\n"

      send_message(chat_id, report)

    cursor.close()
    conn.close()
  return "OK", 200


def set_webhook():
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if render_url:
    webhook_url = f"{render_url}/{TOKEN}"
    requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")


if __name__ == "__main__":
  init_db()
  set_webhook()
  port = int(os.environ.get("PORT", 10000))
  app_flask.run(host="0.0.0.0", port=port)
