import feedparser
import json
import os
import hashlib
import requests
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────
OUTPUT_FILE   = "data/berita.json"
SEEN_FILE     = "data/seen_ids.json"
MAX_PER_FEED  = 10          # max artikel per feed per run
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

RSS_FEEDS = [
    {"name": "Antara - Top News",         "url": "https://www.antaranews.com/rss/top-news"},
    {"name": "Antara - Ekonomi",          "url": "https://www.antaranews.com/rss/ekonomi"},
    {"name": "Antara - Nasional",         "url": "https://www.antaranews.com/rss/nas.xml"},
    {"name": "Antara - Olahraga",         "url": "https://www.antaranews.com/rss/ork.xml"},
    {"name": "Antara - Teknologi",        "url": "https://www.antaranews.com/rss/tek.xml"},
    {"name": "Republika - Utama",         "url": "https://www.republika.co.id/rss"},
    {"name": "Republika - Nasional",      "url": "https://www.republika.co.id/rss/nasional/"},
    {"name": "Republika - Internasional", "url": "https://www.republika.co.id/rss/internasional/"},
    {"name": "Tribunnews",                "url": "https://www.tribunnews.com/rss"},
    {"name": "Merdeka",                   "url": "https://www.merdeka.com/feed/"},
    {"name": "Suara.com",                 "url": "https://www.suara.com/rss"},
    {"name": "Kontan - Keuangan",         "url": "https://rss.kontan.co.id/news/keuangan"},
    {"name": "Kontan - Nasional",         "url": "https://rss.kontan.co.id/news/nasional"},
    {"name": "VIVA",                      "url": "https://www.viva.co.id/get/all"},
    {"name": "Sindonews",                 "url": "https://www.sindonews.com/feed"},
    {"name": "Liputan6 - News",           "url": "https://feed.liputan6.com/rss/news"},
    {"name": "Liputan6 - Bola",           "url": "https://feed.liputan6.com/rss/bola"},
    {"name": "Liputan6 - Tekno",          "url": "https://feed.liputan6.com/rss/tekno"},
    {"name": "Liputan6 - Lifestyle",      "url": "https://feed.liputan6.com/rss/lifestyle"},
    {"name": "Liputan6 - Regional",       "url": "https://feed.liputan6.com/rss/regional"},
    {"name": "Detik - Semua",             "url": "https://rss.detik.com/index.php/detikcom"},
    {"name": "Detik - Finance",           "url": "https://rss.detik.com/index.php/finance"},
    {"name": "Detik - Sport",             "url": "https://rss.detik.com/index.php/sport"},
    {"name": "Detik - Otomotif",          "url": "https://rss.detik.com/index.php/otomotif"},
    {"name": "Detik - Hot",               "url": "https://rss.detik.com/index.php/hot"},
    {"name": "JPNN",                      "url": "https://www.jpnn.com/index.php?mib=rss"},
    {"name": "Media Indonesia",           "url": "https://mediaindonesia.com/rss"},
    {"name": "VOA Indonesia",             "url": "https://www.voaindonesia.com/api/epiqq"},
    {"name": "Tirto.id",                  "url": "https://tirto.id/sitemap/r/google-discover"},
    {"name": "CNN Indonesia",             "url": "https://www.cnnindonesia.com/rss"},
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def make_id(url: str) -> str:
    """Buat hash unik dari URL artikel."""
    return hashlib.md5(url.encode()).hexdigest()

def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_discord(new_count: int, failed_feeds: list, total_articles: int):
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK tidak diset, skip notifikasi.")
        return

    color = 0x57F287 if new_count > 0 else 0x95A5A6
    timestamp = datetime.now(timezone.utc).isoformat()

    failed_text = "\n".join(f"• {f}" for f in failed_feeds) if failed_feeds else "Tidak ada ✅"

    payload = {
        "embeds": [{
            "title": "📰 RSS Fetcher — Update Berita",
            "color": color,
            "fields": [
                {"name": "🆕 Artikel Baru",    "value": str(new_count),    "inline": True},
                {"name": "📦 Total Tersimpan", "value": str(total_articles), "inline": True},
                {"name": "⚠️ Feed Gagal",      "value": failed_text,       "inline": False},
            ],
            "footer": {"text": "RSS Auto Fetcher"},
            "timestamp": timestamp,
        }]
    }

    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        r.raise_for_status()
        print(f"✅ Notifikasi Discord terkirim ({new_count} artikel baru).")
    except Exception as e:
        print(f"❌ Gagal kirim Discord: {e}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    seen_ids: set = set(load_json(SEEN_FILE, []))
    existing: list = load_json(OUTPUT_FILE, [])

    new_articles = []
    failed_feeds  = []

    for feed_info in RSS_FEEDS:
        name = feed_info["name"]
        url  = feed_info["url"]
        print(f"📡 Fetching: {name} ...", end=" ")

        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                raise ValueError(parsed.bozo_exception)

            count = 0
            for entry in parsed.entries[:MAX_PER_FEED]:
                link    = entry.get("link", "")
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                pub     = entry.get("published", "")

                if not link or not title:
                    continue

                uid = make_id(link)
                if uid in seen_ids:
                    continue

                seen_ids.add(uid)
                new_articles.append({
                    "id":        uid,
                    "source":    name,
                    "title":     title,
                    "url":       link,
                    "summary":   summary,
                    "published": pub,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
                count += 1

            print(f"✅ {count} baru")

        except Exception as e:
            print(f"❌ Gagal: {e}")
            failed_feeds.append(name)

    # Gabungkan artikel baru di depan, tapi batasi total agar tidak membengkak
    MAX_TOTAL = 5000
    all_articles = new_articles + existing
    all_articles = all_articles[:MAX_TOTAL]

    save_json(OUTPUT_FILE, all_articles)
    save_json(SEEN_FILE, list(seen_ids))

    print(f"\n📊 Selesai: {len(new_articles)} artikel baru | Total: {len(all_articles)}")

    send_discord(
        new_count      = len(new_articles),
        failed_feeds   = failed_feeds,
        total_articles = len(all_articles),
    )

if __name__ == "__main__":
    main()
