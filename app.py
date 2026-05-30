from flask import Flask, render_template, request, jsonify
import threading
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import psycopg2
import psycopg2.extras
import serial
import serial.tools.list_ports
import re

app = Flask(__name__)

ser = None

DATABASE_URL = "postgresql://psn2_db_user:Cz3QM2YjpqHEI2hjcZ8Q6rj4VoqoWsb9@dpg-d8dd7ternols7397nn10-a.frankfurt-postgres.render.com/psn2_db"

EMAIL_EXPEDITOR = "proiectnanu2@gmail.com"
EMAIL_PAROLA = "wjtr xltv brog qvxt"
EMAIL_DESTINATAR = "proiectnanu2@gmail.com"

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS mesaje
                 (id SERIAL PRIMARY KEY, mesaj TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evenimente
                 (id SERIAL PRIMARY KEY, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS temperatura
                 (id SERIAL PRIMARY KEY, valoare FLOAT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS led
                 (id SERIAL PRIMARY KEY, stare BOOLEAN)''')
    c.execute('''INSERT INTO temperatura (valoare, timestamp)
                 SELECT 0, %s WHERE NOT EXISTS (SELECT 1 FROM temperatura)''',
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    c.execute('''INSERT INTO led (stare)
                 SELECT FALSE WHERE NOT EXISTS (SELECT 1 FROM led)''')
    conn.commit()
    conn.close()

init_db()

def conectare_arduino():
    global ser
    porturi = serial.tools.list_ports.comports()
    for port in porturi:
        try:
            ser = serial.Serial(port.device, 9600, timeout=1)
            time.sleep(2)
            print(f"Arduino conectat pe {port.device}")
            return
        except:
            continue
    print("Arduino negasit - rulam fara hardware")

def salveaza_temperatura(valoare):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE temperatura SET valoare = %s, timestamp = %s WHERE id = 1",
              (valoare, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_led_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT stare FROM led WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else False

def citire_serial():
    while True:
        try:
            if ser and ser.in_waiting:
                linie = ser.readline().decode("utf-8", errors="ignore").strip()
                print(f"Serial: {linie}")
                if "Temp:" in linie:
                    match_temp = re.search(r'Temp:\s*([\d.]+)', linie)
                    if match_temp:
                        temp = float(match_temp.group(1))
                        salveaza_temperatura(temp)
                elif "ALERTA" in linie:
                    inregistreaza_inundatie()
        except Exception as e:
            print(f"Eroare serial: {e}")
        time.sleep(0.1)

def control_led():
    stare_anterioara = None
    while True:
        try:
            stare = get_led_db()
            if stare != stare_anterioara:
                stare_anterioara = stare
                if ser:
                    ser.write(b'A' if stare else b'S')
                    print(f"LED: {'APRINS' if stare else 'STINS'}")
        except Exception as e:
            print(f"Eroare control LED: {e}")
        time.sleep(2)

def trimite_mesaje_arduino():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT MAX(id) FROM mesaje")
        row = c.fetchone()
        conn.close()
        ultim_id = row[0] if row[0] else 0
    except:
        ultim_id = 0

    while True:
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT id, mesaj FROM mesaje WHERE id > %s ORDER BY id ASC", (ultim_id,))
            rows = c.fetchall()
            conn.close()
            for row in rows:
                ultim_id = row[0]
                if ser:
                    ser.write((row[1] + "\n").encode())
                    print(f"Trimis la Arduino: {row[1]}")
        except Exception as e:
            print(f"Eroare trimitere mesaj: {e}")
        time.sleep(1)

def inregistreaza_inundatie():
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO evenimente (timestamp) VALUES (%s)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    c.execute("DELETE FROM evenimente WHERE id NOT IN (SELECT id FROM evenimente ORDER BY id DESC LIMIT 10)")
    conn.commit()
    conn.close()
    threading.Thread(target=trimite_email_inundatie, daemon=True).start()

def trimite_email_inundatie():
    try:
        msg = MIMEText(f"ATENTIE: Inundatie detectata la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}!")
        msg["Subject"] = "ALERTA INUNDATIE - PSN2"
        msg["From"] = EMAIL_EXPEDITOR
        msg["To"] = EMAIL_DESTINATAR
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_EXPEDITOR, EMAIL_PAROLA)
            server.sendmail(EMAIL_EXPEDITOR, EMAIL_DESTINATAR, msg.as_string())
    except Exception as e:
        print(f"Eroare email: {e}")

conectare_arduino()
threading.Thread(target=citire_serial, daemon=True).start()
threading.Thread(target=control_led, daemon=True).start()
threading.Thread(target=trimite_mesaje_arduino, daemon=True).start()

def get_temperatura_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT valoare FROM temperatura WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def get_mesaje_db():
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT id, mesaj, timestamp FROM mesaje ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_evenimente_db():
    conn = get_conn()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT id, timestamp FROM evenimente ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.route("/")
def index():
    return render_template("index.html",
                           temperatura=get_temperatura_db(),
                           led=get_led_db(),
                           mesaje=get_mesaje_db(),
                           evenimente=get_evenimente_db())

@app.route("/temperatura")
def temperatura():
    return jsonify({"temperatura": get_temperatura_db()})

@app.route("/led", methods=["POST"])
def led():
    data = request.get_json()
    stare = data.get("stare", False)
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE led SET stare = %s WHERE id = 1", (stare,))
    conn.commit()
    conn.close()
    return jsonify({"led": stare})

@app.route("/mesaj", methods=["POST"])
def mesaj():
    data = request.get_json()
    msg = data.get("mesaj", "").strip()
    if msg:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO mesaje (mesaj, timestamp) VALUES (%s, %s)",
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
    inregistreaza_inundatie()
    return jsonify({"evenimente": get_evenimente_db()})

@app.route("/inundatie/sterge/<int:event_id>", methods=["DELETE"])
def sterge_eveniment(event_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM evenimente WHERE id = %s", (event_id,))
    conn.commit()
    conn.close()
    return jsonify({"evenimente": get_evenimente_db()})

@app.route("/evenimente")
def get_evenimente():
    return jsonify({"evenimente": get_evenimente_db()})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)