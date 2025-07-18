from urllib.parse import quote_plus
import feedparser
from datetime import datetime, timedelta
import requests
import re
import os
from .multi_ai_enhancer import create_ai_enhancer

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
                        return match.group(1)
        
        # If no extraction method works, return the original URL
        return google_news_url
        
    except Exception as e:
        print(f"Error extracting real URL: {e}")
        return google_news_url

def fetch_articles_multi_source(keywords, max_items=25, use_ai_filtering=True, relevance_threshold=70, show_keyword_suggestions=True):
    """
    Fetch articles from multiple sources: Google News API, RSS feeds, and X/Twitter API
    With AI enhancement features
    """
    all_articles = []
    items_per_source = max(1, max_items // 3)  # Divide among 3 sources
    ai_enhancer = None  # Initialize AI enhancer variable
    
    print(f"Fetching articles for keywords: {keywords}")
    if use_ai_filtering:
        print(f"AI filtering enabled with relevance threshold: {relevance_threshold}")
    
    # Prioritize RSS articles first, then social media articles
    rss_articles = []
    social_articles = []
    
    # 1. Google News RSS (highest priority)
    print("Fetching from Google News...")
    news_articles = fetch_google_news_articles(keywords, max_items=items_per_source)
    rss_articles.extend(news_articles)
    print(f"Google News: {len(news_articles)} articles")
    
    # 2. RSS feeds (from various news sources)
    print("Fetching from RSS feeds...")
    from .fetch_rss import fetch_articles_rss
    rss_feed_articles = fetch_articles_rss(keywords, max_items=items_per_source)
    rss_articles.extend(rss_feed_articles)
    print(f"RSS Feeds: {len(rss_feed_articles)} articles")
    
    # 3. X/Twitter posts (social media)
    print("Fetching from X/Twitter...")
    twitter_articles = fetch_x_articles(keywords, max_items=items_per_source)
    social_articles.extend(twitter_articles)
    print(f"X/Twitter: {len(twitter_articles)} articles")
    
    # Combine with RSS articles first, then social media
    all_articles = rss_articles + social_articles
    print(f"Total articles collected before AI processing: {len(all_articles)}")
    print(f"  - RSS articles: {len(rss_articles)}")
    print(f"  - Social media articles: {len(social_articles)}")
    
    # AI Enhancement: Filter by relevance score
    if use_ai_filtering and all_articles:
        print("Applying AI relevance filtering...")
        try:
            # Create AI enhancer instance
            if ai_enhancer is None:
                ai_enhancer = create_ai_enhancer()
            filtered_articles, filter_stats = ai_enhancer.filter_articles_by_relevance(
                all_articles, keywords, relevance_threshold
            )
            all_articles = filtered_articles
            print(f"AI filtering complete: {len(all_articles)} articles remaining")
        except Exception as e:
            print(f"AI filtering failed, using all articles: {e}")
    
    # AI Enhancement: Detect high-priority articles
    if all_articles:
        print("Detecting high-priority articles...")
        try:
            if ai_enhancer is None:
                ai_enhancer = create_ai_enhancer()
            priority_articles = ai_enhancer.detect_high_priority_articles(all_articles, keywords)
            if priority_articles:
                print(f"Found {len(priority_articles)} high-priority articles")
                # Mark priority articles
                priority_urls = {article['url'] for article in priority_articles}
                for article in all_articles:
                    if article.get('url') in priority_urls:
                        article['is_priority'] = True
        except Exception as e:
            print(f"Priority detection failed: {e}")
    
    # AI Enhancement: Suggest keyword expansion (only if enabled)
    if show_keyword_suggestions and all_articles and len(all_articles) >= 5:
        print("Generating keyword expansion suggestions...")
        try:
            if ai_enhancer is None:
                ai_enhancer = create_ai_enhancer()
            expanded_keywords = ai_enhancer.expand_keywords(keywords, all_articles)
            if expanded_keywords:
                print(f"Suggested additional keywords: {', '.join(expanded_keywords)}")
                # Store suggestions in a special article for display
                suggestion_article = {
                    'titre': f"💡 Mots-clés suggérés: {', '.join(expanded_keywords[:3])}{'...' if len(expanded_keywords) > 3 else ''}",
                    'url': '#keyword-suggestions',
                    'source': 'AI Suggestions',
                    'resume': f"L'IA suggère d'ajouter ces mots-clés: {', '.join(expanded_keywords)}",
                    'date': datetime.now().isoformat(),
                    'is_suggestion': True,
                    'suggested_keywords': expanded_keywords
                }
                all_articles.insert(0, suggestion_article)  # Add at top
        except Exception as e:
            print(f"Keyword expansion failed: {e}")
    elif all_articles and len(all_articles) >= 5:
        # Still generate suggestions for logging, but don't add to articles
        try:
            if ai_enhancer is None:
                ai_enhancer = create_ai_enhancer()
            expanded_keywords = ai_enhancer.expand_keywords(keywords, all_articles)
            if expanded_keywords:
                print(f"Suggested additional keywords: {', '.join(expanded_keywords)}")
        except Exception as e:
            print(f"Keyword expansion failed: {e}")
    
    # Return limited number of articles
    return all_articles[:max_items]

def fetch_google_news_articles(keywords, max_items=25):
    """Fetch articles from Google News RSS feed"""
    articles = []
    
    try:
        # Format keywords for Google News RSS
        encoded_keywords = quote_plus(keywords)
        google_news_url = f"https://news.google.com/rss/search?q={encoded_keywords}&hl=fr&gl=FR&ceid=FR:fr"
        
        # Parse the RSS feed
        feed = feedparser.parse(google_news_url)
        
        print(f"Google News RSS returned {len(feed.entries)} entries")
        
        for entry in feed.entries[:max_items]:
            try:
                # Extract publication date
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pub_date = datetime.now()
                
                # Get real URL
                real_url = get_real_url(entry.link)
                
                article = {
                    'titre': entry.title,
                    'url': real_url,
                    'source': 'Google News',
                    'resume': entry.summary if hasattr(entry, 'summary') else entry.title,
                    'date': pub_date.isoformat(),
                    'auteur': getattr(entry, 'author', 'Unknown')
                }
                
                articles.append(article)
                
            except Exception as e:
                print(f"Error processing Google News entry: {e}")
                continue
        
        return articles
        
    except Exception as e:
        print(f"Error fetching Google News articles: {e}")
        return []

def fetch_x_articles(keywords, max_items=5):
    """Fetch Twitter/X posts using API (requires configuration)"""
    articles = []
    
    try:
        # Check if X API credentials are configured
        api_key = os.getenv('X_API_KEY')
        api_secret = os.getenv('X_API_SECRET')
        access_token = os.getenv('X_ACCESS_TOKEN')
        access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            print("X API credentials not configured. Skipping Twitter/X fetching.")
            return []
        
        try:
            import tweepy
            
            # Create API instance
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Search for tweets
            tweets = tweepy.Cursor(api.search_tweets, 
                                 q=keywords, 
                                 lang="fr", 
                                 result_type="recent",
                                 tweet_mode="extended").items(max_items)
            
            for tweet in tweets:
                article = {
                    'titre': tweet.full_text[:100] + "..." if len(tweet.full_text) > 100 else tweet.full_text,
                    'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                    'source': 'Twitter/X',
                    'resume': tweet.full_text,
                    'date': tweet.created_at.isoformat(),
                    'auteur': tweet.user.screen_name
                }
                articles.append(article)
                
        except ImportError:
            print("Tweepy not installed. Install with: pip install tweepy")
            return []
        except Exception as e:
            print(f"Error with X API: {e}")
            return []
        
    except Exception as e:
        print(f"Error fetching Twitter articles: {e}")
        return []
    
    return articles

# Keep the original function for backward compatibility
def fetch_articles_from_google_news(keywords, max_items=25):
    """Backward compatibility wrapper"""
    return fetch_google_news_articles(keywords, max_items)
