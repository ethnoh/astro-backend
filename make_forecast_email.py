# make_forecast_email.py
import sys
import requests
import os
import random
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from collections import defaultdict

# --- Load environment ---
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Gmail config
GMAIL_USER = "evijaparnumerologiju@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Args ---
if len(sys.argv) < 3:
    print("❌ Usage: python make_forecast_email.py DD.MM.YYYY recipient@email.com")
    sys.exit(1)

birthdate = sys.argv[1]
recipient_email = sys.argv[2]

today = datetime.today()
year_now = today.year

print(f"📅 Birthdate: {birthdate}, forecast for {year_now}")
print(f"📧 Will be sent to: {recipient_email}")

# --- 1. Star image from API ---
star_url = f"http://localhost:3333/api/star?date={birthdate}&format=png"
resp = requests.get(star_url)
if resp.status_code != 200:
    raise SystemExit("❌ Failed to generate star image")
star_bytes = resp.content
star_path = f"D:/Work/ASTRO/PDFS/star_{birthdate.replace('.','')}.png"
with open(star_path, "wb") as f:
    f.write(star_bytes)

# --- 2. Calculate gada_cipars & menesa_cipars ---
d, m, y = map(int, birthdate.split("."))
gada_cipars = d + m + (year_now % 10)  # simplified, adjust if needed
while gada_cipars > 22:
    gada_cipars = sum(map(int, str(gada_cipars)))

menesa_cipars = gada_cipars + today.month
while menesa_cipars > 22:
    menesa_cipars = sum(map(int, str(menesa_cipars)))

print(f"🔢 gada_cipars={gada_cipars}, menesa_cipars={menesa_cipars}")

# --- 3. Fetch gada image ---
gada_res = supabase.table("forecast_gada_images").select("*").eq("gada_cipars", gada_cipars).execute()
if not gada_res.data:
    raise SystemExit(f"❌ No gada_cipars {gada_cipars} found")
gada_img_url = gada_res.data[0]["image_url"]
gada_bytes = requests.get(gada_img_url).content
gada_path = f"D:/Work/ASTRO/PDFS/gada_{birthdate.replace('.','')}.png"
with open(gada_path, "wb") as f:
    f.write(gada_bytes)

# --- 4. Fetch menesa images and group by variant ---
menesa_res = supabase.table("forecast_menesa_images").select("*").eq("menesa_cipars", menesa_cipars).execute()
if not menesa_res.data:
    raise SystemExit(f"❌ No menesa_cipars {menesa_cipars} found")

# Group into main variants (1, 2, 3...) based on "variant" field like "1.1"
groups = defaultdict(list)
for item in menesa_res.data:
    variant_str = str(item["variant"])  # e.g. "1.1"
    if "." in variant_str:
        main, sub = variant_str.split(".")
    else:
        main, sub = variant_str, "0"
    groups[main].append(item)

# Pick one main variant
chosen_main = random.choice(list(groups.keys()))
chosen_items = sorted(groups[chosen_main], key=lambda x: x["variant"])

print(f"📂 Chosen menesa variant: {chosen_main} ({len(chosen_items)} images)")

menesa_paths = []
for i, item in enumerate(chosen_items, start=1):
    img_url = item["image_url"]
    img_bytes = requests.get(img_url).content
    img_path = f"D:/Work/ASTRO/PDFS/menesa_{birthdate.replace('.','')}_{chosen_main}_{i}.png"
    with open(img_path, "wb") as f:
        f.write(img_bytes)
    menesa_paths.append(img_path)

# --- 5. Compose email ---
msg = MIMEMultipart()
msg["From"] = GMAIL_USER
msg["To"] = recipient_email
msg["Subject"] = "Personalizētā astroloģijas prognoze – Jūsu zvaigzne, gada un mēneša skaitlis"

body = f"""
<p>Labdien,</p>
<p>Paldies par Jūsu interesi par astroloģiju un numeroloģiju. Kā solīts, pielikumā pievienoju Jūsu personalizēto astroloģijas analīzi.</p>
<p>Šajā epastā atradīsiet trīs daļas:</p>
<ul>
  <li>🌟 Tava Astroloģiskā Zvaigzne</li>
  <li>📅 Tava Gada Prognoze ({year_now})</li>
  <li>📆 Tava Mēneša Prognoze (variants {chosen_main})</li>
</ul>
<p>Ar sirsnīgiem sveicieniem,<br>Evija</p>
"""
msg.attach(MIMEText(body, "html", "utf-8"))

# Helper to attach files
def attach_file(msg, path, filename):
    with open(path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

# Attach star, gada, all chosen menesa images
attach_file(msg, star_path, "Tava_Astrologiska_Zvaigzne.png")
attach_file(msg, gada_path, "Tava_Gada_Prognoze.png")
for i, p in enumerate(menesa_paths, start=1):
    attach_file(msg, p, f"Tava_Menesa_Prognoze_{chosen_main}_{i}.png")

# --- 6. Send email ---
with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASS)
    server.send_message(msg)

print(f"📧 Email with attachments sent to {recipient_email}")
