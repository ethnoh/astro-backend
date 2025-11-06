# forecast_menesa_images.py
import os, re
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service role key required
BUCKET_NAME = "astro-forecasts"
LOCAL_FOLDER = r"D:\Work\ASTRO\DOCS\veikts\prognozes\MENESA CIPARS"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("❌ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not found in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# File name examples:
# mc10v1.jpg   → menesa_cipars=10, variant="1"
# mc10v1.1.jpg → menesa_cipars=10, variant="1.1"
rx = re.compile(r"^mc(\d{1,2})v([\d\.]+)\.jpe?g$", re.I)

for name in os.listdir(LOCAL_FOLDER):
    m = rx.match(name)
    if not m:
        continue

    menesa_cipars = int(m.group(1))
    variant = m.group(2)  # keep as string ("1", "1.1", "2.3", ...)

    file_path = os.path.join(LOCAL_FOLDER, name)
    storage_path = f"menesa/{name}"

    # Upload to Supabase Storage
    with open(file_path, "rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            f,
            {"content-type": "image/jpeg", "upsert": "true"}
        )

    # Get public URL
    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    # Insert record into table
    supabase.table("forecast_menesa_images").insert({
        "menesa_cipars": menesa_cipars,
        "variant": variant,  # now string, supports "1.1"
        "image_url": public_url
    }).execute()

    print(f"✅ menesa {menesa_cipars} v{variant} → {public_url}")

print("🎉 All menesa files uploaded.")
