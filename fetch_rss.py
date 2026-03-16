import feedparser
import json
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─────────────────────────────────────────────
OUTPUT_FILE  = "data/berita.json"
WIB          = ZoneInfo("Asia/Jakarta")
USER_AGENT   = "Mozilla/5.0 (compatible; RSS-Fetcher-Bot/1.0)"
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
session = requests.Session()
retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://",  HTTPAdapter(max_retries=retries))
session.headers.update({"User-Agent": USER_AGENT})

# ─────────────────────────────────────────────
articles = []

for feed_info in RSS_FEEDS:
    name = feed_info["name"]
    url  = feed_info["url"]
    print(f"📡 {name} ...", end=" ", flush=True)
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)

        for entry in parsed.entries[:10]:
            link    = entry.get("link", "")
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            pub     = entry.get("published", "")
            if not link or not title:
                continue
            articles.append({
                "source":     name,
                "title":      title,
                "url":        link,
                "summary":    summary,
                "published":  pub,
                "user_agent": USER_AGENT,
                "fetched_at": datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB"),
            })

        print(f"✅ {len(parsed.entries[:10])} artikel")
    except Exception as e:
        print(f"❌ {e}")

# ─────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"\n✅ Selesai — {len(articles)} artikel disimpan ke {OUTPUT_FILE}")
