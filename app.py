from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from get_daily_forecast import get_daily_forecast, quick_supabase_ping

app = Flask(__name__)
CORS(app)

@app.get("/debug/env")
def debug_env():
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    sk  = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return jsonify({
        "url": url,
        # маскируем ключ
        "service_role_key_preview": f"{sk[:8]}...{sk[-4:]}" if sk else None
    })

@app.get("/debug/ping")
def debug_ping():
    ok, payload = quick_supabase_ping()
    return (jsonify(payload), 200 if ok else 500)

@app.post("/api/make_forecast")
def make_forecast():
    data = request.get_json(silent=True) or {}
    dob = str(data.get("date", "")).strip()
    if not dob:
        return jsonify({"error": "date is required"}), 400
    try:
        num, row = get_daily_forecast(dob, lang="lv")
        if not row:
            return jsonify({"error": "no_text", "dailyNumber": num}), 404
        return jsonify({
            "dailyNumber": num,
            "forecast": {"title": row["title"], "content": row["content"]}
        })
    except Exception as e:
        return jsonify({"error": "server", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
