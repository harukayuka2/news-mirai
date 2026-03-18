"""
news_summary.py — AI News Summarizer untuk Mirai Bot
Membaca data/berita.json, merangkum setiap artikel via Gemini API (REST v1),
lalu menyimpan hasil ke data/summary.json.

Env vars yang dibutuhkan:
  GEMINI_API_KEY   — API key Google AI Studio

Cara pakai:
  python news_summary.py
  python news_summary.py --limit 50   # hanya proses 50 artikel terbaru
  python news_summary.py --batch 10   # ukuran batch per request Gemini
"""

import argparse
import json
import os
import sys
import time
import requests
from datetime import datetime, timezone

# ─── Konfigurasi ─────────────────────────────────────────────────────────────

MODEL          = "gemini-2.5-flash"          # Ganti ke "gemini-2.5-flash" jika tersedia
API_KEY        = os.environ.get("GEMINI", "")
API_URL        = (
    f"https://generativelanguage.googleapis.com/v1/models/{MODEL}"
    f":generateContent?key={API_KEY}"
)

INPUT_FILE     = "data/berita.json"
OUTPUT_FILE    = "data/summary.json"

DEFAULT_LIMIT  = 100   # Berapa artikel terbaru yang diproses (0 = semua)
DEFAULT_BATCH  = 20    # Artikel per satu request ke Gemini
RETRY_MAX      = 3     # Maks retry per batch
RETRY_DELAY    = 5     # Detik antar retry
REQUEST_DELAY  = 1.2   # Detik antar batch (rate limit aman)

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Kamu adalah asisten penyusun ringkasan berita Indonesia yang ringkas dan netral.
Kamu akan menerima daftar artikel berita dalam format JSON.
Tugasmu: tulis ulang field "summary" menjadi 1–2 kalimat padat dalam Bahasa Indonesia
yang informatif dan mudah dipahami. Jangan tambahkan opini atau informasi di luar konteks.

Kembalikan HANYA JSON array tanpa penjelasan, tanpa markdown code block, tanpa teks lainnya.
Format output setiap elemen:
{
  "source": "<sama persis dengan input>",
  "title": "<sama persis dengan input>",
  "summary": "<ringkasan baru buatanmu, 1–2 kalimat>",
  "fetched_at": "<sama persis dengan input>"
}
""".strip()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_articles(path: str, limit: int) -> list[dict]:
    if not os.path.exists(path):
        print(f"❌ File tidak ditemukan: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        print("❌ berita.json kosong atau bukan array.")
        sys.exit(1)

    # Ambil N artikel terbaru (berdasarkan urutan di file)
    articles = data if limit == 0 else data[-limit:]
    print(f"📂 Loaded {len(data)} artikel, memproses {len(articles)} terbaru.")
    return articles


def extract_fields(articles: list[dict]) -> list[dict]:
    """Hanya ambil 4 field yang relevan untuk dikirim ke Gemini."""
    return [
        {
            "source":     a.get("source", ""),
            "title":      a.get("title", ""),
            "summary":    a.get("summary", ""),
            "fetched_at": a.get("fetched_at", ""),
        }
        for a in articles
    ]


def call_gemini(batch: list[dict]) -> list[dict] | None:
    """Kirim satu batch ke Gemini, kembalikan list dict hasil summarize."""
    user_message = json.dumps(batch, ensure_ascii=False)

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "temperature":    0.3,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = requests.post(API_URL, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            raw_text = (
                data["candidates"][0]["content"]["parts"][0]["text"]
            )

            # Bersihkan fence markdown kalau ada
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```", 2)[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)

            if not isinstance(result, list):
                raise ValueError("Respons Gemini bukan array JSON.")

            return result

        except requests.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            print(f"  ⚠️  HTTP {status} — attempt {attempt}/{RETRY_MAX}")
            if status == 429:
                wait = RETRY_DELAY * attempt * 2
                print(f"  ⏳ Rate limited, tunggu {wait}s...")
                time.sleep(wait)
            elif attempt < RETRY_MAX:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ Gagal setelah {RETRY_MAX} percobaan.")
                return None

        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
            print(f"  ⚠️  Parse error: {e} — attempt {attempt}/{RETRY_MAX}")
            if attempt < RETRY_MAX:
                time.sleep(RETRY_DELAY)
            else:
                return None

        except requests.RequestException as e:
            print(f"  ⚠️  Request error: {e} — attempt {attempt}/{RETRY_MAX}")
            if attempt < RETRY_MAX:
                time.sleep(RETRY_DELAY)
            else:
                return None

    return None


def validate_summary_item(item: dict) -> bool:
    """Pastikan item hasil Gemini punya semua field yang dibutuhkan."""
    required = {"source", "title", "summary", "fetched_at"}
    return required.issubset(item.keys())


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="News Summarizer via Gemini API")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Jumlah artikel terbaru yang diproses (0 = semua, default: {DEFAULT_LIMIT})")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                        help=f"Ukuran batch per request Gemini (default: {DEFAULT_BATCH})")
    args = parser.parse_args()

    # ── Validasi API key ──
    if not API_KEY:
        print("❌ GEMINI_API_KEY tidak ditemukan di environment variable!")
        sys.exit(1)

    print("=" * 55)
    print("  📰 News Summarizer — Mirai Bot")
    print(f"  Model  : {MODEL}")
    print(f"  Input  : {INPUT_FILE}")
    print(f"  Output : {OUTPUT_FILE}")
    print("=" * 55)

    # ── Load & siapkan data ──
    articles     = load_articles(INPUT_FILE, args.limit)
    slimmed      = extract_fields(articles)
    total        = len(slimmed)
    batch_size   = args.batch
    batches      = [slimmed[i:i + batch_size] for i in range(0, total, batch_size)]
    total_batch  = len(batches)

    print(f"🔢 Total batch: {total_batch} (masing-masing ≤{batch_size} artikel)\n")

    # ── Proses batch demi batch ──
    all_summaries: list[dict] = []
    failed_batches: list[int] = []

    for idx, batch in enumerate(batches, start=1):
        print(f"[{idx}/{total_batch}] 🤖 Summarizing {len(batch)} artikel...", end=" ", flush=True)

        result = call_gemini(batch)

        if result is None:
            print(f"❌ Batch {idx} gagal total, dilewati.")
            failed_batches.append(idx)
            # Fallback: simpan artikel asli tanpa perubahan
            all_summaries.extend(batch)
            continue

        # Validasi & fallback per item
        valid_count = 0
        for i, item in enumerate(result):
            if validate_summary_item(item):
                all_summaries.append(item)
                valid_count += 1
            else:
                # Fallback ke data asli jika item tidak valid
                all_summaries.append(batch[i] if i < len(batch) else batch[-1])

        print(f"✅ {valid_count}/{len(batch)} OK")

        if idx < total_batch:
            time.sleep(REQUEST_DELAY)

    # ── Simpan output ──
    os.makedirs("data", exist_ok=True)

    meta = {
        "_meta": {
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "model":         MODEL,
            "total_articles": len(all_summaries),
            "failed_batches": failed_batches,
        }
    }

    # Format: object dengan meta + array articles
    output = {**meta, "articles": all_summaries}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 55)
    print(f"✅ Selesai! {len(all_summaries)} artikel tersimpan ke {OUTPUT_FILE}")
    if failed_batches:
        print(f"⚠️  {len(failed_batches)} batch gagal: {failed_batches}")
    print("=" * 55)


if __name__ == "__main__":
    main()
