import os
from datetime import date, datetime
from typing import Tuple, Optional
from supabase import create_client, Client

def _sb_client() -> Client:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)

def quick_supabase_ping():
    """
    Пытаемся одним запросом дернуть таблицу. Возвращаем (ok, payload).
    """
    try:
        sb = _sb_client()
        res = sb.table("daily_texts").select("number", count="exact").limit(1).execute()
        return True, {"count": res.count, "sample": res.data}
    except Exception as e:
        return False, {"error": str(e)}

# --- дальше твоя логика без изменений ---
YEAR_OFFSETS = {2025: 9, 2026: 10}

def reduce22(n: int) -> int:
    return n if n <= 22 else sum(int(c) for c in str(n))

def personal_year(b_day: int, b_month: int, target_year: int) -> int:
    if target_year not in YEAR_OFFSETS:
        raise ValueError(f"No offset for {target_year}")
    d = reduce22(b_day) if b_day > 22 else b_day
    return reduce22(d + b_month + YEAR_OFFSETS[target_year])

def daily_number(dob: date, target: date) -> int:
    py = personal_year(dob.day, dob.month, target.year)
    day_adj = reduce22(target.day) if target.day > 22 else target.day
    return reduce22(py + target.month + day_adj)

def parse_date(s: str) -> date:
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Bad date: {s}")

def pick_variant(rows: list) -> Optional[dict]:
    if not rows:
        return None
    doy = datetime.utcnow().timetuple().tm_yday
    return rows[doy % len(rows)]

def get_daily_forecast(dob_str: str, target_str: Optional[str] = None, lang: str = "lv") -> Tuple[int, Optional[dict]]:
    sb = _sb_client()
    dob = parse_date(dob_str)
    target = parse_date(target_str) if target_str else date.today()
    num = daily_number(dob, target)
    res = sb.table("daily_texts").select("*").eq("lang", lang).eq("number", num).order("variant").execute()
    rows = res.data or []
    return num, pick_variant(rows)
