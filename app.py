from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)

# Помощники — сокращение чисел до 22
def reduce22(n: int) -> int:
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n

# Смещения по годам (те же, что были в Next.js)
YEAR_OFFSETS = {2025: 9, 2026: 10}

def personal_year(day: int, month: int, year: int) -> int:
    offset = YEAR_OFFSETS.get(year)
    if offset is None:
        offset = 9
    d_prime = reduce22(day)
    return reduce22(d_prime + month + offset)

def daily_number(dob: datetime.date, target: datetime.date) -> int:
    py = personal_year(dob.day, dob.month, target.year)
    day_prime = reduce22(target.day)
    return reduce22(py + target.month + day_prime)

@app.route("/api/make_forecast", methods=["POST"])
def make_forecast():
    try:
        data = request.get_json()
        date_str = data.get("date")

        # поддержка разных форматов
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                dob = datetime.datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            return jsonify(error="Invalid date format. Use DD.MM.YYYY"), 400

        today = datetime.date.today()
        num = daily_number(dob, today)

        # Тестовые тексты — потом заменим на реальные из Supabase
        sample_forecasts = {
            1: "Šodien dari pirmo soli! Enerģija piemērota jauniem sākumiem.",
            2: "Lieliska diena sadarbībai un iekšējam līdzsvaram.",
            3: "Radošums plaukst — izsaki sevi brīvi.",
            4: "Koncentrējies uz struktūru un stabilitāti.",
        }
        content = sample_forecasts.get(num, f"Tava dienas enerģija ir numurs {num}.")

        return jsonify({
            "dailyNumber": num,
            "forecast": {
                "title": f"Dienas prognoze ({num})",
                "content": content
            }
        })

    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/", methods=["GET"])
def root():
    return jsonify(service="astro-backend", status="running")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
