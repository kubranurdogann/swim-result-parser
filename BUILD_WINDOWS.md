# Windows .exe Nasıl Oluşturulur

Bu adımları kendi Windows bilgisayarında uygula.

## 1. Gereksinimler

Python 3.10+ kurulu olmalı. Cmd / PowerShell'de:

```bash
pip install pyinstaller pdfplumber pillow
```

## 2. Projeyi İndir

```bash
git clone https://github.com/kubranurdogann/swim-result-parser.git
cd swim-result-parser
```

## 3. .exe Oluştur

```bash
pyinstaller swim_parser.spec
```

Birkaç dakika sürer. Bitince `dist\YuzmeYarisiSorgula.exe` oluşur.

## 4. Çalıştır

`dist\YuzmeYarisiSorgula.exe` dosyasına çift tıkla — Python kurulu olmasa da çalışır.

## 5. Masaüstüne Kısayol

`dist\YuzmeYarisiSorgula.exe` dosyasına sağ tıkla →  
**"Masaüstüne kısayol gönder"** (veya **"Görev çubuğuna sabitle"**)

---

### Not

- İlk çalıştırmada Windows Defender uyarısı çıkabilir → "Yine de çalıştır" tıkla.
- Uygulama ayarlarını `%APPDATA%\YuzmeYarisi\ayarlar.txt` dosyasında saklar.
- PDF klasörünü bir kez seçtikten sonra her açılışta hatırlar.
