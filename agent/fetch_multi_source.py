from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import feedparser
from datetime import datetime, timedelta
import requests
import re
import os
import tweepy
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
from .ai_keyword_expander import create_keyword_expander

# Load environment variables
load_dotenv()
def parse_entry_date(entry):
    """Parse entry date from RSS feed"""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        else:
            return datetime.now()
    except:
        return datetime.now()

def fetch_articles_rss(query, max_items=25):
    """Fetch articles from RSS sources (Google News)"""
    if not query or query.strip() == "":
        raise ValueError("Le mot-clé ne peut pas être vide.")
    
    # Get Google News results
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
            "url": real_url
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

def get_real_url(google_news_url):
    """Extract the real URL from Google News redirect URL"""
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

def fetch_twitter_articles(keywords, max_items=10):
    """
    Fetch articles from X/Twitter API
    """
    articles = []
    
    try:
        # Twitter API credentials
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            print("Twitter API credentials not found. Skipping Twitter articles.")
            return articles
        
        # Authenticate with Twitter API
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        
        api = tweepy.API(auth)
        
        # Search for tweets
        tweets = tweepy.Cursor(api.search_tweets, q=keywords, lang='fr', result_type='recent').items(max_items)
        
        for tweet in tweets:
            try:
                article = {
                    'titre': tweet.text[:100] + '...' if len(tweet.text) > 100 else tweet.text,
                    'url': f"https://twitter.com/user/status/{tweet.id}",
                    'source': f"Twitter - @{tweet.user.screen_name}",
                    'date': tweet.created_at.isoformat(),
                    'resume': tweet.text
                }
                articles.append(article)
                
            except Exception as e:
                print(f"Error processing tweet: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching Twitter articles: {e}")
        return []
    
    return articles

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
                        # Handle feedparser tuple conversion - ignore type checking
                        parsed_time = entry.published_parsed  # type: ignore
                        if parsed_time and len(parsed_time) >= 6:
                            pub_date = datetime(*parsed_time[:6])  # type: ignore
                        else:
                            pub_date = datetime.now()
                    except (TypeError, ValueError, IndexError):
                        pub_date = datetime.now()
                
                # Get real URL
                real_url = get_real_url(entry.link)
                
                article = {
                    'titre': entry.title,
                    'url': real_url,
                    'source': 'Google News',
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
            # Create API instance
            auth = tweepy.OAuthHandler(api_key, api_secret)  # type: ignore
            auth.set_access_token(access_token, access_token_secret)
            api = tweepy.API(auth, wait_on_rate_limit=True)  # type: ignore
            
            # Search for tweets
            tweets = tweepy.Cursor(api.search_tweets,  # type: ignore 
                                 q=keywords, 
                                 lang="fr", 
                                 result_type="recent",
                                 tweet_mode="extended").items(max_items)
            
            for tweet in tweets:
                article = {
                    'titre': tweet.full_text[:100] + "..." if len(tweet.full_text) > 100 else tweet.full_text,
                    'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                    'source': 'Twitter/X',
                    'date': tweet.created_at.isoformat(),
                    'auteur': tweet.user.screen_name
                }
                articles.append(article)
                
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

def fetch_articles_multi_source(
    keywords: str,
    max_items: int = 25,
    show_keyword_suggestions: bool = True,
    campaigns: Optional[List[Dict]] = None,
    ai_enhancer: Optional[Any] = None
) -> List[Dict]:
    """
    Fetch articles from multiple sources (RSS, social media)
    
    Args:
        keywords: Search keywords
        max_items: Maximum number of articles to return
        show_keyword_suggestions: Whether to show AI keyword suggestions
        campaigns: List of campaign configurations
        ai_enhancer: Optional AI enhancer instance
        
    Returns:
        List of article dictionaries
    """
    print(f"Fetching articles for keywords: {keywords}")
    
    # Fetch from RSS sources (Google News)
    rss_articles = fetch_articles_rss(keywords, max_items)
    
    # Fetch from social media sources
    social_articles = fetch_twitter_articles(keywords, max_items=10)
    
    # Combine with RSS articles first, then social media
    all_articles = rss_articles + social_articles
    print(f"Total articles collected: {len(all_articles)}")
    print(f"  - RSS articles: {len(rss_articles)}")
    print(f"  - Social media articles: {len(social_articles)}")
    
    # AI Enhancement: Suggest keyword expansion (only if enabled)
    if show_keyword_suggestions and all_articles and len(all_articles) >= 5:
        print("Generating keyword expansion suggestions...")
        try:
            if ai_enhancer is None:
                # Get user profile and create AI enhancer with user-preferred model
                from .user_profile_manager import UserProfileManager
                profile_manager = UserProfileManager()
                user_profile = profile_manager.get_user_profile()
                ai_enhancer = create_keyword_expander(user_profile)
            french_words, english_words = ai_enhancer.expand_keywords(keywords)
            expanded_keywords = french_words + english_words
            if expanded_keywords:
                print(f"Suggested additional keywords: {', '.join(expanded_keywords)}")
                # Store suggestions in a special article for display
                suggestion_article = {
                    'titre': f"💡 Mots-clés suggérés: {', '.join(expanded_keywords[:3])}{'...' if len(expanded_keywords) > 3 else ''}",
                    'url': '#keyword-suggestions',
                    'source': 'AI Suggestions',
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
                # Get user profile and create AI enhancer with user-preferred model
                from .user_profile_manager import UserProfileManager
                profile_manager = UserProfileManager()
                user_profile = profile_manager.get_user_profile()
                ai_enhancer = create_keyword_expander(user_profile)
            french_words, english_words = ai_enhancer.expand_keywords(keywords)
            expanded_keywords = french_words + english_words
            if expanded_keywords:
                print(f"Suggested additional keywords: {', '.join(expanded_keywords)}")
        except Exception as e:
            print(f"Keyword expansion failed: {e}")
    
    # Return limited number of articles
    return all_articles[:max_items]
