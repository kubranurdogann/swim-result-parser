# 🏊 Yüzme Yarışı Sonuç Sorgulama

Türkiye yüzme yarışlarının PDF sonuç dosyalarını otomatik olarak okuyup sporcu bazında sorgulama yapmanızı sağlayan masaüstü uygulaması.

## Özellikler

- 📄 **Çoklu PDF formatı desteği** — Standart (Antalya/İzmir), Gelişim Ligi (Giresun/Ankara) ve SEM Finali (Samsun) formatlarını otomatik tanır
- 🔍 **Sporcu sorgulama** — Ad veya soyad ile anlık arama, Türkçe karakter desteğiyle
- ⚡ **Akıllı önbellekleme** — Bir kez okunan PDF sonuçları cache'lenir, sonraki açılışta anında yüklenir
- 🗂️ **Yarış yönetimi** — PDF ekle, adını düzenle, sil; liste alfabetik sırada
- 📂 **OneDrive/ağ sürücüsü desteği** — PDF klasörü olarak herhangi bir konum seçilebilir

## Ekran Görüntüsü

| Yarış Listesi | Sporcu Sorgulama |
|---|---|
| Yarışları listeler, alfabetik sıralar | Sporcu adıyla tüm yarış sonuçlarını gösterir |

## Kurulum

### Gereksinimler

- Python 3.10+
- Aşağıdaki kütüphaneler:

```bash
pip install pdfplumber
```

### Çalıştırma

```bash
python gui.py
```

## Kullanım

### Yarış Yükle sekmesi

1. **PDF Klasörü** — Yarış PDF'lerinin bulunduğu klasörü seçin (OneDrive, ağ sürücüsü vb.)
2. **+ PDF Ekle** — Yeni yarış PDF'i ekleyin; program yarış adını otomatik okur
3. **✏️** — Yarış adını düzenleyin (satır üzerinde inline düzenleme)
4. **🗑** — Yarışı silin (cache de otomatik temizlenir)
5. **Çift tıkla** — PDF'i tarayıcıda açın

### Sporcu Sorgula sekmesi

1. Dropdown'dan yarışı seçin → PDF yüklenir
2. Sporcu adını yazıp **Ara**'ya basın (veya Enter)
3. Tüm yarış ve turlar listelenir

## Desteklenen PDF Formatları

| Format | Örnek Yarışlar |
|--------|---------------|
| **Standart** | Antalya, İzmir şampiyonaları |
| **Gelişim Ligi** | Giresun, Ankara, Konya |
| **SEM Finali** | Samsun Sporcu Eğitim Merkezleri Türkiye Finali |

## Proje Yapısı

```
swim-result-parser/
├── gui.py        # Tkinter arayüzü
├── main.py       # PDF okuma ve parser'lar
└── ayarlar.txt   # PDF klasör yolu (otomatik oluşur)
```
