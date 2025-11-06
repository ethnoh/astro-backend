from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.post("/api/make_personiba")
def make_personiba():
    data = request.get_json()
    date = data.get("date")
    email = data.get("email")
    subprocess.run(["python3", "make_personiba_pdf.py", date, email])
    return jsonify({"status": "ok"})

@app.post("/api/make_forecast")
def make_forecast():
    data = request.get_json()
    date = data.get("date")
    email = data.get("email")
    subprocess.run(["python3", "make_forecast_pdf_full.py", date, email])
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
