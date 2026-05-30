from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

led_stare = False
temperatura_curenta = 25.0
mesaje = []
evenimente_inundatie = []

EMAIL_EXPEDITOR = "proiectnanu2@gmail.com"
EMAIL_PAROLA = "wjtr xltv brog qvxt"
EMAIL_DESTINATAR = "proiectnanu2@gmail.com"  # schimba cu emailul tau real

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

@app.route("/")
def index():
    return render_template("index.html",
                           temperatura=temperatura_curenta,
                           led=led_stare,
                           mesaje=mesaje,
                           evenimente=evenimente_inundatie)

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
    global mesaje
    data = request.get_json()
    msg = data.get("mesaj", "").strip()
    if msg:
        mesaje.append(msg)
        if len(mesaje) > 10:
            mesaje.pop(0)
    return jsonify({"mesaje": mesaje})

@app.route("/mesaje")
def get_mesaje():
    return jsonify({"mesaje": mesaje})

@app.route("/inundatie", methods=["POST"])
def inundatie():
    global evenimente_inundatie
    eveniment = {
        "id": len(evenimente_inundatie) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    evenimente_inundatie.append(eveniment)
    if len(evenimente_inundatie) > 10:
        evenimente_inundatie.pop(0)
    threading.Thread(target=trimite_email_inundatie, daemon=True).start()
    return jsonify({"evenimente": evenimente_inundatie})

@app.route("/inundatie/sterge/<int:event_id>", methods=["DELETE"])
def sterge_eveniment(event_id):
    global evenimente_inundatie
    evenimente_inundatie = [e for e in evenimente_inundatie if e["id"] != event_id]
    return jsonify({"evenimente": evenimente_inundatie})

@app.route("/evenimente")
def get_evenimente():
    return jsonify({"evenimente": evenimente_inundatie})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)