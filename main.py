import pdfplumber
import re
from difflib import SequenceMatcher

def parse_pdf(pdf_path, include_relays=True):
    """PDF'i parse eder ve tüm sonuçları döndürür"""
    
    raw_lines = []
    print("📄 PDF okunuyor...")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"   Toplam {total_pages} sayfa bulundu")
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Her 10 sayfada bir ilerleme göster
                    if page_num % 10 == 0 or page_num == total_pages:
                        print(f"   Sayfa {page_num}/{total_pages} okunuyor...", end='\r')
                    
                    text = page.extract_text()
                    if text:
                        raw_lines.extend(text.split("\n"))
                except KeyboardInterrupt:
                    print(f"\n⚠️  İşlem iptal edildi. {page_num-1}/{total_pages} sayfa okundu.")
                    print(f"   Devam ediliyor (şu ana kadar okunanlarla)...")
                    break
                except Exception as e:
                    print(f"\n⚠️  Sayfa {page_num} okunurken hata: {str(e)[:50]}... (atlanıyor)")
                    continue
            
            print(f"\n   ✅ {len(raw_lines)} satır okundu")
    
    except FileNotFoundError:
        print(f"\n❌ PDF dosyası bulunamadı: {pdf_path}")
        return []
    except KeyboardInterrupt:
        print(f"\n⚠️  PDF okuma iptal edildi. Mevcut verilerle devam ediliyor...")
        if not raw_lines:
            print("   Hiç veri okunamadı.")
            return []
    except Exception as e:
        print(f"\n❌ PDF okuma hatası: {e}")
        return []

    if not raw_lines:
        print("   ❌ Hiç satır okunamadı!")
        return []

    print("   🔄 Veriler işleniyor...")
    
    results = []
    current_event = None
    current_age_group = None
    current_round = "Prelim"  # Default: Prelim (Eleme)
    
    # Relay parsing için
    in_relay = False
    relay_rank = None
    relay_club = None
    relay_time = None

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # Gereksiz satırları atla
        if any(x in line for x in ["Splash Meet Manager", "TÜRKİYE", "Points"]):
            continue
        if line.startswith(("DSQ", "SW")) or "(Time" in line:
            continue

        # ================= ROUND TESPİTİ (Results Finals, Prelim) =================
        # "Results Finals" → Final
        if "Results" in line and "Final" in line:
            current_round = "Final"
            continue
        
        # "Final A", "Final B", "Final C" satırı
        final_line_match = re.fullmatch(r"Final\s*([A-D]?)", line, re.I)
        if final_line_match:
            letter = final_line_match.group(1)
            current_round = f"Final {letter}" if letter else "Final"
            continue
        
        # "Prelim" satırı
        if re.fullmatch(r"Prelim", line, re.I):
            current_round = "Prelim"
            continue

        # ================= EVENT =================
        event_match = re.search(r"Event\s+(\d+)\s*,?\s*(Men|Boys|Women|Girls)?\s*,?\s*(.+)", line, re.I)
        
        if event_match:
            event_no = event_match.group(1)
            gender = (event_match.group(2) or "Unknown").title()
            rest = event_match.group(3).strip()

            # Event satırında "Prelim" veya "Final" var mı?
            if re.search(r"\bPrelim\b", rest, re.I):
                current_round = "Prelim"
            elif re.search(r"\bFinal\s*([A-D]?)\b", rest, re.I):
                final_match = re.search(r"\bFinal\s*([A-D]?)\b", rest, re.I)
                letter = final_match.group(1)
                current_round = f"Final {letter}" if letter else "Final"
            # Yoksa default "Prelim" kalır

            # Yaş grubu
            age_match = re.search(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", rest)
            age_group = age_match.group(1) if age_match else "Unknown"
            
            # Yarış stili (Prelim/Final temizle)
            race = re.sub(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open|Prelim|Final\s*[A-D]?)", "", rest, flags=re.I).strip(" ,")

            # Relay mi?
            is_relay = bool(re.search(r"\b\d+\s*x\s*\d+", race, re.I))
            
            if is_relay and not include_relays:
                current_event = None
                in_relay = False
                continue
            
            current_event = {
                "event": event_no,
                "gender": gender,
                "race": race,
                "age_group": age_group,
                "is_relay": is_relay,
                "round": current_round
            }
            current_age_group = age_group
            in_relay = is_relay
            relay_rank = None
            relay_club = None
            continue

        if current_event is None:
            continue

        # Yaş grubu satırı
        if re.fullmatch(r"(\d+\s*-\s*\d+\s*years|\d+\s*years|Open)", line):
            current_age_group = line
            continue

        # ================= RELAY PARSE =================
        if in_relay:
            # Kulüp satırı: "2. Fenerbahçe Spor Kulübü Fenerbahce Spor Kulubu 4:08.66"
            club_match = re.match(r"^(\d+)\.\s+(.+?)\s+(\d+:\d+\.\d+)$", line)
            if club_match:
                relay_rank = club_match.group(1)
                relay_time = club_match.group(3)
                
                # Kulüp adını parse et
                middle = club_match.group(2).strip()
                words = middle.split()
                club_words = []
                for word in words:
                    club_words.append(word)
                    if word.lower() in ["kulübü", "kulubu"]:
                        break
                relay_club = " ".join(club_words)
                continue
            
            # Sporcu satırı: "Meric UYGUN 07 31.92 1:07.87"
            athlete_match = re.match(r"^([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)\s+(\d{2})\s+[\d:.]+", line)
            if athlete_match and relay_club:
                name = athlete_match.group(1).strip()
                year = athlete_match.group(2)
                
                event_copy = current_event.copy()
                event_copy["age_group"] = current_age_group or "Unknown"
                
                # Relay formatında kaydet
                relay_line = f"{relay_rank}. {name} {year} {relay_club} {relay_time}"
                results.append((event_copy, relay_line))
                continue

        # ================= BİREYSEL YARIŞ PARSE =================
        if not in_relay and re.match(r"^\d+\.", line) and re.search(r"\d+:\d+\.\d+", line):
            event_copy = current_event.copy()
            event_copy["age_group"] = current_age_group or "Unknown"
            results.append((event_copy, line))

    return results


def parse_athlete_line(line):
    """Sporcu satırından bilgileri çıkarır (bireysel veya relay)"""
    
    # Bireysel: "1. İsim Soyisim YAS Kulüp Adı ZAMAN"
    match = re.match(r"^(\d+)\.\s+(.+?)\s+(\d+)\s+(.+?)\s+(\d+:\d+\.\d+)", line)
    if match:
        return {
            "rank": match.group(1),
            "name": match.group(2).strip(),
            "birth_year": match.group(3),
            "club": match.group(4).strip(),
            "time": match.group(5),
            "is_relay": False
        }
    return None


def similarity_score(a, b):
    """İki string arasındaki benzerlik oranını hesaplar (0-1 arası)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def smart_name_match(search_name, athlete_name):
    """Akıllı isim eşleştirmesi - ad ve soyadı ayrı ayrı kontrol eder"""
    search_lower = search_name.lower().strip()
    athlete_lower = athlete_name.lower().strip()
    
    if search_lower == athlete_lower:
        return True, 1.0
    
    search_parts = search_lower.split()
    athlete_parts = athlete_lower.split()
    
    if len(search_parts) < 2 or len(athlete_parts) < 2:
        score = similarity_score(search_lower, athlete_lower)
        return score >= 0.8, score
    
    first_name_score = similarity_score(search_parts[0], athlete_parts[0])
    last_name_score = similarity_score(search_parts[-1], athlete_parts[-1])
    
    if first_name_score >= 0.7 and last_name_score >= 0.7:
        avg_score = (first_name_score + last_name_score) / 2
        return True, avg_score
    
    return False, 0.0


def remove_prelims_with_finals(matches):
    """
    Aynı yarış için hem Prelim hem Final varsa, sadece Final'i tutar.
    Prelim'i sadece Final yoksa gösterir.
    
    Mantık:
    - Aynı Event + Race için (yaş grubu önemsiz!)
    - Herhangi bir Final varsa → Tüm Prelim'leri gizle
    - Hiç Final yoksa → Tüm Prelim'leri göster
    
    Örnek:
    - Event 3, 100m Breaststroke, 15 years, Prelim → GİZLE
    - Event 3, 100m Breaststroke, Open, Prelim → GİZLE
    - Event 3, 100m Breaststroke, Open, Final C → GÖSTER
    """
    
    if not matches:
        return matches
    
    # Event + Race bazında grupla (yaş grubu dahil değil!)
    groups = {}
    
    for match in matches:
        event = match["event"]
        
        # Anahtar: sadece event_no + race (yaş grubu YOK)
        key = (event["event"], event["race"])
        
        if key not in groups:
            groups[key] = {"prelim": [], "final": [], "has_final": False}
        
        round_type = event.get("round", "Prelim")
        
        if "Final" in round_type:
            groups[key]["final"].append(match)
            groups[key]["has_final"] = True
        else:
            groups[key]["prelim"].append(match)
    
    # Filtreleme mantığı
    filtered = []
    
    for key, rounds in groups.items():
        if rounds["has_final"]:
            # O yarışta herhangi bir Final varsa, sadece Final'leri ekle
            filtered.extend(rounds["final"])
        else:
            # Hiç Final yoksa, Prelim'leri ekle
            filtered.extend(rounds["prelim"])
    
    # Similarity skoruna göre tekrar sırala
    filtered.sort(key=lambda x: x["similarity"], reverse=True)
    
    return filtered


def deduplicate_results(matches):
    """
    Aynı event/round/time olan duplike sonuçları temizler.
    En spesifik yaş grubunu tutar (örn: "15 years" > "13-15 years" > "Open")
    
    Öncelik sırası:
    1. Tek yaş grubu (örn: "15 years", "14 years")
    2. Yaş aralığı (örn: "13-15 years")
    3. Open
    """
    
    if not matches:
        return matches
    
    # Event + Round + Time bazında grupla
    groups = {}
    
    for match in matches:
        event = match["event"]
        athlete = match["athlete"]
        
        # Anahtar: event_no + round + race + time
        key = (
            event["event"],
            event.get("round", "Prelim"),
            event["race"],
            athlete["time"]
        )
        
        if key not in groups:
            groups[key] = []
        
        groups[key].append(match)
    
    # Her grup için en iyi yaş grubunu seç
    filtered = []
    
    for key, group_matches in groups.items():
        if len(group_matches) == 1:
            # Tek sonuç varsa direkt ekle
            filtered.append(group_matches[0])
        else:
            # Birden fazla sonuç varsa en spesifik yaş grubunu seç
            best_match = None
            best_priority = -1
            
            for match in group_matches:
                age_group = match["event"]["age_group"]
                
                # Öncelik hesapla
                if re.match(r"^\d+\s*years$", age_group):
                    # Tek yaş: "15 years" → en yüksek öncelik
                    priority = 3
                elif re.match(r"^\d+\s*-\s*\d+\s*years$", age_group):
                    # Yaş aralığı: "13-15 years" → orta öncelik
                    priority = 2
                elif age_group.lower() == "open":
                    # Open → en düşük öncelik
                    priority = 1
                else:
                    # Bilinmeyen → düşük öncelik
                    priority = 0
                
                if priority > best_priority:
                    best_priority = priority
                    best_match = match
            
            if best_match:
                filtered.append(best_match)
    
    # Similarity skoruna göre tekrar sırala
    filtered.sort(key=lambda x: x["similarity"], reverse=True)
    
    return filtered


def search_athlete(athlete_name, results, threshold=0.7, remove_duplicates=True, hide_prelims_with_finals=True):
    """Sporcu adını arar ve sonuçlarını döndürür"""
    
    matches = []
    
    for event, line in results:
        athlete_data = parse_athlete_line(line)
        if athlete_data:
            is_match, score = smart_name_match(athlete_name, athlete_data["name"])
            if is_match and score >= threshold:
                matches.append({
                    "event": event,
                    "athlete": athlete_data,
                    "similarity": score
                })
    
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    
    # 1. Duplikeleri temizle (aynı yarış, farklı yaş grupları)
    if remove_duplicates:
        matches = deduplicate_results(matches)
    
    # 2. Final varsa Prelim'i gizle
    if hide_prelims_with_finals:
        matches = remove_prelims_with_finals(matches)
    
    return matches


def display_results(athlete_name, matches):
    """Sonuçları güzel bir formatta gösterir"""
    
    if not matches:
        print(f"\n❌ '{athlete_name}' isimli sporcu bulunamadı.\n")
        return
    
    print(f"\n🏊 '{athlete_name}' için {len(matches)} sonuç bulundu:\n")
    print("=" * 80)
    
    for i, match in enumerate(matches, 1):
        event = match["event"]
        athlete = match["athlete"]
        
        relay_marker = " [RELAY]" if event.get("is_relay") else ""
        round_info = event.get("round", "Prelim")
        
        print(f"\n{i}. YARIŞ BİLGİSİ{relay_marker}:")
        print(f"   Sporcu Adı    : {athlete['name']}")
        print(f"   Doğum Yılı    : {athlete['birth_year']}")
        print(f"   Kulüp         : {athlete['club']}")
        print(f"   Sıralama      : {athlete['rank']}. sıra")
        print(f"   Süre          : {athlete['time']}")
        print(f"   Yarış         : {event['race']}")
        print(f"   Tur           : {round_info}")  # Prelim veya Final
        print(f"   Cinsiyet      : {event['gender']}")
        print(f"   Yaş Grubu     : {event['age_group']}")
        print(f"   Event No      : {event['event']}")
        if match["similarity"] < 1.0:
            print(f"   Benzerlik     : %{match['similarity']*100:.1f}")
    
    print("\n" + "=" * 80)


def main():
    """Ana program"""
    
    pdf_path = "pdfs/ornek.pdf"
    
    # PDF dosyası var mı kontrol et
    import os
    if not os.path.exists(pdf_path):
        print(f"\n❌ PDF dosyası bulunamadı: {pdf_path}")
        print("   Lütfen PDF'i doğru klasöre koyun ve tekrar deneyin.\n")
        return
    
    try:
        results = parse_pdf(pdf_path, include_relays=True)
        
        if not results:
            print("\n❌ PDF'den hiç sonuç okunamadı.")
            print("   Olası sebepler:")
            print("   - PDF çok erken iptal edildi (daha fazla sayfa okumayı deneyin)")
            print("   - PDF bozuk veya şifreli")
            print("   - PDF'de yarış sonucu yok\n")
            
            # Kullanıcıya seçenek sun
            retry = input("   Tekrar denemek ister misiniz? (e/h): ").strip().lower()
            if retry in ['e', 'y', 'yes', 'evet']:
                return main()  # Tekrar çalıştır
            return
        
        print(f"✅ {len(results)} yarış sonucu yüklendi.")
        
        # İlk birkaç sonucu göster
        if len(results) >= 10:
            print(f"   İlk sonuçlar hazır - arama yapabilirsiniz!")
        else:
            print(f"   ⚠️  Sadece {len(results)} sonuç var - PDF tam okunmamış olabilir.")
        print()
        
    except KeyboardInterrupt:
        print("\n\n👋 Program kapatıldı.\n")
        return
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}\n")
        return
    
    while True:
        try:
            print("\n" + "=" * 80)
            athlete_name = input("🔍 Sporcu adı girin (çıkmak için 'q'): ").strip()
            
            if athlete_name.lower() in ['q', 'quit', 'exit', 'çık']:
                print("\n👋 Görüşmek üzere!\n")
                break
            
            if not athlete_name:
                print("⚠️  Lütfen bir isim girin.")
                continue
            
            matches = search_athlete(athlete_name, results)
            display_results(athlete_name, matches)
        
        except KeyboardInterrupt:
            print("\n\n👋 Görüşmek üzere!\n")
            break
        except Exception as e:
            print(f"\n❌ Hata: {e}")
            continue


if __name__ == "__main__":
    main()