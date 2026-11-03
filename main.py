import re
import os


# ─────────────────────────────────────────────
# PDF OKUMA
# ─────────────────────────────────────────────

def read_pdf_lines(pdf_path):
    import pdfplumber
    raw_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page_num in range(total):
            if page_num % 10 == 0:
                print(f"   Sayfa {page_num+1}/{total} okunuyor...")
            try:
                text = pdf.pages[page_num].extract_text()
                if text:
                    raw_lines.extend(text.split("\n"))
            except Exception:
                continue
    print(f"   Sayfa {total}/{total} tamamlandı.\n")
    return raw_lines


# ─────────────────────────────────────────────
# FORMAT TESPİTİ
# ─────────────────────────────────────────────

def detect_format(raw_lines):
    """
    Standart:  'Event N' ile başlar (Antalya/İzmir)
    Gelişim:   'Yarış N' + 'ULUSAL GELİŞİM' içerir (Giresun)
    SEM:       'SPORCU EĞİTİM MERKEZLERİ' içerir (Samsun SEM Finali)
    """
    text_head = "\n".join(raw_lines[:60]).upper()
    if "SPORCU EĞİTİM MERKEZLERİ" in text_head or "SEM FİNAL" in text_head or "SEM FINAL" in text_head:
        return "sem"
    if "ULUSAL GELİŞİM" in text_head or "GELİŞİM LİGİ" in text_head or "GELİŞİM PROJESİ" in text_head:
        return "gelisim"
    for line in raw_lines[:80]:
        if re.search(r"^Event\s+\d+", line.strip(), re.I):
            return "standart"
        if re.search(r"^Yarış\s+\d+", line.strip(), re.I):
            return "gelisim"
    return "standart"


# ─────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────

def time_to_seconds(t):
    try:
        if ":" in t:
            m, s = t.split(":")
            return int(m) * 60 + float(s)
        return float(t)
    except:
        return 9999


def normalize(text):
    # Virgülü kaldır (Giresun formatı: "Beren, DİNÇ" → "beren dinç")
    text = text.replace(",", " ")
    # Fazla boşlukları temizle
    text = re.sub(r"\s+", " ", text).strip()
    for a, b in [("İ","i"),("I","i"),("ı","i"),("Ğ","g"),("ğ","g"),
                 ("Ü","u"),("ü","u"),("Ş","s"),("ş","s"),("Ö","o"),("ö","o"),("Ç","c"),("ç","c")]:
        text = text.replace(a, b)
    return text.lower()


# ─────────────────────────────────────────────
# STANDART PARSER (Antalya / İzmir formatı)
# ─────────────────────────────────────────────

