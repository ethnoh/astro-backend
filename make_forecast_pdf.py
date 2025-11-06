# make_forecast_pdf.py
import sys
import requests
import os
import random
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- Load environment ---
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Gmail config (App password must be in .env.local)
GMAIL_USER = "evijaparnumerologiju@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Check arguments ---
if len(sys.argv) < 3:
    print("❌ Usage: python make_forecast_pdf.py DD.MM.YYYY recipient@email.com")
    sys.exit(1)

birthdate = sys.argv[1]
recipient_email = sys.argv[2]

today = datetime.today()
year_now = today.year

print(f"📅 Birthdate: {birthdate}, forecast for {year_now}")
print(f"📧 Will be sent to: {recipient_email}")

# --- Register Unicode font ---
pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))

def draw_fullpage_image(c, img):
    """Draws an image scaled to fit the full A4 page"""
    w, h = A4
    iw, ih = img.getSize()
    aspect = iw / ih
    page_aspect = w / h

    if aspect > page_aspect:
        new_w = w
        new_h = w / aspect
        x = 0
        y = (h - new_h) / 2
    else:
        new_h = h
        new_w = h * aspect
        x = (w - new_w) / 2
        y = 0

    c.drawImage(img, x, y, width=new_w, height=new_h)

# --- 1. Generate star image ---
star_url = f"http://localhost:3333/api/star?date={birthdate}&format=png"
resp = requests.get(star_url)
if resp.status_code != 200:
    raise SystemExit("❌ Failed to generate star image")
star_img = ImageReader(BytesIO(resp.content))

# --- 2. Calculate gada_cipars & menesa_cipars ---
d, m, y = map(int, birthdate.split("."))
gada_cipars = d + m + 9
while gada_cipars > 22:
    gada_cipars = sum(map(int, str(gada_cipars)))

menesa_cipars = gada_cipars + today.month
while menesa_cipars > 22:
    menesa_cipars = sum(map(int, str(menesa_cipars)))

print(f"🔢 gada_cipars={gada_cipars}, menesa_cipars={menesa_cipars}")

# --- 3. Fetch images from Supabase ---
gada_res = supabase.table("forecast_gada_images").select("*").eq("gada_cipars", gada_cipars).execute()
if not gada_res.data:
    raise SystemExit(f"❌ No gada_cipars {gada_cipars} found")
gada_img_url = gada_res.data[0]["image_url"]
gada_img = ImageReader(BytesIO(requests.get(gada_img_url).content))

menesa_res = supabase.table("forecast_menesa_images").select("*").eq("menesa_cipars", menesa_cipars).execute()
if not menesa_res.data:
    raise SystemExit(f"❌ No menesa_cipars {menesa_cipars} found")
menesa_choice = random.choice(menesa_res.data)
menesa_img_url = menesa_choice["image_url"]
menesa_img = ImageReader(BytesIO(requests.get(menesa_img_url).content))

# --- 4. Save PDF locally ---
output_dir = r"D:/Work/ASTRO/PDFS"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"GADA PROGNOZE_{birthdate.replace('.', '')}.pdf")

c = canvas.Canvas(output_path, pagesize=A4)
w, h = A4

draw_fullpage_image(c, star_img)
c.setFont("DejaVu", 18)
c.drawCentredString(w/2, h-40, f"Tava {year_now} gada prognoze")
c.showPage()

draw_fullpage_image(c, gada_img)
c.setFont("DejaVu", 16)
c.drawCentredString(w/2, h-40, f"Gada cipars: {gada_cipars}")
c.showPage()

draw_fullpage_image(c, menesa_img)
c.setFont("DejaVu", 16)
c.drawCentredString(w/2, h-40, f"Mēneša cipars: {menesa_cipars}")
c.showPage()

c.save()
print(f"✅ PDF saved: {output_path}")

# --- 5. Send email with PDF ---
msg = MIMEMultipart()
msg["From"] = GMAIL_USER
msg["To"] = recipient_email
msg["Subject"] = "Personalizētā astroloģijas prognoze – Jūsu zvaigzne, gada un mēneša skaitlis"

body = """
<p>Labdien,</p>
<p>Paldies par Jūsu interesi par astroloģiju un numeroloģiju. Kā solīts, pielikumā pievienoju Jūsu personalizēto astroloģijas analīzi PDF formātā.</p>
<p>Šajā dokumentā atradīsiet:</p>
<ul>
  <li>🌟 Jūsu astroloģisko zvaigzni</li>
  <li>📅 Gada skaitļa prognozi</li>
  <li>📆 Mēneša skaitļa analīzi</li>
</ul>
<p>Ar sirsnīgiem sveicieniem,<br>Evija</p>
"""
msg.attach(MIMEText(body, "html", "utf-8"))

with open(output_path, "rb") as f:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(f.read())
encoders.encode_base64(part)
part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(output_path)}"')
msg.attach(part)

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASS)
    server.send_message(msg)

print(f"📧 Email sent to {recipient_email}")
