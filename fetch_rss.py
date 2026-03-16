import feedparser
import json
import os
import hashlib
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────
OUTPUT_FILE     = "data/berita.json"
SEEN_FILE       = "data/seen_ids.json"
MAX_PER_FEED    = 10
MAX_TOTAL       = 5000
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
WIB             = ZoneInfo("Asia/Jakarta")

# User-Agent agar tidak diblokir server
USER_AGENT = "Mozilla/5.0 (compatible; RSS-Fetcher-Bot/1.0; +https://github.com/username/repo)"
feedparser.USER_AGENT = USER_AGENT

RSS_FEEDS = [
    {"name": "Antara - Top News",         "url": "https://www.antaranews.com/rss/top-news"},
    {"name": "Antara - Ekonomi",          "url": "https://www.antaranews.com/rss/ekonomi"},
    {"name": "Antara - Nasional",         "url": "https://www.antaranews.com/rss/nasional"},
    {"name": "Antara - Olahraga",         "url": "https://www.antaranews.com/rss/olahraga"},
    {"name": "Antara - Teknologi",        "url": "https://www.antaranews.com/rss/teknologi"},
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
# HTTP SESSION dengan retry & timeout
# ─────────────────────────────────────────────
def make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session

SESSION = make_session()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def make_id(url: str) -> str:
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

def fetch_feed(url: str):
    """Fetch RSS via requests dulu baru parse, agar timeout & User-Agent terkontrol."""
    resp = SESSION.get(url, timeout=10)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return feedparser.parse(resp.text)

def send_discord(new_count: int, failed_feeds: list, total_articles: int, last_fetched: str):
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK tidak diset, skip notifikasi.")
        return

    color = 0x57F287 if new_count > 0 else 0x95A5A6

    # Potong daftar gagal agar tidak melebihi limit 1024 karakter Discord
    if failed_feeds:
        shown = failed_feeds[:10]
        failed_text = "\n".join(f"• {f}" for f in shown)
        if len(failed_feeds) > 10:
            failed_text += f"\n... dan {len(failed_feeds) - 10} lainnya"
    else:
        failed_text = "Tidak ada ✅"

    payload = {
        "embeds": [{
            "title": "📰 RSS Fetcher — Update Berita",
            "color": color,
            "fields": [
                {"name": "🆕 Artikel Baru",    "value": str(new_count),      "inline": True},
                {"name": "📦 Total Tersimpan", "value": str(total_articles), "inline": True},
                {"name": "🕐 Last Fetch (WIB)", "value": last_fetched,       "inline": False},
                {"name": "⚠️ Feed Gagal",       "value": failed_text,        "inline": False},
            ],
            "footer": {"text": "RSS Auto Fetcher"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    # Load data existing — support format lama (list) dan baru (dict dengan "articles")
    raw = load_json(OUTPUT_FILE, [])
    existing: list = raw.get("articles", raw) if isinstance(raw, dict) else raw

    seen_ids: set = set(load_json(SEEN_FILE, []))

    new_articles = []
    failed_feeds  = []

    for feed_info in RSS_FEEDS:
        name = feed_info["name"]
        url  = feed_info["url"]
        print(f"📡 Fetching: {name} ...", end=" ", flush=True)

        try:
            parsed = fetch_feed(url)

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
                    "id":         uid,
                    "source":     name,
                    "title":      title,
                    "url":        link,
                    "summary":    summary,
                    "published":  pub,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
                count += 1

            print(f"✅ {count} baru")

        except Exception as e:
            print(f"❌ Gagal: {e}")
            failed_feeds.append(name)

    all_articles = (new_articles + existing)[:MAX_TOTAL]

    # Waktu WIB untuk metadata
    now_wib       = datetime.now(WIB)
    last_fetched  = now_wib.strftime("%Y-%m-%d %H:%M WIB")

    # Simpan dengan struktur root yang rapi
    output_data = {
        "last_fetched":  last_fetched,
        "fetch_count":   len(all_articles),
        "new_this_run":  len(new_articles),
        "articles":      all_articles,
    }

    save_json(OUTPUT_FILE, output_data)
    save_json(SEEN_FILE, list(seen_ids))

    print(f"\n📊 Selesai: {len(new_articles)} artikel baru | Total: {len(all_articles)} | {last_fetched}")

    send_discord(
        new_count      = len(new_articles),
        failed_feeds   = failed_feeds,
        total_articles = len(all_articles),
        last_fetched   = last_fetched,
    )

if __name__ == "__main__":
    main()
