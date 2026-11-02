import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import shutil
import webbrowser
import urllib.parse

from main import parse_pdf, search_athlete, get_competition_info

# ── AÇIK TEMA RENKLERİ ──────────────────────────
BG      = "#f5f5f7"   # arka plan (açık gri)
BG2     = "#ffffff"   # panel arka planı
BG3     = "#e8e8ed"   # başlık satırı
ACCENT  = "#4a6cf7"   # vurgu (mavi-mor)
ACCENT2 = "#0a84ff"   # ikincil vurgu
FG      = "#1c1c1e"   # ana metin
FG2     = "#6e6e73"   # ikincil metin
SUCCESS = "#34c759"
WARNING = "#ff9f0a"
DANGER  = "#ff3b30"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏊 Yüzme Yarışı Sonuç Sorgulama")
        self.geometry("1150x720")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.pdf_files   = []
        self.pdf_infos   = []
        self.results     = []
        self.current_pdf = None
        self._loading    = False

        self.config_file = "ayarlar.txt"
        self.pdf_dir     = self._load_pdf_dir()

        os.makedirs(self.pdf_dir, exist_ok=True)
        self._style()
        self._build()
        self._refresh_pdf_list()

    def _load_pdf_dir(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    path = f.read().strip()
                if os.path.isdir(path):
                    return path
            except Exception:
                pass
        return "pdfs"

    def _save_pdf_dir(self, path):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception:
            pass

    # ── STİL ────────────────────────────────────────
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview",
            background=BG2, foreground=FG,
            fieldbackground=BG2, rowheight=28,
            font=("Segoe UI", 10))
        s.configure("Treeview.Heading",
            background=BG3, foreground=FG,
            font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#fff")])
        s.configure("Vertical.TScrollbar",
            background=BG3, troughcolor=BG, arrowcolor=FG2)
        s.configure("Horizontal.TScrollbar",
            background=BG3, troughcolor=BG, arrowcolor=FG2)
        s.configure("TNotebook", background=BG, tabmargins=[0, 0, 0, 0])
        s.configure("TNotebook.Tab",
            background=BG3, foreground=FG2,
            padding=[16, 8], font=("Segoe UI", 10))
        s.map("TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#fff")])

    # ── ANA YAPI ────────────────────────────────────
    def _build(self):
        tk.Label(self, text="🏊  YÜZME YARIŞI SONUÇ SORGULAMA",
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI", 15, "bold")).pack(pady=(14, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=12)

        self.tab_load   = tk.Frame(self.notebook, bg=BG)
        self.tab_search = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.tab_load,   text="  📂  Yarış Yükle  ")
        self.notebook.add(self.tab_search, text="  🔍  Sporcu Sorgula  ")

        self._build_load_tab()
        self._build_search_tab()

    # ── TAB 1: YARIŞ YÜKLE ─────────────────────────
    def _build_load_tab(self):
        tab = self.tab_load

        top = tk.Frame(tab, bg=BG, pady=12)
        top.pack(fill="x", padx=24)

        # Klasör satırı
        folder_row = tk.Frame(top, bg=BG)
        folder_row.pack(fill="x", pady=(0, 8))

        tk.Label(folder_row, text="📁 PDF Klasörü:",
                 bg=BG, fg=FG2, font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))

        self.lbl_pdf_dir = tk.Label(folder_row,
            text=self.pdf_dir, bg=BG, fg=ACCENT2,
            font=("Segoe UI", 10, "italic"), cursor="hand2")
        self.lbl_pdf_dir.pack(side="left")

        tk.Button(folder_row, text="  📂 Klasör Değiştir  ",
            bg=BG3, fg=FG, font=("Segoe UI", 9),
            relief="flat", cursor="hand2", activebackground=ACCENT,
            command=self._change_pdf_dir).pack(side="right")

        # PDF ekle satırı
        btn_row = tk.Frame(top, bg=BG)
        btn_row.pack(fill="x")
        tk.Label(btn_row,
            text="PDF ekleyin, program otomatik olarak yarış adını okur.",
            bg=BG, fg=FG2, font=("Segoe UI", 10)).pack(side="left")
        tk.Button(btn_row, text="  + PDF Ekle  ",
            bg=ACCENT, fg="#fff", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", activebackground="#3355cc",
            command=self._add_pdf).pack(side="right")

        lf = tk.Frame(tab, bg=BG3, padx=1, pady=1)
        lf.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Sütunlar: yarış adı + kalem + çöp
        cols = ("yarış_adı", "düzenle", "sil")
        self.list_tree = ttk.Treeview(lf, columns=cols,
                                       show="headings", selectmode="browse")
        self.list_tree.heading("yarış_adı", text="Yarış Adı")
        self.list_tree.heading("düzenle",   text="")
        self.list_tree.heading("sil",       text="")
        self.list_tree.column("yarış_adı", width=820, anchor="w")
        self.list_tree.column("düzenle",   width=40,  anchor="center", stretch=False)
        self.list_tree.column("sil",       width=40,  anchor="center", stretch=False)
        self.list_tree.tag_configure("odd",  background=BG2)
        self.list_tree.tag_configure("even", background="#f0f0f5")
        # Çift tıkla PDF aç; tek tıkla aksiyon sütunları
        self.list_tree.bind("<Double-1>",         self._open_pdf_in_browser)
        self.list_tree.bind("<ButtonRelease-1>",  self._list_click)
        # Inline edit için overlay entry
        self._edit_entry  = None
        self._edit_iid    = None

        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.list_tree.yview)
        self.list_tree.configure(yscrollcommand=vsb.set)
        self.list_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        bot = tk.Frame(tab, bg=BG)
        bot.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(bot,
            text="✏️ adı düzenle · 🗑 sil · çift tıkla PDF'i aç",
            bg=BG, fg=FG2, font=("Segoe UI", 8)).pack(side="left")

    # ── TAB 2: SPORCU SORGULA ──────────────────────
    def _build_search_tab(self):
        tab = self.tab_search

        top = tk.Frame(tab, bg=BG3, padx=16, pady=12)
        top.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(top, text="Yarış:", bg=BG3, fg=FG2,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(top, textvariable=self.combo_var,
                                   state="readonly", width=85,
                                   font=("Segoe UI", 10))
        self.combo.grid(row=0, column=1, sticky="w")
        self.combo.bind("<<ComboboxSelected>>", self._on_pdf_select)
        self.lbl_load_status = tk.Label(top, text="", bg=BG3, fg=WARNING,
                                         font=("Segoe UI", 9, "italic"))
        self.lbl_load_status.grid(row=0, column=2, padx=12)

        sf = tk.Frame(tab, bg=BG, padx=16, pady=8)
        sf.pack(fill="x")
        tk.Label(sf, text="🔍 Sporcu Adı:", bg=BG, fg=FG2,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.search_var = tk.StringVar()
        self.entry = tk.Entry(sf, textvariable=self.search_var,
                               bg=BG2, fg=FG, insertbackground=FG,
                               font=("Segoe UI", 11), relief="solid", bd=1, width=32)
        self.entry.pack(side="left")
        self.entry.bind("<Return>", lambda e: self._search())
        tk.Button(sf, text="  Ara  ",
            bg=ACCENT, fg="#fff", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", activebackground="#3355cc",
            command=self._search).pack(side="left", padx=8)
        self.lbl_count = tk.Label(sf, text="", bg=BG, fg=FG2,
                                   font=("Segoe UI", 9))
        self.lbl_count.pack(side="left", padx=8)

        tf = tk.Frame(tab, bg=BG)
        tf.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("no", "yarış", "cinsiyet", "yaş", "sıralama", "süre", "tur", "kulüp", "doğum")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        hdrs = {
            "no":       ("No",       50),
            "yarış":    ("Yarış",   160),
            "cinsiyet": ("Cinsiyet", 75),
            "yaş":      ("Yaş Gr.", 100),
            "sıralama": ("Sıralama",185),
            "süre":     ("Süre",     80),
            "tur":      ("Tur",      80),
            "kulüp":    ("Kulüp",   225),
            "doğum":    ("D.Yılı",  65),
        }
        for col, (text, width) in hdrs.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width,
                             anchor="center" if width < 150 else "w")
        self.tree.tag_configure("odd",   background=BG2)
        self.tree.tag_configure("even",  background="#f0f0f5")
        self.tree.tag_configure("relay", background="#e8f4fd", foreground=ACCENT2)

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)

    # ── PDF LİSTESİNİ YENİLE ───────────────────────
    def _refresh_pdf_list(self):
        pdf_files  = [f for f in os.listdir(self.pdf_dir) if f.lower().endswith(".pdf")]
        custom     = self._load_custom_names()

        def get_info(fname):
            if fname in custom:
                return custom[fname]
            return get_competition_info(os.path.join(self.pdf_dir, fname)) or fname

        # Yarış adına göre alfabetik sırala (Türkçe)
        tr_map = str.maketrans("ÇçĞğİıÖöŞşÜü", "CcGgIiOoSsUu")
        pdf_files = sorted(pdf_files, key=lambda f: get_info(f).translate(tr_map).lower())

        for row in self.list_tree.get_children():
            self.list_tree.delete(row)

        self.pdf_files = pdf_files
        self.pdf_infos = []
        combo_values   = []

        for i, f in enumerate(pdf_files):
            info = get_info(f)
            self.pdf_infos.append(info)
            combo_values.append(info)
            tag = "odd" if i % 2 == 0 else "even"
            self.list_tree.insert("", "end", iid=f, tags=(tag,), values=(info, "✏️", "🗑"))

        self.combo["values"] = combo_values
        if combo_values:
            if not self.combo_var.get() or self.combo_var.get() not in combo_values:
                self.combo_var.set(combo_values[0])
            # Otomatik yükleme YOK — kullanıcı manuel seçecek

    # ── LİSTEDE TEK TIKLA ──────────────────────────
    def _list_click(self, event):
        col = self.list_tree.identify_column(event.x)
        row = self.list_tree.identify_row(event.y)
        if not row:
            return
        if col == "#2":   # ✏️ düzenle
            self._start_inline_edit(row)
        elif col == "#3": # 🗑 sil
            self._delete_pdf(row)

    # ── LİSTEDE ÇİFT TIKLA → PDF'İ GOOGLE'DA AÇ ──
    def _open_pdf_in_browser(self, event=None):
        sel = self.list_tree.selection()
        if not sel:
            return
        fname    = sel[0]
        pdf_path = os.path.join(self.pdf_dir, fname)
        # Google Drive Viewer ile aç (yerel dosyaları desteklemez),
        # bunun yerine dosyayı doğrudan tarayıcıda aç
        url = "file:///" + pdf_path.replace("\\", "/").replace(" ", "%20")
        webbrowser.open(url)

    # ── KLASÖR DEĞİŞTİR ────────────────────────────
    def _change_pdf_dir(self):
        new_dir = filedialog.askdirectory(
            title="PDF Klasörünü Seçin (OneDrive, ağ sürücüsü, vb.)",
            initialdir=self.pdf_dir)
        if not new_dir:
            return

        self.pdf_dir = new_dir
        self._save_pdf_dir(new_dir)
        self.lbl_pdf_dir.config(text=new_dir)

        self.results     = []
        self.current_pdf = None
        self._clear_table()
        self.lbl_load_status.config(text="")
        self.combo_var.set("")
        self._refresh_pdf_list()

        messagebox.showinfo("Klasör Değiştirildi",
            f"PDF klasörü değiştirildi:\n{new_dir}\n\nBu ayar hatırlanacak.")

    # ── PDF EKLE ───────────────────────────────────
    def _add_pdf(self):
        paths = filedialog.askopenfilenames(
            title="PDF Seçin",
            filetypes=[("PDF Dosyaları", "*.pdf"), ("Tüm Dosyalar", "*.*")])
        if not paths:
            return

        for src in paths:
            fname = os.path.basename(src)
            dest  = os.path.join(self.pdf_dir, fname)

            if os.path.exists(dest) and src != dest:
                if not messagebox.askyesno("Dosya Var",
                        f"'{fname}' zaten mevcut. Üzerine yazılsın mı?"):
                    continue

            if src != dest:
                shutil.copy2(src, dest)

            if self.list_tree.exists(fname):
                self.list_tree.delete(fname)
            self.list_tree.insert("", "end", iid=fname, tags=("loading",),
                                   values=("⏳ Okunuyor...", "", ""))
            self.update()

            def read_info(dest=dest, fname=fname):
                info = get_competition_info(dest) or fname
                self.after(0, lambda i=info, f=fname: self._update_list_row(f, i))

            threading.Thread(target=read_info, daemon=True).start()

    def _update_list_row(self, fname, info):
        if self.list_tree.exists(fname):
            self.list_tree.item(fname, tags=("ok",), values=(info, "✏️", "🗑"))
        self._refresh_pdf_list()

        if info in self.combo["values"]:
            self.combo_var.set(info)
            self.current_pdf = None
            self._on_pdf_select()

    # ── INLINE DÜZENLEME ───────────────────────────
    def _start_inline_edit(self, fname):
        # Önce açık edit varsa kapat
        self._close_inline_edit(save=False)

        try:
            idx = self.pdf_files.index(fname)
            current_info = self.pdf_infos[idx]
        except ValueError:
            return

        # Satırın ekran koordinatlarını bul
        bbox = self.list_tree.bbox(fname, "#1")
        if not bbox:
            return
        x, y, w, h = bbox

        # Treeview'in canvas içindeki konumunu hesapla
        tx = self.list_tree.winfo_x()
        ty = self.list_tree.winfo_y()

        var = tk.StringVar(value=current_info)
        entry = tk.Entry(self.list_tree, textvariable=var,
                         bg="#fffde7", fg=FG, insertbackground=FG,
                         font=("Segoe UI", 10), relief="solid", bd=1)
        entry.place(x=x + 4, y=y + 1, width=w - 8, height=h - 2)
        entry.select_range(0, "end")
        entry.focus_set()

        self._edit_entry = entry
        self._edit_iid   = fname

        def save(e=None):
            new_name = var.get().strip()
            if new_name and new_name != current_info:
                self._save_custom_name(fname, new_name)
            self._close_inline_edit(save=False)

        def cancel(e=None):
            self._close_inline_edit(save=False)

        entry.bind("<Return>",  save)
        entry.bind("<Escape>",  cancel)
        entry.bind("<FocusOut>", save)

    def _close_inline_edit(self, save=True):
        if self._edit_entry:
            self._edit_entry.destroy()
            self._edit_entry = None
            self._edit_iid   = None

    def _save_custom_name(self, fname, new_name):
        """Özel yarış adını ayar dosyasına kaydet ve listeyi yenile"""
        names_file = os.path.join(self.pdf_dir, ".custom_names.txt")
        names = {}
        if os.path.exists(names_file):
            try:
                with open(names_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            names[parts[0]] = parts[1]
            except Exception:
                pass
        names[fname] = new_name
        try:
            with open(names_file, "w", encoding="utf-8") as f:
                for k, v in names.items():
                    f.write(f"{k}\t{v}\n")
        except Exception:
            pass
        self._refresh_pdf_list()
        # Combo'yu da güncelle
        if new_name in self.combo["values"]:
            self.combo_var.set(new_name)

    def _load_custom_names(self):
        """Kaydedilmiş özel isimleri yükle"""
        names_file = os.path.join(self.pdf_dir, ".custom_names.txt")
        names = {}
        if os.path.exists(names_file):
            try:
                with open(names_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            names[parts[0]] = parts[1]
            except Exception:
                pass
        return names

    # ── PDF SİL ────────────────────────────────────
    def _delete_pdf(self, fname=None):
        if fname is None:
            sel = self.list_tree.selection()
            if not sel:
                messagebox.showinfo("Bilgi", "Silmek için bir yarış seçin.")
                return
            fname = sel[0]
        if not messagebox.askyesno("Emin misiniz?", f"'{fname}' silinsin mi?"):
            return
        path = os.path.join(self.pdf_dir, fname)
        if os.path.exists(path):
            os.remove(path)
        # Cache dosyasını da sil
        cache_path = os.path.join(self.pdf_dir, ".cache", fname + ".cache")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception:
                pass
        self._refresh_pdf_list()
        self.results     = []
        self.current_pdf = None
        self._clear_table()
        self.lbl_load_status.config(text="")
        self.combo_var.set("")

    # ── PDF SEÇİLDİ ────────────────────────────────
    def _on_pdf_select(self, event=None):
        if self._loading:
            return
        selected_info = self.combo_var.get()
        if not selected_info:
            return

        pdf_path = None
        for f, info in zip(self.pdf_files, self.pdf_infos):
            if info == selected_info:
                pdf_path = os.path.join(self.pdf_dir, f)
                break

        if not pdf_path or pdf_path == self.current_pdf:
            return

        self._loading = True
        self._clear_table()
        self.lbl_load_status.config(text="⏳ PDF yükleniyor...", fg=WARNING)
        self.entry.config(state="disabled")
        self.update()

        def load(path=pdf_path):
            r = parse_pdf(path)
            self.after(0, lambda p=path, res=r: self._on_loaded(p, res))

        threading.Thread(target=load, daemon=True).start()

    def _on_loaded(self, pdf_path, count_or_results):
        self._loading    = False
        # count_or_results eski çağrılarla uyumluluk için
        if isinstance(count_or_results, list):
            self.results     = count_or_results
            self.current_pdf = pdf_path
            count = len(count_or_results)
        else:
            count = count_or_results
        self.lbl_load_status.config(
            text=f"✅ {count} sonuç" if count else "❌ Sonuç yok",
            fg=SUCCESS if count else DANGER)
        self.entry.config(state="normal")
        self.entry.focus()

    # ── SPORCU ARA ─────────────────────────────────
    def _search(self):
        name = self.search_var.get().strip()
        if not name:
            return
        if not self.results:
            messagebox.showwarning("Uyarı",
                "Önce bir yarış seçin ve yüklenmesini bekleyin.")
            return

        matches = search_athlete(self.results, name)
        self._clear_table()

        if not matches:
            self.lbl_count.config(text=f"'{name}' bulunamadı", fg=WARNING)
            return

        self.lbl_count.config(text=f"{len(matches)} sonuç bulundu", fg=SUCCESS)

        for i, r in enumerate(matches):
            is_relay = r["event"].get("is_relay", False)
            tag = "relay" if is_relay else ("odd" if i % 2 == 0 else "even")
            self.tree.insert("", "end", tags=(tag,), values=(
                r["event"]["event"],
                ("🏳 " if is_relay else "") + r["event"]["race"],
                r["event"]["gender"],
                r["age_group"],
                r["rank"],
                r["time"],
                r.get("round", "") or "-",
                r["club"],
                r["birth_year"],
            ))

    def _clear_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.lbl_count.config(text="")


if __name__ == "__main__":
    app = App()
    app.mainloop()
