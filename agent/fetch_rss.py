from urllib.parse import quote_plus
import feedparser
from datetime import datetime, timedelta
import requests
import re
import time
import json

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

def expand_keywords(query):
    """Expand keywords with synonyms and related terms for better search coverage"""
    
    # Dictionary of keyword expansions
    keyword_expansions = {
        'intelligence artificielle': ['AI', 'IA', 'machine learning', 'apprentissage automatique', 'deep learning', 'réseaux de neurones'],
        'ai': ['intelligence artificielle', 'IA', 'machine learning', 'apprentissage automatique'],
        'blockchain': ['crypto', 'bitcoin', 'ethereum', 'DeFi', 'NFT', 'cryptomonnaie'],
        'startup': ['start-up', 'entrepreneur', 'financement', 'levée de fonds', 'innovation'],
        'tech': ['technologie', 'numérique', 'digital', 'innovation', 'startup'],
        'cybersécurité': ['sécurité informatique', 'cyber', 'piratage', 'ransomware', 'hack'],
        'cloud': ['nuage', 'AWS', 'Azure', 'Google Cloud', 'infrastructure'],
        'data': ['données', 'big data', 'analyse', 'analytics', 'data science'],
        'fintech': ['finance', 'banque', 'paiement', 'néobanque', 'crypto'],
        'mobilité': ['transport', 'véhicule électrique', 'voiture autonome', 'mobilité durable'],
        'énergie': ['renouvelable', 'solaire', 'éolien', 'batteries', 'transition énergétique'],
        'santé': ['medtech', 'e-santé', 'télémédecine', 'biotech', 'pharma'],
        'industrie': ['4.0', 'robotique', 'automation', 'IoT', 'capteurs'],
        'métaverse': ['réalité virtuelle', 'VR', 'AR', 'réalité augmentée', 'NFT'],
        'quantum': ['quantique', 'informatique quantique', 'calcul quantique']
    }
    
    words = query.lower().split()
    expanded_terms = set(words)
    
    for word in words:
        if word in keyword_expansions:
            expanded_terms.update(keyword_expansions[word])
    
    # Return original query plus 2-3 most relevant expanded terms
    additional_terms = list(expanded_terms - set(words))[:3]
    return ' OR '.join([query] + additional_terms)

def parse_entry_date(entry):
    """Safely parse entry date from feedparser"""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            # Convert time.struct_time to datetime
            parsed_time = entry.published_parsed
            if isinstance(parsed_time, tuple) and len(parsed_time) >= 6:
                return datetime(*parsed_time[:6])
        return datetime.now()
    except Exception:
        return datetime.now()

def fetch_articles_rss(query, max_items=25):
    if not query or query.strip() == "":
        raise ValueError("Le mot-clé ne peut pas être vide.")

    # Expand keywords for better coverage
    expanded_query = expand_keywords(query)
    
    # First, get regular Google News results
    query_encoded = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(url)
    
    results = []
    
    # Process Google News results
    for entry in feed.entries[:max_items]:
        # Get the real URL instead of the Google News redirect
        real_url = get_real_url(entry.link)
        
        # Parse date safely
        pub_date = parse_entry_date(entry)
        
        results.append({
            "date": pub_date.isoformat(),
            "source": "Google News RSS",
            "titre": str(entry.title) if hasattr(entry, 'title') else "",
            "url": real_url,
            "resume": str(entry.summary) if hasattr(entry, 'summary') else ""
        })
    
    # Sort by date (most recent first)
    results.sort(key=lambda x: x['date'], reverse=True)
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    
    for result in results:
        if result['url'] not in seen_urls:
            seen_urls.add(result['url'])
            unique_results.append(result)
    
    return unique_results[:max_items]
