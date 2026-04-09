# 📰 News Scraper

A modern, simplified news aggregator built with **PyWebIO** and powered by the **NewsAPI**. Quickly fetch real-time headlines from any news domain with integrated sentiment analysis, CSV export, and browser-based text-to-speech.

---

## ✨ Features

- ⚡ **Quick-Select Grid** — One-click access to major news sources like BBC, CNN, Reuters, The Guardian, and India Today.
- 🎯 **Domain-Based Search** — Simply enter any news website domain (e.g., `techcrunch.com`) to fetch its latest articles.
- 🔄 **Smart Fetching** — Automatically switches between "Top Headlines" and "All Articles" endpoints based on the source's API availability.
- 😊 **Sentiment Analysis** — Headlines are processed via [TextBlob](https://textblob.readthedocs.io/) and tagged as Positive, Negative, or Neutral.
- 🔊 **Voice Mode** — Full text-to-speech controls (Play, Pause, Resume, Stop) to listen to your news feed.
- 📄 **Data Export** — Export your curated news list to a clean CSV file including source names, dates, and sentiment scores.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- [NewsAPI](https://newsapi.org/) Key (Get a free one at newsapi.org)

### 2. Installation
```bash
pip install pywebio requests beautifulsoup4 textblob
```

### 3. Setup NLP Data
```bash
python -m textblob.download_corpora
```

### 4. Configure & Run
Create a `.env` file in the root directory (based on `.env.example`) and add your key:
```env
NEWS_API_KEY=your_api_key_here
```
Run the application:
```bash
python app.py
```
Open **http://localhost:8080** to start scraping.

---

## 🛠️ Usage

1. **Pick a Source**: Use the top grid buttons for curated popular sites.
2. **Enter Custom Domain**: Type any news domain (e.g., `nytimes.com`) in the input box.
3. **Choose Mode**:
   - **Top Headlines**: Best for major global breaking news.
   - **All Articles**: Best for niche sites or specific daily updates.
4. **Analyze & Export**: Review sentiment scores and download the report in one click.

---

## 📦 Dependencies

| Package | Role |
|---------|------|
| `pywebio` | Web Interface & Interaction |
| `requests` | API Communication |
| `textblob` | NLP Sentiment Analysis |
| `beautifulsoup4` | Domain metadata handling |

---

## 📜 License
MIT License - Created for educational and personal news tracking.