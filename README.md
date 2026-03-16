# 📰 RSS Berita Indonesia — Auto Fetcher

Scraper otomatis untuk mengumpulkan berita dari **30 portal berita Indonesia**, berjalan setiap jam via GitHub Actions, menyimpan hasil ke JSON, dan mengirim notifikasi ke Discord.

[![📰 RSS Berita Indonesia — Auto Fetcher](https://github.com/harukayuka2/news-mirai/actions/workflows/rss_fetcher.yml/badge.svg)](https://github.com/harukayuka2/news-mirai/actions/workflows/rss_fetcher.yml)
---

## ✨ Fitur

- 📡 Fetch dari **30 RSS feed** portal berita Indonesia
- 🔁 **Filter duplikat** otomatis via hash MD5 URL artikel
- 💾 Simpan ke **`data/berita.json`** dan push ke repo otomatis
- 🔔 **Notifikasi Discord** embed setiap ada artikel baru
- ⏱️ Berjalan **setiap jam** via GitHub Actions scheduler
- 🚫 Skip commit kalau tidak ada artikel baru (anti spam)

---

## 📁 Struktur Repo

```
├── .github/
│   └── workflows/
│       └── rss_fetcher.yml   # Workflow GitHub Actions
├── data/
│   ├── berita.json           # Hasil artikel tersimpan (auto-generated)
│   └── seen_ids.json         # Hash artikel yang sudah pernah diambil (auto-generated)
├── fetch_rss.py              # Script utama fetcher
├── requirements.txt          # Dependensi Python
└── README.md
```

---

## ⚙️ Setup

### 1. Fork / Clone repo ini

```bash
git clone https://github.com/username/nama-repo.git
cd nama-repo
```

### 2. Tambahkan Secrets di GitHub

Buka **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Keterangan |
|---|---|
| `PAT_TOKEN` | Personal Access Token GitHub (scope: `repo`) |
| `DISCORD_WEBHOOK` | URL webhook channel Discord tujuan notifikasi |

> 💡 Cara buat PAT: **github.com → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token** — centang scope `repo`.

### 3. Aktifkan GitHub Actions

Masuk ke tab **Actions** di repo → klik **Enable Actions** jika belum aktif.

Untuk test langsung tanpa menunggu jadwal, klik **Run workflow** secara manual.

---

## 📦 Sumber RSS

| No | Portal | Topik |
|---|---|---|
| 1 | Antara | Top News |
| 2 | Antara | Ekonomi |
| 3 | Antara | Nasional |
| 4 | Antara | Olahraga |
| 5 | Antara | Teknologi |
| 6 | Republika | Utama |
| 7 | Republika | Nasional |
| 8 | Republika | Internasional |
| 9 | Tribunnews | Semua Berita |
| 10 | Merdeka | Semua Berita |
| 11 | Suara.com | Semua Berita |
| 12 | Kontan | Keuangan |
| 13 | Kontan | Nasional |
| 14 | VIVA | Semua Berita |
| 15 | Sindonews | Semua Berita |
| 16 | Liputan6 | News |
| 17 | Liputan6 | Bola |
| 18 | Liputan6 | Tekno |
| 19 | Liputan6 | Lifestyle |
| 20 | Liputan6 | Regional |
| 21 | Detik | Semua Berita |
| 22 | Detik | Finance |
| 23 | Detik | Sport |
| 24 | Detik | Otomotif |
| 25 | Detik | Hot / Entertainment |
| 26 | JPNN | Semua Berita |
| 27 | Media Indonesia | Semua Berita |
| 28 | VOA Indonesia | Terkini |
| 29 | Tirto.id | Google Discover |
| 30 | CNN Indonesia | Semua Berita |

---

## 📊 Format Data JSON

Setiap artikel tersimpan dalam format berikut:

```json
{
  "id": "a1b2c3d4e5f6...",
  "source": "Detik - Finance",
  "title": "Judul artikel berita",
  "url": "https://finance.detik.com/...",
  "summary": "Ringkasan singkat artikel...",
  "published": "Mon, 17 Mar 2025 10:00:00 +0700",
  "fetched_at": "2025-03-17T03:00:00+00:00"
}
```

---

## 🔔 Contoh Notifikasi Discord

Bot akan mengirim embed seperti ini setiap ada artikel baru:

```
📰 RSS Fetcher — Update Berita
┌─────────────────────────────┐
│ 🆕 Artikel Baru   │ 47      │
│ 📦 Total Tersimpan│ 1.203   │
│ ⚠️ Feed Gagal     │ Tidak ada ✅ │
└─────────────────────────────┘
```

---

## 🛠️ Konfigurasi

Edit bagian atas `fetch_rss.py` untuk menyesuaikan:

```python
MAX_PER_FEED = 10     # Maksimal artikel per feed per run
MAX_TOTAL    = 5000   # Batas total artikel tersimpan di JSON
```

---

## 📋 Requirements

```
feedparser==6.0.11
requests==2.32.3
```

Python **3.11+** direkomendasikan.

---

## 📄 Lisensi

MIT License — bebas digunakan dan dimodifikasi.
