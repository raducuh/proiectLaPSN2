from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

led_stare = False
temperatura_curenta = 25.0

DATABASE = "psn2.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS mesaje
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  mesaj TEXT,
                  timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evenimente
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

EMAIL_EXPEDITOR = "proiectnanu2@gmail.com"
EMAIL_PAROLA = "wjtr xltv brog qvxt"
EMAIL_DESTINATAR = "proiectnanu2@gmail.com"

def simuleaza_temperatura():
    global temperatura_curenta
    while True:
        temperatura_curenta = round(20 + random.uniform(0, 15), 1)
        time.sleep(3)

t = threading.Thread(target=simuleaza_temperatura, daemon=True)
t.start()

def trimite_email_inundatie():
    try:
        msg = MIMEText(f"ATENTIE: Inundatie detectata la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}!")
        msg["Subject"] = "ALERTA INUNDATIE - PSN2"
        msg["From"] = EMAIL_EXPEDITOR
        msg["To"] = EMAIL_DESTINATAR
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_EXPEDITOR, EMAIL_PAROLA)
            server.sendmail(EMAIL_EXPEDITOR, EMAIL_DESTINATAR, msg.as_string())
        return True
    except Exception as e:
        print(f"Eroare email: {e}")
        return False

def get_mesaje_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, mesaj, timestamp FROM mesaje ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "mesaj": r[1], "timestamp": r[2]} for r in rows]

def get_evenimente_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, timestamp FROM evenimente ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "timestamp": r[1]} for r in rows]

@app.route("/")
def index():
    return render_template("index.html",
                           temperatura=temperatura_curenta,
                           led=led_stare,
                           mesaje=get_mesaje_db(),
                           evenimente=get_evenimente_db())

@app.route("/temperatura")
def temperatura():
    return jsonify({"temperatura": temperatura_curenta})

@app.route("/led", methods=["POST"])
def led():
    global led_stare
    data = request.get_json()
    led_stare = data.get("stare", False)
    return jsonify({"led": led_stare})

@app.route("/mesaj", methods=["POST"])
def mesaj():
    data = request.get_json()
    msg = data.get("mesaj", "").strip()
    if msg:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO mesaje (mesaj, timestamp) VALUES (?, ?)",
                  (msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("DELETE FROM mesaje WHERE id NOT IN (SELECT id FROM mesaje ORDER BY id DESC LIMIT 10)")
        conn.commit()
        conn.close()
    return jsonify({"mesaje": get_mesaje_db()})

@app.route("/mesaje")
def get_mesaje():
    return jsonify({"mesaje": get_mesaje_db()})

@app.route("/inundatie", methods=["POST"])
def inundatie():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO evenimente (timestamp) VALUES (?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    c.execute("DELETE FROM evenimente WHERE id NOT IN (SELECT id FROM evenimente ORDER BY id DESC LIMIT 10)")
    conn.commit()
    conn.close()
    threading.Thread(target=trimite_email_inundatie, daemon=True).start()
    return jsonify({"evenimente": get_evenimente_db()})

@app.route("/inundatie/sterge/<int:event_id>", methods=["DELETE"])
def sterge_eveniment(event_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM evenimente WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return jsonify({"evenimente": get_evenimente_db()})

@app.route("/evenimente")
def get_evenimente():
    return jsonify({"evenimente": get_evenimente_db()})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)