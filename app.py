from flask import Flask, request, jsonify
from flask_cors import CORS
from get_daily_forecast import get_daily_forecast

app = Flask(__name__)
CORS(app)

@app.post("/api/make_forecast")
def make_forecast():
    try:
        data = request.get_json()
        date = data.get("date")

        if not date:
            return jsonify({"error": "Date missing"}), 400

        # Вызов твоей функции, без PDF и лишнего
        num, forecast = get_daily_forecast(date)

        if not forecast:
            return jsonify({
                "forecast": {
                    "title": f"Dienas prognoze ({num})",
                    "content": "⚠️ Prognoze nav atrasta šim skaitlim."
                }
            })

        return jsonify({
            "forecast": {
                "title": forecast["title"],
                "content": forecast["content"]
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