def parse_standart(raw_lines):
    results = []
    current_event = None
    current_age_group = None
    current_round = "Prelim"
    relay_rank = "?"
    relay_club = ""
    relay_time = ""
    last_rank = 0

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        if any(x in line for x in ["Splash Meet Manager","Registered to","TÜRKİYE SPORTİVE","ANTALYA","Points","Show all"]):
            continue
        if line.startswith(("DSQ","SW")) or "(Time" in line:
            continue

        # Round tespiti
        if "Results" in line:
            if "Final" in line:
                current_round = "Final"
            elif "Prelim" in line:
                current_round = "Prelim"
            else:
                current_round = ""
            continue

        final_only = re.fullmatch(r"Final\s*([A-D]?)", line, re.I)
        if final_only:
            letter = final_only.group(1)
            current_round = f"Final {letter}" if letter else "Final"
            continue

        if re.fullmatch(r"Prelim", line, re.I):
            current_round = "Prelim"
            continue

        # Event
        event_match = re.search(r"Event\s+(\d+)\s*,?\s*(Men|Boys|Women|Girls)?\s*,?\s*(.+)", line, re.I)
        if event_match:
            event_no = event_match.group(1)
            gender = (event_match.group(2) or "Unknown").title()
            rest = event_match.group(3).strip()

            if re.search(r"\bPrelim\b", rest, re.I):
                current_round = "Prelim"
            elif re.search(r"\bFinal\b", rest, re.I):
                current_round = "Final"

            rest = re.sub(r"\b(Prelim|Final\s*[A-D]?)\b", "", rest, flags=re.I).strip()
            age_match = re.search(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", rest)
            age_group = age_match.group(1) if age_match else "Unknown"
            race = re.sub(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", "", rest).strip(" ,")
            is_relay = bool(re.search(r"\b\d+\s*x\s*\d+", race, re.I))

            current_event = {"event": event_no, "gender": gender, "race": race,
                             "age_group": age_group, "is_relay": is_relay}
            current_age_group = age_group
            last_rank = 0
            if is_relay:
                relay_rank = "?"; relay_club = ""; relay_time = ""
            continue

        if current_event is None:
            continue

        if re.fullmatch(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", line):
            current_age_group = line
            continue

        # Relay
        if current_event.get("is_relay"):
            club_match = re.match(r"^(\d+)\.\s+(.+?)\s*(\d+:\d+\.\d+|\d+\.\d+)\s*\d*\s*$", line)
            if club_match:
                relay_rank = club_match.group(1)
                relay_time = club_match.group(3)
                club_raw = club_match.group(2).strip()
                cut = len(club_raw)
                for sw in ["Kulübü","Kulubu"]:
                    idx = club_raw.find(sw)
                    if idx != -1:
                        cut = idx + len(sw); break
                relay_club = club_raw[:cut].strip()
                continue

            relay_athletes = re.findall(
                r"([A-ZÇĞİÖŞÜa-zçğıöşü][A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)\s+(\d{2})\s+([\d:.]+(?:\s+[\d:.]+)*)",
                line)
            for name_r, year_r, _ in relay_athletes:
                name_r = name_r.strip()
                if len(name_r) < 4 or not re.search(r"[A-ZÇĞİÖŞÜa-z]", name_r):
                    continue
                results.append({"event": current_event.copy(), "rank": relay_rank,
                                 "name": name_r, "birth_year": year_r, "club": relay_club,
                                 "time": relay_time, "age_group": current_age_group, "round": current_round})
            continue

        # Bireysel — sıralı
        athlete_match = re.match(r"^(\d+)\.\s+(.+?)\s+(\d{2})\s+(.+?)\s+(\d+:\d+\.\d+|\d+\.\d+)(?:\s|$)", line)
        if athlete_match:
            rank = athlete_match.group(1)
            last_rank = int(rank)
            results.append({"event": current_event.copy(), "rank": rank,
                             "name": athlete_match.group(2).strip(), "birth_year": athlete_match.group(3),
                             "club": athlete_match.group(4).strip(), "time": athlete_match.group(5),
                             "age_group": current_age_group, "round": current_round})
            continue

        # Bireysel — sırasız (eşit süre)
        no_rank = re.match(r"^([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)\s+(\d{2})\s+(.+?)\s+(\d+:\d+\.\d+|\d+\.\d+)(?:\s|$)", line)
        if no_rank and not current_event.get("is_relay"):
            results.append({"event": current_event.copy(), "rank": str(last_rank + 1),
                             "name": no_rank.group(1).strip(), "birth_year": no_rank.group(2),
                             "club": no_rank.group(3).strip(), "time": no_rank.group(4),
                             "age_group": current_age_group, "round": current_round})

    return results


# ─────────────────────────────────────────────
# GELİŞİM LİGİ PARSER (Giresun formatı)
# ─────────────────────────────────────────────

def parse_gelisim(raw_lines):
    """
    Bireysel: Baraj satırı varsa ekle, rank='Katılım Barajını Geçti'
              Yaş alt grubu ("10 yaş", "11 yaş") ayrı satırdan okunur
    Bayrak:   Süreye göre sırala, rank=1,2,3...
    """
    results = []
    current_event    = None
    current_age_group = None   # event'in genel yaş grubu
    current_age_sub  = None    # "10 yaş", "11 yaş", "12 yaş" alt grubu
    in_relay = False

    relay_entries  = []
    relay_club     = ""
    relay_time     = ""
    relay_athletes = []
    pending        = None

    def flush_relay():
        nonlocal relay_entries, relay_club, relay_time, relay_athletes
        if relay_club and relay_athletes:
            relay_entries.append((relay_club, time_to_seconds(relay_time), relay_time, relay_athletes[:]))
        if relay_entries:
            for rank_i, (club, _, t, athletes) in enumerate(sorted(relay_entries, key=lambda x: x[1]), 1):
                for ath in athletes:
                    results.append({
                        "event":      current_event.copy(),
                        "rank":       str(rank_i),
                        "name":       ath["name"],
                        "birth_year": ath["birth_year"],
                        "club":       club,
                        "time":       t,
                        "age_group":  current_age_sub or current_age_group,
                        "round":      ""
                    })
        relay_entries = []; relay_club = ""; relay_time = ""; relay_athletes = []

    SKIP = ["Puanlar:", "AQUA", "Zaman  Derece", "Zaman Derece", "YB Zaman",
            "TÜRKİYE YÜZME FEDERASYONU 10", "BARAJLARI", "GİRESUN,", "ANKARA,",
            "Seans", "GÜN SABAH", "GÜN ÖĞLEDEN", "Splash Meet",
            "BAŞHAKEM", "NESLİHAN", "GÜRKAN KARA", "YB  ", "Sonuçlar",
            "ERGUN SAVAN", "ALİ SERCAN", "50m:", "YB Zaman Derece"]

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        
        # PDF encoding hatası düzeltme
        # "Ku3lü5b.1ü2" → "35.12", "Kulü2b:47.31" → "2:47.31" gibi bozuk süreler
        # Adım 1: harf+rakam+harf+: → rakam:  ("Kulü2b:" → "2:")
        line = re.sub(r"[A-Za-zçğıöşüÇĞİÖŞÜ]+(\d+)[A-Za-zçğıöşüÇĞİÖŞÜ]+:", r"\1:", line)
        # Adım 2: rakam:harf+rakam → rakam:rakam  ("2:ü23" → "2:23")
        line = re.sub(r"(\d+:)[A-Za-zçğıöşüÇĞİÖŞÜ]+(\d)", r"\1\2", line)
        # Adım 3: rakam+harf+rakam.rakam → rakamrakam.rakam  ("3lü5b.1ü2" → "35.12")
        # Birden fazla kez uygula
        for _ in range(5):
            new = re.sub(r"(\d+)[A-Za-zçğıöşüÇĞİÖŞÜ]+(\d)", r"\1\2", line)
            if new == line:
                break
            line = new

        if any(x in line for x in SKIP):
            continue
        if re.match(r"^\d+\.\d+\.\d{4}", line):  # tarih satırı
            continue

        # DSQ / SW
        if line.startswith("DSQ") or re.match(r"^SW[\s\d]", line):
            pending = None
            if in_relay:
                relay_club = ""; relay_time = ""; relay_athletes = []
            continue

        # ── EVENT ──
        ev = re.match(r"Yarış\s+(\d+)[,\s]+(Kızlar|Erkekler|Karma)\s*,?\s*(.+)", line, re.I)
        if ev:
            if in_relay:
                flush_relay()
            pending = None
            current_age_sub = None

            gender_map = {"Kızlar": "Girls", "Erkekler": "Boys", "Karma": "Mixed"}
            gender = gender_map.get(ev.group(2).strip(), ev.group(2).strip())
            rest   = ev.group(3).strip()

            age_m = re.search(r"(\d+\s*-\s*\d+\s*yaş\S*(?:\s+arası)?|\d+\s*yaş\S*)", rest, re.I)
            age_group = age_m.group(1).strip() if age_m else "Unknown"
            race = re.sub(r"\d+\s*-\s*\d+\s*yaş\S*(?:\s+arası)?|\d+\s*yaş\S*",
                          "", rest, flags=re.I).strip(" ,")
            is_relay = bool(re.search(r"\d+\s*x\s*\d+", race, re.I))

            current_event     = {"event": ev.group(1), "gender": gender,
                                 "race": race, "age_group": age_group, "is_relay": is_relay}
            current_age_group = age_group
            in_relay          = is_relay
            continue

        if current_event is None:
            continue

        # ── YAŞ ALT GRUBU: "10 yaş", "11 yaş", "12 yaş" ──
        age_sub = re.fullmatch(r"(\d{1,2})\s*yaş", line, re.I)
        if age_sub:
            current_age_sub = age_sub.group(1) + " yaş"
            continue

        # ── BİREYSEL ──
        if not in_relay:
            if re.search(r"BARAJINI GEÇTİ", line, re.I):
                if pending:
                    results.append(pending)
                    pending = None
                continue

            # Sporcu: "Damla, KAYNAKÇI 16 Istanbul Çevre Spor Kulübü 45.94 255"  (virgüllü)
            # veya:   "Zeynep FIÇICIOĞLU 15 Itü Geliştirme Vakfı ... 1:12.25 366"  (virgülsüz)
            # (kulüp ile süre arasında boşluk olmayabilir!)
            m = re.match(
                r"^([A-ZÇĞİÖŞÜa-zçğıöşü][^,\d]+(?:,\s*[A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)?)\s+"
                r"(\d{2})\s+(.+?)\s*(\d+:\d+\.\d+|\d+\.\d+)(?:\s|$)",
                line
            )
            if m:
                pending = None
                club_raw = m.group(3).strip()
                # Kulüp adını temizle: yapışık rakamları ve sonraki içerikleri at
                club_clean = re.sub(r"\d[\d.:]*.*$", "", club_raw).strip()
                if not club_clean:
                    club_clean = club_raw
                pending = {
                    "event":      current_event.copy(),
                    "rank":       "Katılım Barajını Geçti",
                    "name":       m.group(1).strip(),
                    "birth_year": m.group(2),
                    "club":       club_clean,
                    "time":       m.group(4),
                    "age_group":  current_age_sub or current_age_group,
                    "round":      ""
                }

        # ── RELAY ──
        else:
            # Kulüp satırı tespiti:
            # Giresun: "Istanbul Çevre Spor Kulübü Istanbul Çevre Spor Kulübü 2:44.67 263"
            # Ankara:  "V.A.M.O.S V.A.M.O.S 2:02.19 335"  veya "Orka Swim Team Orka Swim Team 2:07.40 295"
            # Strateji: satırda süre var + başlangıç harf ile başlıyor + sporcu YB regex yok
            club_time_m = re.search(r"(\d+:\d+\.\d+|\d+\.\d+)\s*\d*\s*$", line)
            is_athlete_line = bool(re.search(r"\b\d{2}\b", line))  # YB (13,14,15) içeriyor mu?

            if club_time_m and re.match(r"^[A-ZÇĞİÖŞÜa-zçğıöşü.\-]", line):
                # Kulüp satırı mı sporcu satırı mı ayırt et:
                # Sporcu satırında: "Ad SOYAD 13 süre Ad SOYAD 13 süre" — araya YB giriyor
                # Kulüp satırında: "KulüpAdı KulüpAdı süre" — YB yok veya sadece süre var
                # Eğer satırda sadece süre rakamları var (YB hariç) → kulüp satırı
                line_no_time = re.sub(r"\d+:\d+\.\d+|\d+\.\d+", "", line)
                two_digit_count = len(re.findall(r"\b\d{2}\b", line_no_time))
                # Kulüp satırında iki haneli rakam olmaz (veya az olur), sporcu satırında YB'ler var
                if two_digit_count == 0:
                    relay_time_val = club_time_m.group(1)
                    # Kulüp adını bul: süre öncesindeki metni al, tekrarlı kısmı temizle
                    before_time = line[:club_time_m.start()].strip()
                    # "KulüpAdı KulüpAdı" → ilk yarıyı al (adın iki kez yazıldığı format)
                    # Tekrarlayan prefiksi bul
                    words = before_time.split()
                    half_w = len(words) // 2
                    first_half_words = words[:half_w] if half_w > 0 else words
                    candidate = " ".join(first_half_words).strip()
                    # Eğer candidate çok kısaysa tüm before_time'ı al
                    club_name = candidate if len(candidate) >= 4 else before_time
                    if relay_club and relay_athletes:
                        relay_entries.append((relay_club, time_to_seconds(relay_time),
                                              relay_time, relay_athletes[:]))
                    relay_club     = club_name
                    relay_time     = relay_time_val
                    relay_athletes = []
                    continue

            # Relay sporcu satırı — Giresun (virgüllü): "Nisan Hira, EROL 16 Beste, UMAN 16 ..."
            # Relay sporcu satırı — Ankara (virgülsüz): "Efe AĞABABAOĞLU 13 29.54 Koray GÜNDÜZ 13 30.86"
            if relay_club:
                # Önce virgüllü formatı dene (Giresun)
                ath_matches = re.findall(
                    r"([A-ZÇĞİÖŞÜa-zçğıöşü][^,\d]+,\s*[A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)\s+(\d{2})\s+",
                    line
                )
                # Virgüllü bulunamadıysa virgülsüz formatı dene (Ankara)
                if not ath_matches:
                    ath_matches = re.findall(
                        r"([A-ZÇĞİÖŞÜa-zçğıöşü][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü][A-Za-zçğıöşüÇĞİÖŞÜ]+)+)\s+(\d{2})\s+",
                        line
                    )
                for name_r, year_r in ath_matches:
                    name_r = name_r.strip()
                    if len(name_r) >= 4:
                        relay_athletes.append({"name": name_r, "birth_year": year_r})

    if in_relay:
        flush_relay()

    return results


# ─────────────────────────────────────────────
# SEM FİNALİ PARSER (Samsun formatı)
# ─────────────────────────────────────────────

def parse_sem(raw_lines):
    """
    Sporcu Eğitim Merkezleri Türkiye Finali formatı.
    Sporcu: "N. Ad SOYAD  YB  Şehir  Süre  Puan"
            "disk. Ad SOYAD  YB  Şehir"
    Yarış başlığı: "Yarış N  Kızlar/Erkekler, Xm Stil  Yaş grubu"
    Yaş grubu satırı: "12 yaş", "13 yaş", ..., "17 - 18 yaşları arası"
    """
    results = []
    current_event = None
    current_age_group = None
    current_age_sub   = None   # "12 yaş", "13 yaş" vb.

    # Şehir listesi — sporcu satırında kulüp yerine şehir var
    # Kulüp olarak şehri saklayacağız

    # Cinsiyet / yarış regex
    race_re   = re.compile(
        r"^Yarış\s+(\d+)\s+(Kızlar|Erkekler|Bayanlar|Baylar)[,\s]+(.+?)(?:\s+([\d\s\-–]+yaşları?\s*arası|[\d]+\s*yaş))?$",
        re.I
    )
    age_sub_re = re.compile(
        r"^(\d{1,2}\s*-\s*\d{1,2}\s*yaşları\s*arası|\d{1,2}\s*yaş)$",
        re.I
    )
    # Sporcu: "1.  Ad SOYAD  YB  Şehir  Süre  Puan"
    # veya:   "1. Ad SOYAD 12 Ankara 35.74 9,00"
    athlete_re = re.compile(
        r"^(\d+)\.\s+(.+?)\s+(\d{2})\s+([A-ZÇĞİÖŞÜa-zçğıöşü][A-Za-zçğışöüÇĞİŞÖÜ\s]+?)\s+"
        r"(\d+:\d+\.\d+|\d+\.\d+)\s*([\d,\.]+)?$"
    )
    # disk. (diskalifiye)
    disk_re = re.compile(
        r"^disk\.\s+(.+?)\s+(\d{2})\s+([A-ZÇĞİÖŞÜa-zçğıöşü].*?)$",
        re.I
    )

    def gender_from(s):
        s = s.upper()
        if "KIZLAR" in s or "BAYAN" in s:
            return "Girls"
        return "Boys"

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # Gün/seans başlığını atla
        if re.match(r"^\d+\s*-\s*\d+\.GÜN|^\d+\s*-\s*\d+\.GÜN", line, re.I):
            continue
        if re.match(r"^Splash Meet Manager|^Registered to|^SPORCU EĞİTİM", line, re.I):
            continue

        # Yarış başlığı: "Yarış 1  Kızlar, 50m Kurbağalama  14 - 18 yaşları arası"
        m = re.match(
            r"^Yarış\s+(\d+)\s+(Kızlar|Erkekler|Bayanlar|Baylar)[,\s]+(.+?)(?:\s+([\d\s\-–]+yaşları?\s*arası|[\d]+\s*yaş\s*(?:ve üstü)?))?\s*$",
            line, re.I
        )
        if m:
            event_no = m.group(1)   # str, diğer parser'larla tutarlı
            gender   = gender_from(m.group(2))
            race_raw = m.group(3).strip().rstrip(",")
            age_grp  = (m.group(4) or "").strip()
            current_event = {
                "event":    event_no,
                "race":     race_raw,
                "gender":   gender,
                "is_relay": False,
            }
            current_age_group = age_grp or "Open"
            current_age_sub   = None
            continue

        # Yarış ikinci satırı (tarih): "28.07.2026"  → atla
        if re.match(r"^\d{2}\.\d{2}\.\d{4}$", line):
            continue

        # Devam başlık satırı: "Yarış 3, Kızlar, 100m Serbest"
        m2 = re.match(r"^Yarış\s+\d+,\s+(Kızlar|Erkekler)[,\s]+(.+?),\s+(\d+.*yaş)", line, re.I)
        if m2:
            continue

        # Sıra / YB / Zaman sütun başlığı
        if re.match(r"^Sıra\s+YB|^YB\s+Zaman", line, re.I):
            continue

        # Yaş alt grubu: "14 yaş", "17 - 18 yaşları arası"
        m3 = age_sub_re.match(line)
        if m3:
            current_age_sub = m3.group(1).strip()
            continue

        # KATILIM satırı → atla
        if "KATILIM BARAJINI" in line.upper():
            continue

        # SW kuralı ihlali notu → atla
        if line.upper().startswith("SW "):
            continue

        if current_event is None:
            continue

        # Sporcu satırı
        m4 = athlete_re.match(line)
        if m4:
            rank     = int(m4.group(1))
            name     = m4.group(2).strip()
            yb       = m4.group(3)
            city     = m4.group(4).strip()
            time_str = m4.group(5)
            birth_year = "20" + yb if int(yb) >= 5 else "20" + yb

            # Yaş grubu: önce current_age_sub, yoksa current_age_group
            age_grp = current_age_sub if current_age_sub else current_age_group

            results.append({
                "name":       name,
                "club":       city,   # şehir = kulüp
                "birth_year": birth_year,
                "time":       time_str,
                "rank":       f"{rank}. sıra",
                "age_group":  age_grp,
                "round":      "",
                "event":      current_event,
            })
            continue

        # disk. satırı
        m5 = disk_re.match(line)
        if m5:
            name = m5.group(1).strip()
            yb   = m5.group(2)
            city = m5.group(3).strip()
            age_grp = current_age_sub if current_age_sub else current_age_group
            results.append({
                "name":       name,
                "club":       city,
                "birth_year": "20" + yb,
                "time":       "DQ",
                "rank":       "Diskalifiye",
                "age_group":  age_grp,
                "round":      "",
                "event":      current_event,
            })

    return results


# ─────────────────────────────────────────────
# ANA PARSE FONKSİYONU
# ─────────────────────────────────────────────

def get_cache_path(pdf_path):
    """PDF için cache dosya yolunu döndürür"""
    cache_dir = os.path.join(os.path.dirname(pdf_path), ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    pdf_name = os.path.basename(pdf_path)
    return os.path.join(cache_dir, pdf_name + ".cache")


def is_cache_valid(pdf_path, cache_path):
    """Cache dosyası var mı ve PDF'den daha yeni mi?"""
    if not os.path.exists(cache_path):
        return False
    return os.path.getmtime(cache_path) >= os.path.getmtime(pdf_path)


def parse_pdf(pdf_path):
    import pickle

    cache_path = get_cache_path(pdf_path)

    # Cache geçerliyse direkt yükle
    if is_cache_valid(pdf_path, cache_path):
        print(f"⚡ Cache'den yükleniyor: {os.path.basename(pdf_path)}")
        try:
            with open(cache_path, "rb") as f:
                results = pickle.load(f)
            if results:  # 0 sonuçlu cache'i geçersiz say
                print(f"✅ {len(results)} sonuç cache'den yüklendi\n")
                return results
            else:
                print("   ⚠️  Cache boş (0 sonuç), PDF yeniden okunuyor...")
        except Exception:
            print("   ⚠️  Cache bozuk, PDF yeniden okunuyor...")

    # Cache yoksa PDF'i parse et
    print(f"📄 PDF okunuyor: {pdf_path}")
    raw_lines = read_pdf_lines(pdf_path)
    if not raw_lines:
        print("   ❌ PDF okunamadı!")
        return []
    print(f"   ✅ {len(raw_lines)} satır okundu\n")

    fmt = detect_format(raw_lines)
    if fmt == "gelisim":
        print("   📋 Format: Gelişim Ligi\n")
        results = parse_gelisim(raw_lines)
    elif fmt == "sem":
        print("   📋 Format: SEM Finali\n")
        results = parse_sem(raw_lines)
    else:
        print("   📋 Format: Standart\n")
        results = parse_standart(raw_lines)

    print(f"✅ {len(results)} sonuç parse edildi\n")

    # Cache'e kaydet
    try:
        with open(cache_path, "wb") as f:
            pickle.dump(results, f)
        print(f"💾 Cache kaydedildi\n")
    except Exception as e:
        print(f"   ⚠️  Cache kaydedilemedi: {e}")

    return results


# ─────────────────────────────────────────────
# YARIŞIN BİLGİSİNİ OKU
# ─────────────────────────────────────────────

def get_competition_info(pdf_path):
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            lines = []
            for page in pdf.pages[:3]:
                try:
                    text = page.extract_text()
                    if text:
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if lines:
                            break
                except Exception:
                    continue

            if not lines:
                return os.path.splitext(os.path.basename(pdf_path))[0]

            name = None
            location_date = None

            for line in lines[:15]:
                if re.search(r"\d{1,2}\.\s*-\s*\d{1,2}\.\d{1,2}\.\d{4}", line) \
                        and "Results" not in line and "MORNING" not in line:
                    location_date = line
                elif "ŞAMPİYONASI" in line.upper() and not name:
                    name = line
                elif "SPORCU EĞİTİM MERKEZLERİ" in line.upper() and not name:
                    name = line
                elif "SEM FİNAL" in line.upper() and not name:
                    name = line
                elif not name and len(line) > 25 and any(k in line.upper() for k in
                        ["YÜZME","SWIMMING","CHAMPIONSHIP","KULÜP","GELİŞİM","LİGİ","MÜSABAKA","SEM"]):
                    name = line

            if name and location_date:
                return f"{location_date} — {name}"
            return name or location_date or os.path.splitext(os.path.basename(pdf_path))[0]
    except Exception:
        return os.path.splitext(os.path.basename(pdf_path))[0]


# ─────────────────────────────────────────────
# ARAMA
# ─────────────────────────────────────────────

def search_athlete(results, athlete_name):
    search_norm = normalize(athlete_name)
    matches = [r for r in results if search_norm in normalize(r["name"])]
    if not matches:
        return []

    # Duplike temizle: event+race+age_group+round+time+rank
    seen = set()
    deduped = []
    for m in matches:
        key = (m["event"]["event"], m["event"]["race"], m["age_group"],
               m["round"], m["time"], m["rank"], m["event"].get("is_relay", False))
        if key not in seen:
            seen.add(key); deduped.append(m)

    # Aynı yarış+round+süre+sıra için en spesifik yaş grubunu seç
    def age_pri(ag):
        if re.match(r"^\d+\s*years$", ag or ""):          return 3
        if re.match(r"^\d+\s*-\s*\d+\s*years", ag or ""): return 2
        if (ag or "").lower() == "open":                   return 1
        return 0

    best = {}
    for m in deduped:
        key = (m["event"]["event"], m["event"]["race"], m["round"], m["time"], m["rank"])
        if key not in best or age_pri(m["age_group"]) > age_pri(best[key]["age_group"]):
            best[key] = m
    deduped = list(best.values())

    # Final varsa Prelim'i gizle (event+race bazında)
    groups = {}
    for m in deduped:
        key = (m["event"]["event"], m["event"]["race"])
        if key not in groups:
            groups[key] = {"prelim": [], "final": [], "single": []}
        if "Final" in m.get("round", ""):
            groups[key]["final"].append(m)
        elif m.get("round", "") == "":
            groups[key]["single"].append(m)
        else:
            groups[key]["prelim"].append(m)

    filtered = []
    for key, rounds in groups.items():
        if rounds["single"]:
            filtered.extend(rounds["single"])
        elif rounds["final"]:
            filtered.extend(rounds["final"])
        else:
            filtered.extend(rounds["prelim"])

    filtered.sort(key=lambda x: int(x["event"]["event"]) if str(x["event"]["event"]).isdigit() else 0)
    return filtered


# ─────────────────────────────────────────────
# GÖSTER
# ─────────────────────────────────────────────

def display_results(athlete_name, matches):
    if not matches:
        print(f"❌ '{athlete_name}' bulunamadı\n")
        return

    print(f"\n🏊 '{athlete_name}' için {len(matches)} sonuç bulundu:\n")
    print("=" * 80)

    for i, r in enumerate(matches, 1):
        is_relay = r["event"].get("is_relay", False)
        tur = r.get("round", "") or "-"
        rank = r["rank"]

        print(f"\n{i}. YARIŞ{'  [BAYRAK]' if is_relay else ''}:")
        print(f"   Sporcu      : {r['name']}")
        print(f"   Kulüp       : {r['club']}")
        print(f"   Sıralama    : {rank}")
        print(f"   Süre        : {r['time']}")
        print(f"   Doğum Yılı  : {r['birth_year']}")
        print(f"   Yarış       : {r['event']['race']}")
        print(f"   Tur         : {tur}")
        print(f"   Cinsiyet    : {r['event']['gender']}")
        print(f"   Yaş Grubu   : {r['age_group']}")
        print(f"   Event No    : {r['event']['event']}")

    print("\n" + "=" * 80)


# ─────────────────────────────────────────────
# ANA PROGRAM
# ─────────────────────────────────────────────

def main():
    pdf_dir = "pdfs"
    pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])

    if not pdf_files:
        print("❌ 'pdfs' klasöründe PDF bulunamadı!")
        return

    print("\n" + "=" * 80)
    print("🏊 YÜZME YARIŞI SONUÇ SORGULAMA")
    print("=" * 80)
    print("\n📂 Mevcut yarış dosyaları:\n")

    infos = []
    for i, f in enumerate(pdf_files, 1):
        info = get_competition_info(os.path.join(pdf_dir, f))
        infos.append(info)
        print(f"   {i}. {info}")

    print()
    while True:
        secim = input("Yarış seçin (numara girin): ").strip()
        if secim.isdigit() and 1 <= int(secim) <= len(pdf_files):
            break
        print("   ⚠️  Geçersiz seçim.")

    idx = int(secim) - 1
    pdf_path = os.path.join(pdf_dir, pdf_files[idx])
    print(f"\n✅ Seçilen yarış: {infos[idx]}\n")

    results = parse_pdf(pdf_path)
    if not results:
        print("❌ PDF'den sonuç okunamadı!")
        return

    while True:
        print("\n" + "=" * 80)
        athlete_name = input("🔍 Sporcu adı girin (çıkmak için 'q', yarış değiştirmek için 'r'): ").strip()

        if athlete_name.lower() in ["q", "quit", "exit"]:
            print("\n👋 Görüşmek üzere!\n")
            break
        if athlete_name.lower() in ["r", "restart"]:
            main(); return
        if not athlete_name:
            continue

        matches = search_athlete(results, athlete_name)
        display_results(athlete_name, matches)


if __name__ == "__main__":
    main()
