# make_berns_pdf.py
# Generate "Bērna personības analīze" PDF (1920x1080)
# Usage: python make_berns_pdf.py DD.MM.YYYY

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

# =========================
# ENV & SUPABASE
# =========================
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("❌ SUPABASE_URL / KEY missing in .env.local")

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Public storage base
STORE = f"{SUPABASE_URL}/storage/v1/object/public/astro-forecasts/berns"

# Font (Latvian letters)
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")))

# =========================
# LAYOUT TUNING (easy to tweak)
# =========================
# Star (slide 3): scale to 72% of page width (auto height), then shift a bit lower (5% of H)
STAR_MAX_W_PCT = 0.72
STAR_MAX_H_PCT = 0.72
STAR_SHIFT_DOWN_PCT = 0.05  # move a bit below center (positive value moves DOWN)

# Triangle (slide 4): fit into a left box and center there
# Box approx covers the light triangle region on your background.
TRI_BOX_X_PCT = 0.003   # левее
TRI_BOX_Y_PCT = 0.11   # ниже
TRI_BOX_W_PCT = 0.44   # чуть шире
TRI_BOX_H_PCT = 0.72   # чуть выше


# API endpoints (transparent PNGs)
API_BASE = "http://localhost:3333"
STAR_URL_TPL = API_BASE + "/api/star/berns?date={date}&format=png"
TRI_URL_TPL  = API_BASE + "/api/triangle/berns?date={date}&format=png"


# =========================
# NUMERICS (same as Personība)
# =========================
def reduce22(n: int) -> int:
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n

def year_reduced(y: int) -> int:
    return reduce22(sum(int(d) for d in str(y)))

def personiba_numbers(d: int, m: int, y: int):
    d1 = reduce22(d)
    yR = year_reduced(y)
    # bottomRight
    br = reduce22(d1 + m)
    # bottomLeft cascade
    a1 = d1
    a2 = m
    a3 = yR
    a4 = reduce22(a1 + a2 + a3)
    a5 = reduce22(a1 + a2 + a3 + a4)
    bl = reduce22(a1 + a5)
    # Middles
    mr = reduce22(d1 + br)
    ml = reduce22(d1 + bl)
    mb = reduce22(br + bl)
    return OrderedDict(top=d1, ml=ml, mr=mr, left=bl, mb=mb, right=br)

# =========================
# HELPERS
# =========================
def get(url: str) -> bytes:
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"GET failed: {url} -> {r.status_code}")
    return r.content

def draw_full_bg(c: canvas.Canvas, W: float, H: float, img_bytes: bytes, title: str = ""):
    green_bg = HexColor("#0b1f1c")
    c.setFillColor(green_bg)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    if title:
        c.setFont("DejaVu", 20)
        c.setFillColor("white")
        c.drawCentredString(W / 2, H - 40, title)

    bg = ImageReader(BytesIO(img_bytes))
    c.drawImage(bg, 0, 0, width=W, height=H, preserveAspectRatio=False, mask="auto")

def draw_overlay_fit_center(c: canvas.Canvas, W: float, H: float, overlay_bytes: bytes,
                            box_x: float, box_y: float, box_w: float, box_h: float):
    """Fit overlay into (box_x,box_y,box_w,box_h), keep aspect, center."""
    ov = ImageReader(BytesIO(overlay_bytes))
    iw, ih = ov.getSize()
    aspect = iw / ih

    # fit into box
    tgt_w = box_w
    tgt_h = tgt_w / aspect
    if tgt_h > box_h:
        tgt_h = box_h
        tgt_w = tgt_h * aspect

    x = box_x + (box_w - tgt_w) / 2
    y = box_y + (box_h - tgt_h) / 2
    c.drawImage(ov, x, y, width=tgt_w, height=tgt_h, preserveAspectRatio=True, mask="auto")

def draw_slide_bg_then_overlay(c: canvas.Canvas, W: float, H: float,
                               bg_bytes: bytes, overlay_bytes: bytes,
                               box_rel=None, shift_down_rel=0.0):
    """Draw background full, then overlay either centered in page or in a relative box."""
    draw_full_bg(c, W, H, bg_bytes)

    if box_rel is None:
        # Center in page (with optional vertical shift down)
        ov = ImageReader(BytesIO(overlay_bytes))
        iw, ih = ov.getSize()
        aspect = iw / ih

        max_w = W * STAR_MAX_W_PCT
        max_h = H * STAR_MAX_H_PCT
        tgt_w = max_w
        tgt_h = tgt_w / aspect
        if tgt_h > max_h:
            tgt_h = max_h
            tgt_w = tgt_h * aspect

        x = (W - tgt_w) / 2
        y = (H - tgt_h) / 2 - H * shift_down_rel  # positive → lower
        c.drawImage(ov, x, y, width=tgt_w, height=tgt_h, preserveAspectRatio=True, mask="auto")
    else:
        bx, by, bw, bh = box_rel
        draw_overlay_fit_center(c, W, H, overlay_bytes,
                                box_x=W*bx, box_y=H*by, box_w=W*bw, box_h=H*bh)

    c.showPage()

