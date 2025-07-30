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
from database.managers import DatabaseUserProfileManager
from database.models import DatabaseManager

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
        
        # Get summary
        summary_text = str(getattr(entry, 'summary', entry.title))
        resume_text = summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
        
        results.append({
            "date": pub_date.isoformat(),
            "source": "Google News RSS",
            "titre": entry.title,
            "url": real_url,
            "description": getattr(entry, 'summary', entry.title),
            "resume": resume_text,
            "auteur": getattr(entry, 'author', 'Unknown')
        })
    
    return results

def get_real_url(google_news_url):
    """Extract the real URL from Google News redirect"""
    try:
        # Parse the URL
        parsed = urlparse(google_news_url)
        
        # For Google News URLs, the real URL is in the 'url' parameter
        if 'news.google.com' in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if 'url' in query_params:
                return unquote(query_params['url'][0])
        
        # If it's not a Google News redirect, return the original URL
        return google_news_url
        
    except Exception:
        return google_news_url

def fetch_twitter_articles(keywords, max_items=10):
    """Fetch articles from Twitter"""
    articles = []
    
    try:
        # Get Twitter API credentials
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
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
                
            except Exception:
                continue
                
    except Exception:
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
                
            except Exception:
                continue
        
        return articles
        
    except Exception:
        return []

# Keep the original function for backward compatibility
def fetch_articles_from_google_news(keywords, max_items=25):
    """Backward compatibility wrapper"""
    return fetch_google_news_articles(keywords, max_items)

def fetch_articles_multi_source(
    keywords: str,
    max_items: int = 25,
    show_keyword_suggestions: bool = True,
    campaigns: Optional[List[Dict]] = None,
    ai_enhancer: Optional[Any] = None,
    user_id: Optional[str] = None,
    since_datetime: Optional[datetime] = None
) -> List[Dict]:
    """
    Fetch articles from multiple sources (RSS, social media) with smart date filtering
    
    Args:
        keywords: Search keywords
        max_items: Maximum number of articles to return
        show_keyword_suggestions: Whether to show AI keyword suggestions
        campaigns: List of campaign configurations
        ai_enhancer: Optional AI enhancer instance
        user_id: User ID for profile-based settings
        since_datetime: Fetch only articles newer than this datetime (for incremental updates)
        
    Returns:
        List of article dictionaries
    """
    # AI Enhancement: Expand keywords first (before fetching articles)
    expanded_keywords = []
    if show_keyword_suggestions:
        try:
            if ai_enhancer is None:
                # Get user profile and create AI enhancer with user-preferred model
                db_manager = DatabaseManager()
                profile_manager = DatabaseUserProfileManager(db_manager)
                user_profile = profile_manager.get_user_profile(user_id) if user_id else {}
                ai_model = user_profile.get('ai_model', 'deepseek/deepseek-r1')
                ai_enhancer = create_keyword_expander(ai_model)
            
            french_words, english_words = ai_enhancer.expand_keywords([keywords])
            expanded_keywords = french_words + english_words
            
            if expanded_keywords:
                # Create comprehensive search query with original + AI keywords
                all_search_keywords = f"{keywords} OR {' OR '.join(expanded_keywords[:5])}"  # Limit to avoid too long queries
            else:
                all_search_keywords = keywords
        except Exception:
            all_search_keywords = keywords
    else:
        all_search_keywords = keywords
    
    # Fetch from RSS sources (Google News) with enhanced keywords
    rss_articles = fetch_articles_rss(all_search_keywords, max_items)
    
    # Fetch from social media sources with enhanced keywords  
    social_articles = fetch_twitter_articles(all_search_keywords, max_items=10)
    
    # Combine with RSS articles first, then social media
    all_articles = rss_articles + social_articles
    
    # Smart date filtering for incremental updates
    if since_datetime:
        filtered_articles = []
        for article in all_articles:
            article_date_str = article.get('date', '')
            if article_date_str:
                try:
                    article_date = datetime.fromisoformat(article_date_str.replace('Z', ''))
                    if article_date > since_datetime:
                        filtered_articles.append(article)
                except ValueError:
                    # If date parsing fails, include the article (safer approach)
                    filtered_articles.append(article)
            else:
                # If no date, include the article
                filtered_articles.append(article)
        
        all_articles = filtered_articles
    
    # Sort articles by date: NEWEST FIRST for processing
    def get_article_date(article):
        date_str = article.get('date', '')
        if date_str:
            try:
                return datetime.fromisoformat(date_str.replace('Z', ''))
            except ValueError:
                return datetime.min
        return datetime.min
    
    all_articles.sort(key=get_article_date, reverse=True)
    
    # Apply limit after sorting (take the newest articles)
    if len(all_articles) > max_items:
        all_articles = all_articles[:max_items]
    
    # Return articles (keyword expansion already done at the beginning)
    return all_articles[:max_items]
