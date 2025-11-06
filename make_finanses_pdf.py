# make_finanses_pdf.py
import sys, os, requests
from io import BytesIO
from datetime import datetime
from collections import OrderedDict
from dotenv import load_dotenv
from supabase import create_client, Client
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === ENV & SUPABASE ===
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("❌ Missing SUPABASE_URL or SUPABASE_KEY")

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

STORE = f"{SUPABASE_URL}/storage/v1/object/public/astro-forecasts/finanses"
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")))

# === HELPERS ===
def reduce22(n: int) -> int:
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n

def year_reduced(y: int) -> int:
    return reduce22(sum(int(d) for d in str(y)))

def get(url: str) -> bytes:
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"GET failed: {url} -> {r.status_code}")
    return r.content

def draw_page(c: canvas.Canvas, title: str, img_bytes: bytes, is_star=False):
    W, H = width, height
    green_bg = HexColor("#0b1f1c")
    c.setFillColor(green_bg)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    reader = ImageReader(BytesIO(img_bytes))
    iw, ih = reader.getSize()
    aspect = iw / ih

    # --- звезда ---
    if is_star:
        target_w = W * 0.85
        target_h = target_w / aspect
        if target_h > H * 0.85:
            target_h = H * 0.85
            target_w = target_h * aspect
        x = (W - target_w) / 2
        y = (H - target_h) / 2 + 20
        c.drawImage(reader, x, y, width=target_w, height=target_h,
                    preserveAspectRatio=True, mask="auto")

        c.setFont("DejaVu", 38)
        c.setFillColor("white")
        c.drawCentredString(W / 2, H - 80, "Tava numeroloģiskā zvaigzne")

    # --- треугольники (у них есть title) ---
    elif title:
        target_w = W * 0.85
        target_h = target_w / aspect
        if target_h > H * 0.75:
            target_h = H * 0.75
            target_w = target_h * aspect
        x = (W - target_w) / 2
        y = (H - target_h) / 2 - 40
        c.drawImage(reader, x, y, width=target_w, height=target_h,
                    preserveAspectRatio=True, mask="auto")

        c.setFont("DejaVu", 46)
        c.setFillColor("white")
        for i, line in enumerate(title.split("\n")):
            y_pos = H - 120 - (i * 55)
            c.drawCentredString(W / 2, y_pos, line)

    # --- остальные страницы ---
    else:
        c.drawImage(reader, 0, 0, width=W, height=H,
                    preserveAspectRatio=False, mask="auto")

    c.showPage()


def uniq_keep_order(nums):
    seen = set()
    out = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out

def tri_order(nums: dict):
    # верхняя → средняя левая → средняя правая → нижняя левая → нижняя средняя → нижняя правая
    return uniq_keep_order([nums["top"], nums["ml"], nums["mr"], nums["left"], nums["mb"], nums["right"]])

# === TRIANGLE CALC ===
def finanses_numbers(d: int, m: int, y: int):
    yR = year_reduced(y)
    inner = reduce22(d + m + yR)
    top = yR
    right = reduce22(yR + inner)
    left = reduce22(yR + m)
    mr = reduce22(top + right)
    ml = reduce22(top + left)
    mb = reduce22(right + left)
    return OrderedDict(top=top, right=right, left=left, mr=mr, ml=ml, mb=mb)

# === MAIN ===
if len(sys.argv) < 2:
    print("❌ Usage: python make_finanses_pdf.py DD.MM.YYYY")
    sys.exit(1)

birthdate = sys.argv[1]
d, m, y = map(int, birthdate.split("."))

CUSTOM_PAGE = (1920, 1080)
out_pdf = f"D:/Work/ASTRO/PDFS/FINANSES_REALIZACIJA_{birthdate.replace('.','')}.pdf"
c = canvas.Canvas(out_pdf, pagesize=CUSTOM_PAGE)
width, height = CUSTOM_PAGE

# 1–3 MAIN IMAGES
for i in (1, 2, 3):
    img = get(f"{STORE}/main/{i}.jpg")
    draw_page(c, "", img)

# 4 STAR
star_png = get(f"http://localhost:3333/api/star?date={birthdate}&format=png")
draw_page(c, "Tava numeroloģiskā zvaigzne", star_png, is_star=True)

