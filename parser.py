import pdfplumber
import re

pdf_path = "pdfs/ornek.pdf"

# ==================== 1. PDF'TEN HAM SATIRLARI ÇEK ====================
raw_lines = []

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            raw_lines.extend(text.split("\n"))

# ==================== 2. SATIRLARI BİRLEŞTİR ====================
merged_lines = []
current = ""

for line in raw_lines:
    line = line.strip()
    if not line:
        continue

    # Gereksiz satırları atla
    if any(x in line for x in [
        "Splash Meet Manager",
        "Registered to",
        "TÜRKİYE SPORTİVE",
        "ANTALYA",
        "Results",
        "Points",
        "Show all"
    ]):
        continue

    # Diskalifiye ve zaman bilgisi olmayan satırları atla
    if line.startswith("DSQ") or line.startswith("SW") or "(Time" in line:
        continue

    # Event satırı geldiğinde öncekini kaydet
    if line.startswith("Event "):
        if current:
            merged_lines.append(current)
            current = ""
        merged_lines.append(line)
        continue

    # Sporcu satırı başladığında (rakamla başlıyor)
    if re.match(r"^\d+\.", line):
        if current:
            merged_lines.append(current)
        current = line
    else:
        # Devam eden satırı birleştir
        if current:
            current += " " + line

if current:
    merged_lines.append(current)

# ==================== 3. EVENT VE SPORCULARI PARSE ET ====================
results = []
current_event = None
last_event_no = None
current_age_group = None

for line in merged_lines:

    # ================= EVENT =================
    event_match = re.search(
        r"Event\s+(\d+)\s*,?\s*(Men|Boys|Women|Girls)?\s*,?\s*(.+)",
        line,
        re.IGNORECASE
    )

    if event_match:
        event_no = int(event_match.group(1))
        gender = (event_match.group(2) or "Unknown").title()
        rest = event_match.group(3).strip()

        # Aynı event tekrar gelirse atla (duplike kontrolü)
        if current_event and current_event["event"] == str(event_no) and current_event["gender"] == gender:
            continue

        # Geri giden event numaralarını atla
        if last_event_no is not None and event_no < last_event_no:
            continue
        last_event_no = event_no

        # Prelim/Final gibi bilgileri temizle
        rest = re.sub(r"\bPrelim\b|\bFinal\b", "", rest, flags=re.IGNORECASE)

        # Yaş grubu bul
        age_match = re.search(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", rest)
        age_group = age_match.group(1) if age_match else "Unknown"

        # Yaş grubunu çıkarıp kalan kısmı al (bu yarış stili)
        race = re.sub(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", "", rest).strip(" ,")

        # Bayrak yarışlarını atla (x içeren)
        if re.search(r"\bx\b|\d+\s*x\s*\d+", race, re.IGNORECASE):
            current_event = None
            continue

        current_event = {
            "event": str(event_no),
            "gender": gender,
            "race": race,
            "age_group": age_group
        }

        current_age_group = age_group

        print("\n================ NEW EVENT ================")
        print(current_event)

        continue

    # Event olmadan sporcu satırı gelirse atla
    if current_event is None:
        continue

    # ================= SOLO YAŞ SATIRI =================
    solo_age = re.fullmatch(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", line.strip())
    if solo_age:
        current_age_group = solo_age.group(1)
        continue

    # ================= SPORCU SATIRINDA YAŞ VARSA SÖK =================
    tail_age = re.search(r"(.*?)(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)\s*$", line)
    if tail_age:
        line = tail_age.group(1).strip()
        current_age_group = tail_age.group(2)

    # ================= SPORCU SATIRI =================
    # Sporcu satırı: Rakamla başlıyor VE zaman içeriyor
    if re.match(r"^\d+\.", line) and re.search(r"\d+:\d+\.\d+", line):
        event_copy = current_event.copy()
        event_copy["age_group"] = current_age_group if current_age_group else "Unknown"

        results.append((event_copy, line))

# ==================== 4. SONUÇLARI GÖSTER ====================
print("\n--- CLEAN EVENT + ATHLETE SAMPLE ---\n")
for event, line in results[-80:]:
    print(event, "=>", line)

print("\nTOTAL RESULTS:", len(results))