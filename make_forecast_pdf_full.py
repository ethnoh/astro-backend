import sys, os, random, requests, smtplib
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from collections import defaultdict
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# === Load env ===
load_dotenv(".env.local")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GMAIL_USER = "evijaparnumerologiju@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Helpers ===
def reduce_22(num: int) -> int:
    while num > 22:
        num = sum(map(int, str(num)))
    return num

# Register DejaVu font for Latvian characters
script_dir = os.path.dirname(__file__)
font_path = os.path.join(script_dir, "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVu", font_path))

# === Args ===
if len(sys.argv) < 3:
    print("❌ Usage: python make_forecast_pdf_full.py DD.MM.YYYY recipient@email.com")
    sys.exit(1)

birthdate = sys.argv[1]
recipient_email = sys.argv[2]
today = datetime.today()
year_now = today.year

print(f"📅 Birthdate: {birthdate}, forecast for {year_now}")
print(f"📧 Will be sent to: {recipient_email}")

# === Calculate gada cipars ===
d, m, y = map(int, birthdate.split("."))
year_sum = sum(map(int, str(year_now)))
gada_cipars = reduce_22(d + m + year_sum)

print(f"🧮 Gada cipars formula: {d} + {m} + {year_sum} = {gada_cipars}")

# === Prepare PDF ===
pdf_path = f"D:/Work/ASTRO/PDFS/GADA_PROGNOZE_{birthdate.replace('.','')}_{year_now}.pdf"
CUSTOM_PAGE = (1920, 1080)
c = canvas.Canvas(pdf_path, pagesize=CUSTOM_PAGE)
width, height = CUSTOM_PAGE
green_bg = HexColor("#0b1f1c")

# === Draw page ===
def draw_page(title, image_bytes, is_star=False):
    W, H = width, height
    c.setFillColor(green_bg)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    reader = ImageReader(BytesIO(image_bytes))
    iw, ih = reader.getSize()
    aspect = iw / ih

    # фон
    if is_star:
        target_w = W * 0.85
        target_h = target_w / aspect
        if target_h > H * 0.85:
            target_h = H * 0.85
            target_w = target_h * aspect
        x = (W - target_w) / 2
        y = (H - target_h) / 2
        c.drawImage(reader, x, y, width=target_w, height=target_h,
                    preserveAspectRatio=True, mask="auto")
    else:
        c.drawImage(reader, 0, 0, width=W, height=H,
                    preserveAspectRatio=False, mask="auto")

    # текст поверх картинки
    if title:
        c.setFont("DejaVu", 40)
        c.setFillColor("white")
        c.drawCentredString(W / 2, H - 70, title)

    c.showPage()

# === 1. Star image ===
star_url = f"http://localhost:3333/api/star?date={birthdate}&format=png"
resp = requests.get(star_url)
if resp.status_code != 200:
    raise SystemExit("❌ Failed to generate star image")
draw_page("Tava numeroloģiskā zvaigzne", resp.content, is_star=True)

# === 2. Gada cipars page ===
gada_res = supabase.table("forecast_gada_images").select("*").eq("gada_cipars", gada_cipars).execute()
if not gada_res.data:
    raise SystemExit(f"❌ gada_cipars {gada_cipars} not found")
gada_img_url = gada_res.data[0]["image_url"]
gada_bytes = requests.get(gada_img_url).content
draw_page("", gada_bytes)

# === 3. Mēneša cipari pages ===
month_names = [
    "JANVĀRIS", "FEBRUĀRIS", "MARTS", "APRĪLIS", "MAIJS", "JŪNIJS",
    "JŪLIJS", "AUGUSTS", "SEPTEMBRIS", "OKTOBRIS", "NOVEMBRIS", "DECEMBRIS"
]

for month_num, month_name in enumerate(month_names, start=1):
    menesa_cipars = reduce_22(gada_cipars + month_num)
    menesa_res = supabase.table("forecast_menesa_images").select("*").eq("menesa_cipars", menesa_cipars).execute()
    if not menesa_res.data:
        print(f"⚠️ No data for mēneša cipars {menesa_cipars}")
        continue

    groups = defaultdict(list)
    for item in menesa_res.data:
        variant_str = str(item["variant"])
        main = variant_str.split(".")[0]
        groups[main].append(item)

    chosen_main = random.choice(list(groups.keys()))
    chosen_items = sorted(groups[chosen_main], key=lambda x: x["variant"])

    print(f"📂 {month_name}: cipars={menesa_cipars}, variant={chosen_main}, slides={len(chosen_items)}")

    for item in chosen_items:
        img_bytes = requests.get(item["image_url"]).content
        # теперь название месяца поверх слайда
        draw_page(month_name, img_bytes)


# === Save PDF ===
c.save()
print(f"✅ PDF saved: {pdf_path}")

# === Send email with PDF ===
msg = MIMEMultipart()
msg["From"] = GMAIL_USER
msg["To"] = recipient_email
msg["Subject"] = "Tava Gada prognoze"

body = """
<html>
  <body style="font-family: DejaVu Sans, Arial, sans-serif; color:#000; line-height:1.6;">
    <p>Paldies, ka izvēlējies Gada prognozi! Skati to zemāk pielikumā.</p>
    <p>Katrs gads atver jaunas durvis – tas nes līdzi gan izaicinājumus, gan iespējas.
    Zinot savus ritmus un galvenos akcentus, Tu vari veidot gudrāku ikdienu,
    pieņemt apzinātākus lēmumus un virzīties uz priekšu saskaņā ar savu potenciālu.
    Gada prognoze palīdz ieraudzīt, kad ir piemērotākais laiks rīcībai, kad – atpūtai,
    un kā vislabāk izmantot savu enerģiju, lai gads kļūtu piepildīts un harmonisks.</p>

    <p>Gudri plānojot, Tu vari atvērt ceļu, kurā pilnībā izmanto savus talantus un iespējas.
    Šī prognoze lai kalpo kā atbalsts, lai Tu spētu šo gadu padarīt par soli tuvāk
    saviem sapņiem un mērķiem.</p>

    <p>No sirds pateicos par uzticību!</p>
    <p>Ar sirsnīgiem sveicieniem,<br><b>Evija</b></p>
  </body>
</html>
"""
msg.attach(MIMEText(body, "html", "utf-8"))


with open(pdf_path, "rb") as f:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(f.read())
encoders.encode_base64(part)
part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(pdf_path)}"')
msg.attach(part)

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASS)
    server.send_message(msg)

print(f"📧 Email with PDF sent to {recipient_email}")