# 5 DZC (day number)
day_reduced = reduce22(d)
img = get(f"{STORE}/dzimta/dzc{day_reduced}.jpg")
draw_page(c, "", img)

# 6 TRIANGLE
tri_fin = get(f"http://localhost:3333/api/triangle/finanses?date={birthdate}&format=png")
draw_page(c, "FINANSES UN REALIZĀCIJA\nTRIJSTŪRIS", tri_fin)

# 7 trisstura_apraksts
img = get(f"{STORE}/main/trisstura_apraksts.jpg")
draw_page(c, "", img)

# 8–13 frcX.jpg by triangle order
fin_nums = finanses_numbers(d, m, y)
order_nums = tri_order(fin_nums)
for n in order_nums:
    if n == 1:
        continue  # frc1.jpg не существует
    img = get(f"{STORE}/finanses/frc{n}.jpg")
    draw_page(c, "", img)

# 14 last.jpg + overlay text "PARAUGS"
img = get(f"{STORE}/main/last.jpg")
reader = ImageReader(BytesIO(img))
W, H = width, height

# рисуем фон
green_bg = HexColor("#0b1f1c")
c.setFillColor(green_bg)
c.rect(0, 0, W, H, fill=1, stroke=0)
c.drawImage(reader, 0, 0, width=W, height=H, preserveAspectRatio=False, mask="auto")

# добавляем надпись
c.setFont("DejaVu", 150)
c.setFillColor(HexColor("#ff4c4c"))
c.saveState()
c.translate(W / 2, H / 2)
c.rotate(25)
c.setFillAlpha(0.25)
c.drawCentredString(0, 0, "PARAUGS")
c.restoreState()

c.showPage()

# === SAVE AND SEND EMAIL ===
c.save()
print(f"✅ PDF saved: {out_pdf}")

# === Email setup ===
GMAIL_USER = "evijaparnumerologiju@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
recipient_email = input("📧 Enter recipient email: ")

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import smtplib

msg = MIMEMultipart()
msg["From"] = GMAIL_USER
msg["To"] = recipient_email
msg["Subject"] = "Finanšu un realizācijas ceļvedis"

body = """
<html>
  <body style="font-family: DejaVu Sans, Arial, sans-serif; color:#000; line-height:1.6; font-size:14px;">
    <p>Labdien,</p>

    <p>Paldies, ka izvēlējies <b>Finanšu un realizācijas ceļvedi</b>! Skati to zemāk pielikumā.</p>

    <p>Nauda un pašrealizācija ir cieši saistītas ar mūsu iekšējo potenciālu. 
    Kad izproti savus talantus un dzīves uzdevumus, kļūst vieglāk pieņemt apzinātus lēmumus, 
    kas ved pie stabilitātes, harmonijas un piepildījuma.</p>

    <p>Šis ceļvedis parāda, kā izmantot savas stiprās puses, 
    lai veidotu ne tikai drošu pamatu ikdienai, bet arī dzīvi, 
    kas atspoguļo Tavu patieso būtību.</p>

    <p>Lai šī informācija Tevi iedvesmo drosmīgi virzīties uz priekšu, 
    izmantot savus resursus gudri un atklāt jaunas iespējas, 
    kas ļaus realizēt Tavus mērķus un sapņus.</p>

    <p>Atceries – finanses ir tikai viens posms no kopējā Tava potenciāla. 
    Ja vēlies izzināt sevi plašāk un no dažādiem aspektiem, 
    ieskaties sadaļā <b>“Personības analīze”</b>.</p>

    <p>No sirds pateicos par uzticību un to, ka ļāvi man būt līdzās šajā nozīmīgajā ceļā.</p>

    <p>Ar sirsnīgiem sveicieniem,<br><b>Evija</b></p>
  </body>
</html>
"""

msg.attach(MIMEText(body, "html", "utf-8"))

with open(out_pdf, "rb") as f:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(f.read())
encoders.encode_base64(part)
part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(out_pdf)}"')
msg.attach(part)

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASS)
    server.send_message(msg)

print(f"📧 Email with PDF sent to {recipient_email}")
