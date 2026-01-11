from flask import Flask, render_template, request
import feedparser
from openai import OpenAI
from newspaper import Article

app = Flask(__name__)

import os
client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

def fetch_top_headlines():
    # BBC US & Canada news RSS – free, unlimited, no keys
    feed_url = "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"
    feed = feedparser.parse(feed_url)
    articles = []
    
    # Take top 5
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", "Untitled"),
            "url": entry.get("link", "#"),
            "source": "BBC News",
            "description": entry.get("summary", entry.get("title", "")),
            "image": ""  # No images in RSS
        })
    return articles

def analyze_bias(text):
    if not text:
        return "Unable to analyze (no text available)", "neutral"
    prompt = f"""Analyze this news summary for political bias in the US context.
Classify as Conservative, Liberal, or Neutral.
Give a short 1-sentence reason.

Summary:
{text[:1000]}

Answer only with the classification and reason:"""
    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        result = response.choices[0].message.content.strip()
        lower = result.lower()
        if "conservative" in lower:
            cls = "conservative"
        elif "liberal" in lower:
            cls = "liberal"
        else:
            cls = "neutral"
        return result, cls
    except Exception as e:
        return f"Analysis error: {str(e)}", "neutral"

@app.route('/')
def home():
    headlines = fetch_top_headlines()
    articles = []
    for h in headlines:
        text = h.get("description", h.get("title", ""))
        bias_text, bias_class = analyze_bias(text)
        articles.append({
            "title": h["title"],
            "url": h["url"],
            "source": h["source"],
            "bias": bias_text,
            "bias_class": bias_class,
            "image": h["image"]
        })
    return render_template("index.html", articles=articles)

@app.route('/bias-check', methods=['POST'])
def analyze_url():
    url = request.form['url']
    text = ""
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text or article.summary or ""
        custom_title = article.title or "Custom Article"
    except:
        text = "No text available for this URL - bias analysis limited."
        custom_title = "Custom Article"
    
    bias_text, bias_class = analyze_bias(text)
    
    custom_article = {
        "title": custom_title,
        "url": url,
        "source": "User-provided",
        "bias": bias_text,
        "bias_class": bias_class,
        "image": ""
    }
    
    headlines = fetch_top_headlines()
    articles = []
    for h in headlines:
        text_top = h.get("description", h.get("title", ""))
        bias_top, class_top = analyze_bias(text_top)
        articles.append({
            "title": h["title"],
            "url": h["url"],
            "source": h["source"],
            "bias": bias_top,
            "bias_class": class_top,
            "image": h["image"]
        })
    
    articles.insert(0, custom_article)
    return render_template("index.html", articles=articles)

if __name__ == '__main__':
    app.run(debug=True)