from urllib.parse import quote_plus
import feedparser
from datetime import datetime

def fetch_articles_rss(query, max_items=25):
    if not query or query.strip() == "":
        raise ValueError("Le mot-clé ne peut pas être vide.")

    query_encoded = quote_plus(query)  # gère les espaces et caractères spéciaux
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:max_items]:
        results.append({
            "date": datetime(*entry.published_parsed[:6]).isoformat(),
            "source": "Google News RSS",
            "titre": entry.title,
            "url": entry.link,
            "resume": entry.summary
        })
    return results
