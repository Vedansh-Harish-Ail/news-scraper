from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
import requests
import json
from datetime import datetime
from textblob import TextBlob
from urllib.parse import urlparse
import io
import csv
import base64

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ========= CONFIG ========= #
NEWS_API_KEY  = os.getenv("NEWS_API_KEY")
NEWS_API_BASE = "https://newsapi.org/v2"
API_HEADERS   = {"X-Api-Key": NEWS_API_KEY}

# Known NewsAPI source IDs for fast top-headlines lookup
SOURCE_MAP = {
    "bbc.co.uk":        "bbc-news",
    "bbc.com":          "bbc-news",
    "cnn.com":          "cnn",
    "reuters.com":      "reuters",
    "theguardian.com":  "the-guardian-uk",
    "indiatoday.in":    None,               # no official NewsAPI source ID
}

PRESET_SITES = [
    {"label": "🇬🇧  BBC News",    "domain": "bbc.co.uk"},
    {"label": "📺  CNN",           "domain": "cnn.com"},
    {"label": "📡  Reuters",       "domain": "reuters.com"},
    {"label": "🗞️  The Guardian", "domain": "theguardian.com"},
    {"label": "🇮🇳  India Today",  "domain": "indiatoday.in"},
]

# ========= HELPERS ========= #
def clean_domain(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("http"):
        raw = "https://" + raw
    return urlparse(raw).netloc.lstrip("www.")

def sentiment_label(text: str) -> str:
    try:
        p = TextBlob(text).sentiment.polarity
        if p >  0.1: return "😊 Positive"
        if p < -0.1: return "😡 Negative"
        return "😑 Neutral"
    except:
        return "❓ Unknown"

# ========= API ========= #
def fetch_top_headlines(domain: str):
    source_id = SOURCE_MAP.get(domain)
    if source_id:
        params = {"sources": source_id, "pageSize": 30, "apiKey": NEWS_API_KEY}
        r = requests.get(f"{NEWS_API_BASE}/top-headlines", params=params,
                         headers=API_HEADERS, timeout=12)
    else:
        # Fall back to everything endpoint filtered by domain
        params = {"domains": domain, "pageSize": 30,
                  "sortBy": "publishedAt", "apiKey": NEWS_API_KEY}
        r = requests.get(f"{NEWS_API_BASE}/everything", params=params,
                         headers=API_HEADERS, timeout=12)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        return None, data.get("message", "Unknown API error")
    return data.get("articles", []), None

def fetch_all_articles(domain: str):
    params = {"domains": domain, "pageSize": 30,
              "sortBy": "publishedAt", "apiKey": NEWS_API_KEY}
    r = requests.get(f"{NEWS_API_BASE}/everything", params=params,
                     headers=API_HEADERS, timeout=12)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        return None, data.get("message", "Unknown API error")
    return data.get("articles", []), None

def articles_to_items(articles: list) -> list:
    items = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        items.append({
            "headline":    title,
            "link":        a.get("url") or "",
            "source":      (a.get("source") or {}).get("name") or "",
            "published":   (a.get("publishedAt") or "")[:10],
            "description": (a.get("description") or "").strip(),
        })
    return items

# ========= EXPORT ========= #
def export_to_csv(data: list, label: str):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", "Headline", "Source", "Published", "Sentiment", "Link"])
    for i, item in enumerate(data, 1):
        w.writerow([i, item.get("headline",""), item.get("source",""),
                    item.get("published",""), item.get("sentiment",""),
                    item.get("link","")])
    put_file(
        f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        buf.getvalue().encode("utf-8"),
        f"Download CSV — {label}"
    )

# ========= MAIN ========= #
def main():
    set_env(title="📰 News Scraper", output_animation=False)

    # ---- Styles ----
    put_html("""
    <style>
        :root {
            --grad: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --accent: #667eea;
            --bg: #f4f6fc;
            --card: #ffffff;
            --border: #e0e4f0;
            --text: #212529;
            --muted: #6c757d;
            --link: #5e72e4;
        }
        html, body { background: var(--bg) !important; color: var(--text) !important; }
        footer { display: none !important; }

        /* Header */
        .app-header {
            background: var(--grad);
            color: #fff;
            border-radius: 14px;
            padding: 22px 26px;
            margin-bottom: 22px;
        }
        .app-header h1 { margin: 0 0 5px; font-size: 1.85rem; }
        .app-header p  { margin: 0; opacity: .85; font-size: .95rem; }

        /* Preset grid */
        .preset-section { margin-bottom: 18px; }
        .preset-label   { font-weight: 600; color: #444; margin-bottom: 10px; font-size: .9rem; }
        .preset-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
        }
        @media (max-width: 680px) { .preset-grid { grid-template-columns: repeat(2, 1fr); } }

        .preset-btn {
            padding: 12px 8px;
            border: 2px solid var(--border);
            border-radius: 10px;
            background: var(--card);
            cursor: pointer;
            font-size: .82rem;
            font-weight: 600;
            color: var(--text);
            transition: border-color .18s, background .18s, transform .12s;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .preset-btn:hover  { border-color: var(--accent); background: #eef0ff; transform: translateY(-1px); }
        .preset-btn.active { border-color: var(--accent); background: #eef0ff; box-shadow: 0 0 0 3px #c5caff55; }

        /* Table */
        table { width: 100%; border-collapse: collapse; font-size: .9rem; }
        th { background: #eef0ff !important; color: #3949ab !important;
             padding: 10px 13px; text-align: left; font-weight: 600; }
        td { padding: 9px 13px; vertical-align: top;
             border-bottom: 1px solid var(--border) !important;
             background: var(--card) !important; }
        tr:hover td { background: #f8f9ff !important; }
        a  { color: var(--link) !important; text-decoration: none; }
        a:hover { text-decoration: underline; }

        .badge-source {
            display: inline-block;
            background: #e8eaf6; color: #3949ab;
            border-radius: 6px; padding: 1px 8px;
            font-size: .77rem; white-space: nowrap;
        }
        .badge-date { color: var(--muted); font-size: .77rem; }

        /* Spinner */
        .spinner-wrap { text-align: center; padding: 36px 0; }
        .spinner {
            border: 6px solid #eef0ff;
            border-top: 6px solid var(--accent);
            border-radius: 50%;
            width: 50px; height: 50px;
            animation: spin .85s linear infinite;
            margin: 0 auto 14px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>

    <div class="app-header">
        <h1>📰 News Scraper</h1>
        <p>Real-time headlines powered by NewsAPI &mdash; with sentiment analysis &amp; text-to-speech</p>
    </div>

    <!-- Quick-select preset grid -->
    <div class="preset-section">
        <div class="preset-label">⚡ Quick select a news source:</div>
        <div class="preset-grid">
            <button class="preset-btn" onclick="pickPreset('bbc.co.uk', this)">🇬🇧 BBC News</button>
            <button class="preset-btn" onclick="pickPreset('cnn.com', this)">📺 CNN</button>
            <button class="preset-btn" onclick="pickPreset('reuters.com', this)">📡 Reuters</button>
            <button class="preset-btn" onclick="pickPreset('theguardian.com', this)">🗞️ The Guardian</button>
            <button class="preset-btn" onclick="pickPreset('indiatoday.in', this)">🇮🇳 India Today</button>
        </div>
    </div>

    <script>
    function pickPreset(domain, el) {
        // Highlight button
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        el.classList.add('active');
        // Fill PyWebIO URL input
        const inp = document.querySelector('input[name="url"]');
        if (inp) {
            inp.value = domain;
            ['input','change'].forEach(ev =>
                inp.dispatchEvent(new Event(ev, {bubbles: true}))
            );
        }
    }
    </script>
    """)

    # ---- Form ----
    form = input_group("", [
        select("Mode", name="mode", options=[
            "Top Headlines",
            "All Articles (latest)",
        ], value="Top Headlines"),
        input("Website / Domain", name="url", type=TEXT,
              placeholder="e.g. bbc.co.uk or https://example.com",
              required=True),
    ])

    mode   = form["mode"]
    raw    = form["url"]
    domain = clean_domain(raw)
    label  = f"{domain} — {mode}"

    # ---- Fetch ----
    with use_scope("loading", clear=True):
        put_html("""
        <div class="spinner-wrap">
            <div class="spinner"></div>
            <p><strong>Fetching headlines…</strong></p>
        </div>
        """)
        try:
            if mode == "Top Headlines":
                articles, err = fetch_top_headlines(domain)
            else:
                articles, err = fetch_all_articles(domain)
        except Exception as e:
            articles, err = None, str(e)

    clear("loading")

    if err:
        put_error(f"NewsAPI error: {err}")
        put_buttons(["🔄 Try Again"], onclick=lambda _: run_js("location.reload()"))
        return

    items = articles_to_items(articles or [])
    if not items:
        put_warning("No articles found. Try a different website or mode.")
        put_buttons(["🔄 Try Again"], onclick=lambda _: run_js("location.reload()"))
        return

    # Sentiment
    for item in items:
        item["sentiment"] = sentiment_label(item["headline"])

    put_success(f"✅ {len(items)} headlines from {label}")

    # ---- Table ----
    with use_scope("results", clear=True):
        rows = []
        for i, item in enumerate(items, 1):
            title = item.get("headline","").strip()
            link  = item.get("link","").strip()
            src   = item.get("source","")
            pub   = item.get("published","")
            sent  = item.get("sentiment","")

            title_cell = (
                put_html(f'<a href="{link}" target="_blank">{title}</a>')
                if link.startswith("http") else put_text(title)
            )
            meta_cell = put_html(
                f'<span class="badge-source">{src}</span>'
                f'<br><span class="badge-date">{pub}</span>'
            )
            rows.append([put_text(str(i)), title_cell, meta_cell, put_text(sent)])
        put_table([["#", "Headline", "Source / Date", "Sentiment"]] + rows)

    # ---- Speech JS ----
    put_html("""
    <script>
    window.__ns = {
        hl:[], idx:0, going:false, paused:false,
        start(items) {
            const s=window.speechSynthesis; if(!s){alert('Speech not supported');return;}
            this.stop(); this.hl=items; this.idx=0; this.going=true; this.paused=false;
            const p=new SpeechSynthesisUtterance("Reading headlines.");
            p.onend=()=>this._next(); s.speak(p);
        },
        _next() {
            const s=window.speechSynthesis;
            if(!this.going||this.paused||this.idx>=this.hl.length) return;
            const t=(this.hl[this.idx].headline||"").trim();
            if(!t){this.idx++;this._next();return;}
            const u=new SpeechSynthesisUtterance(`Headline ${this.idx+1}. ${t}`);
            u.onend=()=>{this.idx++;this._next();};
            s.speak(u);
        },
        pause()  { const s=window.speechSynthesis; if(s.speaking) s.pause(); this.paused=true; },
        resume() {
            const s=window.speechSynthesis;
            if(s.paused){s.resume();this.paused=false;}
            else if(!s.speaking&&this.going){this.paused=false;this._next();}
        },
        stop() {
            const s=window.speechSynthesis;
            if(s&&s.speaking) s.cancel();
            this.going=false; this.paused=false; this.idx=0; this.hl=[];
        }
    };
    </script>
    """)

    # ---- Action buttons ----
    def on_btn(btn):
        if btn == "again":
            run_js("location.reload()")
        elif btn == "csv":
            export_to_csv(items, label)
        elif btn == "read":
            safe = [{"headline": it.get("headline","")} for it in items]
            payload = base64.b64encode(json.dumps(safe).encode()).decode("ascii")
            run_js(f"window.__ns.start(JSON.parse(atob('{payload}')))")
        elif btn == "pause":
            run_js("window.__ns.pause()")
        elif btn == "resume":
            run_js("window.__ns.resume()")
        elif btn == "stop":
            run_js("window.__ns.stop()")

    put_buttons([
        {"label": "🔄 New Search",     "value": "again",  "color": "primary"},
        {"label": "📄 Export CSV",      "value": "csv",    "color": "info"},
        {"label": "▶ Read Headlines",  "value": "read",   "color": "secondary"},
        {"label": "⏸ Pause",           "value": "pause",  "color": "warning"},
        {"label": "⏯ Continue",        "value": "resume", "color": "light"},
        {"label": "🛑 Stop",            "value": "stop",   "color": "dark"},
    ], onclick=on_btn)


if __name__ == "__main__":
    start_server(main, port=8080, debug=True)
