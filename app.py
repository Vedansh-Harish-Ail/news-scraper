from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
from datetime import datetime
from textblob import TextBlob
import io
import csv
import base64

# ========= CONFIG ========= #
NEWS_WEBSITES = {
    "India Today": {
        "url": "https://www.indiatoday.in/",
        "selectors": ["h2", "h3", "a[class*='title']"],
        "filter_length": 20
    },
    "CNN": {
        "url": "https://edition.cnn.com",
        "selectors": ["span[data-editable='headline']", "a[data-analytics*='headline']"],
        "filter_length": 15
    },
    "Custom Website": {
        "url": "",
        "selectors": ["h1", "h2", "h3","h6","a[class*='title']","span[data-editable='headline']", "a[data-analytics*='headline']" ],
        "filter_length": 20
    }
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/115.0 Safari/537.36'
}

# ========= SCRAPER ========= #
def scrape_news(url, selectors, filter_length):
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        headlines = []
        for sel in selectors:
            for el in soup.select(sel):
                text = " ".join(el.get_text(separator=" ", strip=True).split())
                if text and len(text) > filter_length:
                    href = ""
                    if el.name == "a" and el.has_attr("href"):
                        href = el["href"]
                    else:
                        a = el.find_parent("a") or el.find("a")
                        if a and a.has_attr("href"):
                            href = a["href"]
                    link = urljoin(base_url, href) if href else ""
                    headlines.append({"headline": text, "link": link})

        seen = set()
        unique = []
        for h in headlines:
            t = h["headline"]
            if t not in seen:
                seen.add(t)
                unique.append(h)

        return unique[:30] if unique else [{"headline": f"No headlines found on {url}.", "link": ""}]

    except requests.exceptions.RequestException as e:
        return [{"headline": f"Network error: {e}", "link": ""}]
    except Exception as e:
        return [{"headline": f"Unexpected error: {e}", "link": ""}]

# ========= HELPERS ========= #
def sentiment_label(text):
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.1:
            return "😊 Positive"
        if polarity < -0.1:
            return "😡 Negative"
        return "😑 Neutral"
    except:
        return "❓ Unknown"

# ========= EXPORT ========= #
def export_to_csv(headlines_data, website_name):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", "Headline", "Link", "Sentiment"])
    for i, item in enumerate(headlines_data, 1):
        w.writerow([i, item.get("headline", ""), item.get("link", ""), item.get("sentiment", "")])
    put_file(f"news_headlines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
             buf.getvalue().encode("utf-8"),
             f"Download CSV - {website_name}")

