from urllib.parse import quote_plus
import feedparser
from datetime import datetime
import requests
import re

def get_real_url(google_news_url):
    """Extract the real URL from Google News redirect URL"""
    import re
    from urllib.parse import urlparse, parse_qs, unquote
    
    try:
        # First, try to extract from the URL parameters
        parsed = urlparse(google_news_url)
        
        # Check if it's a Google News URL with a 'url' parameter
        if 'news.google.com' in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if 'url' in query_params:
                return unquote(query_params['url'][0])
        
        # For articles/CAI* type URLs, try a different approach
        if '/articles/' in google_news_url:
            # Try to follow redirects with a proper user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(google_news_url, headers=headers, timeout=5, allow_redirects=False)
            
            # Check for Location header in redirect
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location')
                if location and 'news.google.com' not in location:
                    return location
            
            # If we get a 200, parse the content for the actual link
            if response.status_code == 200:
                # Look for the actual article link in various patterns
                patterns = [
                    r'<a[^>]*data-n-href="([^"]+)"',
                    r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'location\.replace\(["\']([^"\']+)["\']\)',
                    r'<meta[^>]*http-equiv="refresh"[^>]*content="[^;]*;\s*url=([^"]*)"'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        url = unquote(match.group(1))
                        if not url.startswith('http'):
                            continue
                        if 'news.google.com' not in url:
                            return url
        
    except Exception as e:
        print(f"Error extracting URL: {e}")
        pass
    
    # If all else fails, return the original URL
    return google_news_url

def fetch_articles_rss(query, max_items=25):
    if not query or query.strip() == "":
        raise ValueError("Le mot-clé ne peut pas être vide.")

    query_encoded = quote_plus(query)  # gère les espaces et caractères spéciaux
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:max_items]:
        # Get the real URL instead of the Google News redirect
        real_url = get_real_url(entry.link)
        
        results.append({
            "date": datetime(*entry.published_parsed[:6]).isoformat() if entry.published_parsed else datetime.now().isoformat(),
            "source": "Google News RSS",
            "titre": entry.title,
            "url": real_url,  # Use the real destination URL
            "resume": entry.summary
        })
    return results
