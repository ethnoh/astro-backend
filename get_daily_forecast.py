import os, random, re, sys
from datetime import date, datetime
from typing import Tuple, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------- env ----------
# читает .env.local с SUPABASE_URL и ключом (SERVICE_ROLE или ANON)
load_dotenv(".env.local")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Нет SUPABASE_URL / SUPABASE_*KEY в .env.local")
    sys.exit(1)
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- numerology core ----------
def reduce22(n: int) -> int:
    """Если n > 22 — складываем цифры один раз, иначе оставляем как есть."""
    return n if n <= 22 else sum(int(c) for c in str(n))

# офсеты по годам (из правил в файлах для 2025–2026)
YEAR_OFFSETS = {2025: 9, 2026: 10}

def personal_year(b_day: int, b_month: int, target_year: int) -> int:
    """Личный год: reduce22(day' + month + offset(year))."""
    if target_year not in YEAR_OFFSETS:
        raise ValueError(f"Нет офсета для {target_year}. Добавь в YEAR_OFFSETS.")
    d = reduce22(b_day) if b_day > 22 else b_day
    return reduce22(d + b_month + YEAR_OFFSETS[target_year])

def daily_number(dob: date, target: date) -> int:
    """Дневной номер: reduce22(personalYear + month + day')."""
    py = personal_year(dob.day, dob.month, target.year)
    day_adj = reduce22(target.day) if target.day > 22 else target.day
    return reduce22(py + target.month + day_adj)

# ---------- utils ----------
def parse_date(s: str) -> date:
    """
    Парсит 'DD.MM.YYYY', 'YYYY-MM-DD' или 'DD/MM/YYYY'.
    """
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Не смог распарсить дату: {s}")

def pick_variant(rows: list) -> Optional[dict]:
    if not rows:
        return None
    # детерминированный выбор: по дню года, чтобы один и тот же запрос в день давал одинаковый текст
    today_doy = datetime.utcnow().timetuple().tm_yday
    return rows[today_doy % len(rows)]

# ---------- main ----------
def get_daily_forecast(dob_str: str, target_str: Optional[str] = None, lang: str = "lv") -> Tuple[int, Optional[dict]]:
    dob = parse_date(dob_str)
    target = parse_date(target_str) if target_str else date.today()
    num = daily_number(dob, target)

    # тянем все варианты для этого числа и языка
    res = sb.table("daily_texts").select("*").eq("lang", lang).eq("number", num).order("variant").execute()
    rows = res.data or []
    chosen = pick_variant(rows)
    return num, chosen

if __name__ == "__main__":
    # Примеры запуска:
    # python get_daily_forecast.py 01.09.1986            -> прогноз на сегодня
    # python get_daily_forecast.py 01.09.1986 18.08.2025 -> прогноз на конкретную дату
    if len(sys.argv) < 2:
        print("Использование: python get_daily_forecast.py <DOB> [DATE]\nПримеры: 01.09.1986  |  01.09.1986 18.08.2025")
        sys.exit(0)

    dob_in = sys.argv[1]
    date_in = sys.argv[2] if len(sys.argv) >= 3 else None

    try:
        num, row = get_daily_forecast(dob_in, date_in)
        print(f"\nDienas cipars: {num}")
        if row:
            print(f"\n{row['title']}\n")
            print(row['content'])
        else:
            print("⚠️ Текст для этого числа не найден в БД (проверь загрузку daily_texts).")
    except Exception as e:
        print("Ошибка:", e)
        sys.exit(1)