# ========= MAIN APP ========= #
def main():
    set_env(title="News Website Scraper", output_animation=False)

    put_html("""
    <style>
        :root {
            --bg-color: white ; --text-color: #212529; --card-bg: #ffffff; --border-color: #dee2e6;
            --header-bg: linear-gradient(135deg, #667eea 0%, #764ba2 100%); --header-text: #ffffff;
            --table-header-bg: #f8f9fa; --table-row-bg: #ffffff; --link-color: #007bff;
        }
        html, body { background-color: var(--bg-color) !important; color: var(--text-color) !important; }
        table, th, td { border-color: var(--border-color) !important; }
        th { background-color: var(--table-header-bg) !important; }
        td { background-color: var(--table-row-bg) !important; }
        a { color: var(--link-color) !important; }
        footer { display: none !important; }
        .spinner {
          border: 8px solid #f3f3f3;
          border-top: 8px solid #3498db;
          border-radius: 50%;
          width: 60px;
          height: 60px;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
    </style>
    """)

    put_html("""
    <div style="background: var(--header-bg); color: var(--header-text); border-radius: 10px; padding: 15px;">
        <h1>📰 News Website Scraper</h1>
        <p>Get the latest headlines from your favorite news websites</p>
    </div>
    """)

    selected = input_group("Select source", [
        select("Choose a news website:", name="website", options=list(NEWS_WEBSITES.keys()), value="India Today"),
        input("Or enter a custom URL:", name="custom_url", type=TEXT, placeholder="e.g., https://www.example.com/news")
    ])

    custom_url = (selected.get("custom_url") or "").strip()
    if custom_url:
        url = custom_url
        website_info = NEWS_WEBSITES["Custom Website"]
        selected_website = f"Custom Website ({urlparse(url).netloc})"
    else:
        selected_website = selected["website"]
        website_info = NEWS_WEBSITES[selected_website]
        url = website_info["url"]

    with use_scope("loading", clear=True):
        put_html("""
        <div style="display:flex;flex-direction:column;align-items:center;">
            <div class="spinner"></div>
            <p><strong>Fetching latest news headlines...</strong></p>
        </div>
        """)
        headlines_data = scrape_news(url, website_info["selectors"], website_info["filter_length"])
    clear("loading")

    for item in headlines_data:
        if "headline" in item:
            item["sentiment"] = sentiment_label(item["headline"])

    if headlines_data and not headlines_data[0]["headline"].startswith(("Error:", "Network error:", "No headlines found")):
        put_success(f"Fetched {len(headlines_data)} headlines from {selected_website}")

        with use_scope("table_scope", clear=True):
            rows = []
            for i, item in enumerate(headlines_data, 1):
                title = item.get("headline", "").strip()
                link = item.get("link", "").strip()
                title_cell = put_html(f'<a href="{link}" target="_blank">{title}</a>') if link.startswith("http") else put_text(title)
                rows.append([put_text(str(i)), title_cell, put_text(item.get("sentiment", ""))])
            put_table([["#", "Headline", "Sentiment"]] + rows)

        # === JavaScript for speech ===
        put_html("""
        <script>
        window.__newsSpeech = {
            headlines: [],
            currentIndex: 0,
            isReading: false,
            paused: false,

            readList: function(items) {
                const synth = window.speechSynthesis;
                if (!synth) { alert('Speech not supported'); return; }

                this.stop();
                this.headlines = items;
                this.currentIndex = 0;
                this.isReading = true;
                this.paused = false;

                const pre = new SpeechSynthesisUtterance("Reading headlines.");
                pre.onend = () => this._speakNext();
                synth.speak(pre);
            },

            _speakNext: function() {
                const synth = window.speechSynthesis;
                if (!this.isReading || this.paused || this.currentIndex >= this.headlines.length) return;

                const t = (this.headlines[this.currentIndex].headline || "").trim();
                if (!t) {
                    this.currentIndex++;
                    this._speakNext();
                    return;
                }

                const u = new SpeechSynthesisUtterance(`Headline ${this.currentIndex + 1}. ${t}`);
                u.onend = () => {
                    this.currentIndex++;
                    this._speakNext();
                };
                synth.speak(u);
            },

            pause: function() {
                const synth = window.speechSynthesis;
                if (synth.speaking) synth.pause();
                this.paused = true;
            },

            resume: function() {
                const synth = window.speechSynthesis;
                if (synth.paused) {
                    synth.resume();
                    this.paused = false;
                } else if (!synth.speaking && this.isReading) {
                    this._speakNext();
                }
            },

            stop: function() {
                const synth = window.speechSynthesis;
                if (synth && synth.speaking) synth.cancel();
                this.isReading = false;
                this.paused = false;
                this.currentIndex = 0;
                this.headlines = [];
            }
        };
        </script>
        """)

        def handle_click(btn):
            if btn == 'scrape_again':
                run_js('location.reload()')
            elif btn == 'visit':
                run_js(f'window.open("{url}", "_blank")')
            elif btn == 'export_csv':
                export_to_csv(headlines_data, selected_website)
            elif btn == 'read':
                safe_items = [{"headline": it.get("headline", "")} for it in headlines_data]
                payload = base64.b64encode(json.dumps(safe_items).encode("utf-8")).decode("ascii")
                run_js(f"window.__newsSpeech.readList(JSON.parse(atob('{payload}')))")
            elif btn == 'pause':
                run_js("window.__newsSpeech.pause()")
            elif btn == 'resume':
                run_js("window.__newsSpeech.resume()")
            elif btn == 'stop':
                run_js("window.__newsSpeech.stop()")

        put_buttons([
            {'label': '🔄 Scrape Another', 'value': 'scrape_again', 'color': 'primary'},
            {'label': '🌐 Visit Website', 'value': 'visit', 'color': 'success'},
            {'label': '📄 Export CSV', 'value': 'export_csv', 'color': 'info'},
            {'label': '▶ Read Headlines', 'value': 'read', 'color': 'secondary'},
            {'label': '⏸ Pause', 'value': 'pause', 'color': 'warning'},
            {'label': '⏯ Continue', 'value': 'resume', 'color': 'light'},
            {'label': '🛑 Stop', 'value': 'stop', 'color': 'dark'},
        ], onclick=handle_click)

    else:
        err = headlines_data[0]["headline"] if headlines_data else "Unknown error."
        put_error(f"Failed to get news: {err}")
        put_buttons(['Try Again'], onclick=lambda _: run_js('location.reload()'))

if __name__ == "__main__":
    start_server(main, port=8080, debug=True)
