# make_saderiba_pdf.py
import sys, os, requests
from io import BytesIO
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ====== ENV ======
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
if not SUPABASE_URL:
    raise SystemExit("❌ SUPABASE_URL is missing")

STORE = f"{SUPABASE_URL}/storage/v1/object/public/astro-forecasts/saderiba"
API_BASE = "http://localhost:3333"  # ← при необходимости поправим порт

# ====== PDF / FONT ======
CUSTOM_PAGE = (1920, 1080)
BG = HexColor("#0b1f1c")
FONT_PATH = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))

# ====== HELPERS ======
def reduce22(n: int) -> int:
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n

def reduce9(n: int) -> int:
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n or 1

def get_bytes(url: str) -> bytes:
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"GET failed: {url} -> {r.status_code}")
    return r.content

def draw_full(c: canvas.Canvas, img_bytes: bytes):
    W, H = CUSTOM_PAGE
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    reader = ImageReader(BytesIO(img_bytes))
    c.drawImage(reader, 0, 0, width=W, height=H,
                preserveAspectRatio=False, mask="auto")
    c.showPage()

def draw_overlay_with_title(
    c: canvas.Canvas, bg_bytes: bytes, overlay_bytes: bytes, title: str = "",
    overlay_scale: float = 0.85, y_shift: float = 0, x_shift: float = 0, title_size: int = 38
):
    W, H = CUSTOM_PAGE
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    bg = ImageReader(BytesIO(bg_bytes))
    c.drawImage(bg, 0, 0, width=W, height=H, preserveAspectRatio=False, mask="auto")

    ov = ImageReader(BytesIO(overlay_bytes))
    iw, ih = ov.getSize()
    aspect = iw / ih
    target_w = W * overlay_scale
    target_h = target_w / aspect
    if target_h > H * overlay_scale:
        target_h = H * overlay_scale
        target_w = target_h * aspect

    x = (W - target_w) / 2 + x_shift
    y = (H - target_h) / 2 + y_shift

    c.drawImage(ov, x, y, width=target_w, height=target_h,
                preserveAspectRatio=True, mask="auto")

    if title:
        c.setFont("DejaVu", title_size)
        c.setFillColor("white")
        c.drawCentredString(W / 2, H - 70, title)

    c.showPage()

def draw_triangle_in_slot(c: canvas.Canvas, bg_bytes: bytes, tri_bytes: bytes,
                          slot_x: int, slot_y: int, slot_w: int):
    """Рисуем PNG треугольника в 'светлое поле слева'."""
    W, H = CUSTOM_PAGE
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    bg = ImageReader(BytesIO(bg_bytes))
    c.drawImage(bg, 0, 0, width=W, height=H,
                preserveAspectRatio=False, mask="auto")

    tri = ImageReader(BytesIO(tri_bytes))
    iw, ih = tri.getSize()
    aspect = iw / ih
    target_w = slot_w
    target_h = target_w / aspect
    x = slot_x
    y = slot_y
    c.drawImage(tri, x, y, width=target_w, height=target_h,
                preserveAspectRatio=True, mask="auto")

    c.showPage()

# координаты "светлого поля" для acX.jpg
TRI_X = 80   # левее
TRI_Y = 250
TRI_W = 650

def clamp_attiecibas_index(n: int) -> int:
    return max(3, min(22, n))

# ====== MAIN ======
if len(sys.argv) < 3:
    print("❌ Usage: python make_saderiba_pdf.py DD.MM.YYYY DD.MM.YYYY")
    sys.exit(1)

date_you = sys.argv[1]
date_partner = sys.argv[2]

out_pdf = f"D:/Work/ASTRO/PDFS/SADERIBA_{date_you.replace('.','')}_{date_partner.replace('.','')}.pdf"
c = canvas.Canvas(out_pdf, pagesize=CUSTOM_PAGE)

# --- 1–2 ---
for i in (1, 2):
    img = get_bytes(f"{STORE}/saderiba_main/{i}.jpg")
    draw_full(c, img)

# --- 3. твоя звезда ---
bg3 = get_bytes(f"{STORE}/saderiba_main/3.jpg")
star_you = get_bytes(f"{API_BASE}/api/star/saderiba?date={date_you}&format=png")
draw_overlay_with_title(c, bg3, star_you, "TAVA ZVAIGZNE", 0.78, 0, 0, 42)

# --- 4. партнёр ---
star_partner = get_bytes(f"{API_BASE}/api/star/saderiba?date={date_partner}&format=png")
draw_overlay_with_title(c, bg3, star_partner, "PARTNERA ZVAIGZNE", 0.78, 0, 0, 42)