def add_group_slides(c: canvas.Canvas, W: float, H: float, n: int):
    """Append 4 slides for number n (skip missing silently)."""
    n = reduce22(int(n))
    base = f"{STORE}/group/{n}"
    names = [f"c{n}.jpg", f"c{n}_1.jpg", f"c{n}_2.jpg", f"c{n}_3.jpg"]

    for fname in names:
        url = f"{base}/{fname}"
        try:
            img = get(url)
        except Exception:
            print(f"⚠️  Skip missing: {url}")
            continue

        # Draw and go to next page
        draw_full_bg(c, W, H, img_bytes=img)
        c.showPage()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python make_berns_pdf.py DD.MM.YYYY")
        sys.exit(1)

    birthdate = sys.argv[1]
    d, m, y = map(int, birthdate.split("."))

    # Prepare PDF
    CUSTOM_PAGE = (1920, 1080)
    W, H = CUSTOM_PAGE
    out_pdf = f"D:/Work/ASTRO/PDFS/BERNA_PERSONIBA_{birthdate.replace('.','')}.pdf"
    c = canvas.Canvas(out_pdf, pagesize=CUSTOM_PAGE)

    # ---- 1. Slide: 1-berna_main.jpg
    img1 = get(f"{STORE}/main/1-berna_main.jpg")
    draw_full_bg(c, W, H, img1); c.showPage()

    # ---- 2. Slide: 2-berna_main2.jpg
    img2 = get(f"{STORE}/main/2-berna_main2.jpg")
    draw_full_bg(c, W, H, img2); c.showPage()

    # ---- 3. Slide: background + STAR (transparent) a bit lower than center
    bg3 = get(f"{STORE}/main/3-berna_zvaigzne.jpg")
    star_png = get(STAR_URL_TPL.format(date=birthdate))
    draw_slide_bg_then_overlay(
        c, W, H,
        bg_bytes=bg3,
        overlay_bytes=star_png,
        box_rel=None,
        shift_down_rel=STAR_SHIFT_DOWN_PCT
    )

    # ---- 4. Slide: background + TRIANGLE (transparent) centered inside light triangle
    bg4 = get(f"{STORE}/main/4-berna_trissturis.jpg")
    tri_png = get(TRI_URL_TPL.format(date=birthdate))
    draw_slide_bg_then_overlay(
        c, W, H,
        bg_bytes=bg4,
        overlay_bytes=tri_png,
        box_rel=(TRI_BOX_X_PCT, TRI_BOX_Y_PCT, TRI_BOX_W_PCT, TRI_BOX_H_PCT)
    )

    # ---- Triangles math
    nums = personiba_numbers(d, m, y)

# --- 5–28: slides by unique numbers (avoid duplicates) ---
seq = ["top", "ml", "mr", "left", "mb", "right"]
seen = set()
for key in seq:
    val = int(nums[key])
    if val in seen:
        print(f"⚠️ Skip duplicate number {val} ({key})")
        continue
    seen.add(val)
    add_group_slides(c, W, H, val)


# ---- 29. Final slide: berna_last.jpg
last = get(f"{STORE}/main/berna_last.jpg")
draw_full_bg(c, W, H, last); c.showPage()

# === SAVE AND SEND EMAIL ===
c.save()
print(f"✅ PDF saved: {out_pdf}")

# === Email setup ===
GMAIL_USER = "evijaparnumerologiju@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
recipient_email = input("📧 Enter recipient email: ").strip()
if not recipient_email:
    print("⚠️ No recipient email provided. Skipping email send.")
    sys.exit(0)


from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import smtplib

msg = MIMEMultipart()
msg["From"] = GMAIL_USER
msg["To"] = recipient_email
msg["Subject"] = "Numeroloģiskā Bērna personības analīze"

body = """
<html>
  <body style="font-family: DejaVu Sans, Arial, sans-serif; color:#000; line-height:1.6; font-size:14px;">
    <p>Labdien,</p>

    <p>Paldies, ka izvēlējies <b>Bērna personības analīzi</b>. Skati to zemāk pielikumā.</p>

    <p>Katrs bērns nāk pasaulē ar savu raksturu, talantiem un potenciālu.
    Jo dziļāk mēs spējam ieraudzīt, kas viņā mīt, jo vieglāk ir sniegt viņam atbalstu,
    palīdzēt atklāt stiprās puses un radīt vidi, kurā viņš var augt laimīgs un pārliecināts par sevi.</p>

    <p>Šī analīze ir kā ceļvedis, kas atklāj bērna personības īpašības un viņa iekšējo spēku.
    Tā palīdz labāk saprast, kā uzrunāt, motivēt un atbalstīt viņu ikdienā, lai viņš varētu
    attīstīt savus talantus un justies pieņemts tieši tāds, kāds viņš ir.</p>

    <p>No sirds pateicos par uzticību un to, ka ļāvi man būt daļai no šī
    skaistā sava bērna izzināšanas ceļojuma!</p>

    <p>Ar pateicību un sirsnīgiem sveicieniem,<br>
    <b>Evija</b></p>
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

