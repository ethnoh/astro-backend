# forecast_gada_images.py
import os, re
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service role
BUCKET_NAME = "astro-forecasts"
LOCAL_FOLDER = r"D:\Work\ASTRO\DOCS\veikts\prognozes\GADA CIPARS"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("❌ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY не найдены в .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# убедимся, что имена gc1.jpg..gc22.jpg
rx = re.compile(r"^gc([1-9]|1\d|2[0-2])\.jpe?g$", re.I)

for name in os.listdir(LOCAL_FOLDER):
    if not rx.match(name): 
        continue

    gada_cipars = int(rx.match(name).group(1))
    path = os.path.join(LOCAL_FOLDER, name)
    storage_path = f"gada/{name}"

    with open(path, "rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            f,
            {"content-type": "image/jpeg", "upsert": "true"}  # 👈 строка, не bool
        )

    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    # upsert по gada_cipars (добавь уникальный индекс один раз в БД: ALTER TABLE ... ADD CONSTRAINT uq_gada UNIQUE(gada_cipars);)
    supabase.table("forecast_gada_images").upsert(
        {"gada_cipars": gada_cipars, "image_url": public_url},
        on_conflict="gada_cipars"
    ).execute()

    print(f"✅ gada {gada_cipars} → {public_url}")

print("🎉 Готово.")