# --- 5. твой треугольник ---
tri_you = get_bytes(f"{API_BASE}/api/triangle/saderiba?date={date_you}&format=png")
resp_you = requests.get(f"{API_BASE}/api/triangle/saderiba?date={date_you}&format=json")
nums_you = resp_you.json()
top_you = clamp_attiecibas_index(reduce22(int(nums_you.get("top", 3))))
bg_ac = get_bytes(f"{STORE}/attiecibas/ac{top_you}.jpg")
draw_triangle_in_slot(c, bg_ac, tri_you, TRI_X, TRI_Y, TRI_W)

# --- 6–7 ---
for suffix in ("_1", "_2"):
    img = get_bytes(f"{STORE}/attiecibas/ac{top_you}{suffix}.jpg")
    draw_full(c, img)

# --- 8. партнёрский треугольник ---
tri_partner = get_bytes(f"{API_BASE}/api/triangle/saderiba?date={date_partner}&format=png")
resp_partner = requests.get(f"{API_BASE}/api/triangle/saderiba?date={date_partner}&format=json")
nums_partner = resp_partner.json()
top_partner = clamp_attiecibas_index(reduce22(int(nums_partner.get("top", 3))))
bg_acp = get_bytes(f"{STORE}/attiecibas/ac{top_partner}p.jpg")
draw_triangle_in_slot(c, bg_acp, tri_partner, TRI_X, TRI_Y, TRI_W)

# --- 9–10 ---
for suffix in ("_1", "_2"):
    img = get_bytes(f"{STORE}/attiecibas/ac{top_partner}{suffix}.jpg")
    draw_full(c, img)

# --- 11. совместная звезда ---
bg4 = get_bytes(f"{STORE}/saderiba_main/4-sad_zv.jpg")
star_sum = get_bytes(
    f"{API_BASE}/api/star/saderibasum?dateA={date_you}&dateB={date_partner}&format=png"
)
draw_overlay_with_title(c, bg4, star_sum, "", 0.50, -10, -555, 0)

# --- 12–15 ---
sum_nums = requests.get(
    f"{API_BASE}/api/star/saderibasum?dateA={date_you}&dateB={date_partner}&format=json"
).json()

lm = reduce22(int(sum_nums.get("ml", 3)))
top_c = reduce22(int(sum_nums.get("top", 3)))
rm = reduce22(int(sum_nums.get("mr", 3)))
rb_val = int(sum_nums.get("right") or sum_nums.get("br") or sum_nums.get("mb", 1))
rc_idx = reduce9(rb_val)

slides = [
    (f"{STORE}/saderiba/sac{lm}.jpg"),
    (f"{STORE}/stridi/stc{top_c}.jpg"),
    (f"{STORE}/bizness/bc{rm}.jpg"),
    (f"{STORE}/rekomendacijas/rc{rc_idx}.jpg"),
]

for slide in slides:
    img = get_bytes(slide)
    draw_full(c, img)

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
msg["Subject"] = "Numeroloģiskā Saderības analīze"

body = """
<html>
  <body style="font-family: DejaVu Sans, Arial, sans-serif; color:#000; line-height:1.6; font-size:14px;">
    <p>Labdien,</p>

    <p>Paldies, ka izvēlējies numeroloģisko <b>Saderības analīzi</b> – tā ir iespēja dziļāk izprast attiecības un cilvēku savstarpējo mijiedarbību. 
    Skati to zemāk pielikumā.</p>

    <p>Ir svarīgi atcerēties, ka nav “labu” vai “sliktu” saderību. 
    Katrā attiecībā galvenais ir vēlme vienam otru iepazīt, pieņemt un cienīt. 
    Kad spējam saprast otra skatījumu uz dzīvi, respektēt viņa viedokli un īpašo pasaules redzējumu, 
    tad jebkura savienība var kļūt par vislabāk saderīgo.</p>

    <p>Šī analīze palīdz atklāt ne tikai līdzības, bet arī atšķirības, 
    kas patiesībā ir spēka avots, jo tās iemāca mūs paplašināt savas robežas, 
    būt elastīgākiem un mācīties vienam no otra.</p>

    <p>Lai šī informācija Tev kalpo kā ceļvedis, stiprinot attiecības un veidojot savienību, 
    kurā ir vairāk izpratnes, cieņas un harmonijas.</p>

    <p>No sirds pateicos par uzticību un to, ka ļāvi man būt daļai no šī nozīmīgā izziņas ceļa.</p>

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