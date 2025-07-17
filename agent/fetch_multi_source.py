from urllib.parse import quote_plus
import feedparser
from datetime import datetime
import requests
import re

def get_real_url(google_news_url):
    """Extract the real URL from Google News redirect URL (simple approach)"""
    # Just return the URL as-is since we're keeping it simple
    return google_news_url

def fetch_articles_multi_source(keywords, max_items=25):
    """
    Fetch articles from multiple sources: Google News, Reddit, Facebook, X/Twitter, LinkedIn
    """
    all_articles = []
    items_per_source = max(1, max_items // 5)  # Divide among 5 sources
    
    print(f"Fetching articles for keywords: {keywords}")
    
    # 1. Google News RSS (existing)
    print("Fetching from Google News...")
    news_articles = fetch_articles_rss(keywords, max_items=items_per_source)
    all_articles.extend(news_articles)
    print(f"Google News: {len(news_articles)} articles")
    
    # 2. Reddit posts
    print("Fetching from Reddit...")
    reddit_articles = fetch_reddit_articles(keywords, max_items=items_per_source)
    all_articles.extend(reddit_articles)
    print(f"Reddit: {len(reddit_articles)} articles")
    
    # 3. X/Twitter posts
    print("Fetching from X/Twitter...")
    twitter_articles = fetch_x_articles(keywords, max_items=items_per_source)
    all_articles.extend(twitter_articles)
    print(f"X/Twitter: {len(twitter_articles)} articles")
    
    # 4. Facebook posts (using RSS feeds)
    print("Fetching from Facebook...")
    facebook_articles = fetch_facebook_articles(keywords, max_items=items_per_source)
    all_articles.extend(facebook_articles)
    print(f"Facebook: {len(facebook_articles)} articles")
    
    # 5. LinkedIn posts
    print("Fetching from LinkedIn...")
    linkedin_articles = fetch_linkedin_articles(keywords, max_items=items_per_source)
    all_articles.extend(linkedin_articles)
    print(f"LinkedIn: {len(linkedin_articles)} articles")
    
    # Sort by date (newest first) and limit total results
    all_articles.sort(key=lambda x: x.get('date', ''), reverse=True)
    print(f"Total articles collected: {len(all_articles)}")
    return all_articles[:max_items]

def fetch_articles_rss(keywords, max_items=25):
    """Fetch articles from Google News RSS (existing function)"""
    try:
        # Use Google News RSS feed with search query
        encoded_keywords = quote_plus(keywords)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keywords}&hl=fr&gl=FR&ceid=FR:fr"
        
        # Parse the RSS feed
        feed = feedparser.parse(rss_url)
        
        articles = []
        for entry in feed.entries[:max_items]:
            # Safe handling of source
            source_info = getattr(entry, 'source', None)
            if source_info and hasattr(source_info, 'title'):
                source = source_info.title
            else:
                source = 'Google News'
            
            article = {
                "titre": entry.title,
                "url": entry.link,
                "source": source,
                "resume": getattr(entry, 'summary', getattr(entry, 'description', '')),
                "date": datetime.now().isoformat(),  # Simplified date handling
            }
            
            # Try to parse published date safely
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                    article["date"] = pub_date.isoformat()
                except:
                    pass  # Keep the default date
                    
            articles.append(article)
        
        return articles
        
    except Exception as e:
        print(f"Error fetching RSS articles: {e}")
        return []

def fetch_reddit_articles(keywords, max_items=10):
    """Fetch articles from Reddit using multiple approaches"""
    articles = []
    
    try:
        # Method 1: Reddit search RSS (general search)
        encoded_keywords = quote_plus(keywords)
        reddit_url = f"https://www.reddit.com/search.rss?q={encoded_keywords}&sort=new&t=week"
        
        headers = {
            'User-Agent': 'NewsMonitor/1.0 (News monitoring bot; contact@example.com)'
        }
        
        # Make request with custom headers
        response = requests.get(reddit_url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Parse with requests content
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:max_items]:
                try:
                    title = str(entry.title) if hasattr(entry, 'title') else "Reddit Post"
                    
                    # Clean Reddit title (remove "r/subreddit • Posted by u/username")
                    if ' • ' in title:
                        title = title.split(' • ')[-1]
                    if title.startswith('r/'):
                        parts = title.split(' ', 2)
                        if len(parts) > 2:
                            title = parts[2]
                    
                    # Get content
                    content = ""
                    if hasattr(entry, 'content') and entry.content:
                        content = str(entry.content[0].value)[:300] + "..."
                    elif hasattr(entry, 'summary'):
                        content = str(entry.summary)[:300] + "..."
                    
                    article = {
                        "titre": title,
                        "url": entry.link if hasattr(entry, 'link') else "",
                        "source": "Reddit",
                        "resume": content,
                        "date": datetime.now().isoformat(),
                    }
                    
                    articles.append(article)
                except Exception as e:
                    print(f"Error parsing Reddit entry: {e}")
                    continue
        
        # Method 2: Try specific subreddits if general search didn't work
        if len(articles) < 3:
            subreddits = ['news', 'worldnews', 'technology', 'science']
            for subreddit in subreddits:
                try:
                    sub_url = f"https://www.reddit.com/r/{subreddit}/search.rss?q={encoded_keywords}&restrict_sr=1&sort=new&t=week"
                    response = requests.get(sub_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)
                        
                        for entry in feed.entries[:2]:  # Limit per subreddit
                            try:
                                title = str(entry.title) if hasattr(entry, 'title') else f"r/{subreddit} post"
                                
                                article = {
                                    "titre": title,
                                    "url": entry.link if hasattr(entry, 'link') else "",
                                    "source": f"Reddit r/{subreddit}",
                                    "resume": str(entry.summary)[:200] + "..." if hasattr(entry, 'summary') else "",
                                    "date": datetime.now().isoformat(),
                                }
                                
                                articles.append(article)
                            except:
                                continue
                                
                        if len(articles) >= max_items:
                            break
                except:
                    continue
        
        return articles[:max_items]
        
    except Exception as e:
        print(f"Error fetching Reddit articles: {e}")
        return []

def fetch_facebook_articles(keywords, max_items=5):
    """Fetch public Facebook posts related to keywords"""
    articles = []
    
    try:
        # Since Facebook's API requires authentication and RSS feeds are limited,
        # we'll use a simple approach for public posts
        encoded_keywords = quote_plus(keywords)
        
        # Try some public Facebook pages' RSS feeds (if available)
        public_pages = [
            'BBCNews',
            'cnn',
            'Reuters',
            'nytimes',
            'TheEconomist'
        ]
        
        headers = {
            'User-Agent': 'NewsMonitor/1.0 (News monitoring bot)'
        }
        
        for page in public_pages:
            try:
                # Note: Facebook RSS feeds are very limited now
                # This is a placeholder - in production you'd need Facebook Graph API
                
                # Create mock articles for now since Facebook severely restricted RSS
                article = {
                    "titre": f"Facebook content related to {keywords} from {page}",
                    "url": f"https://facebook.com/{page}",
                    "source": f"Facebook ({page})",
                    "resume": f"Public content from {page} related to your keywords. Note: Full Facebook integration requires API access.",
                    "date": datetime.now().isoformat(),
                }
                
                articles.append(article)
                
                if len(articles) >= max_items:
                    break
                    
            except Exception as e:
                print(f"Error with Facebook page {page}: {e}")
                continue
        
        return articles[:max_items]
        
    except Exception as e:
        print(f"Error fetching Facebook articles: {e}")
        return []


def fetch_x_articles(keywords, max_items=5):
    """Fetch Twitter/X posts (limited without API)"""
    articles = []
    
    try:
        # Twitter severely restricted RSS access
        # This implementation provides placeholder content
        
        encoded_keywords = quote_plus(keywords)
        
        # Create informative placeholder articles since X/Twitter requires API access
        for i in range(min(max_items, 3)):
            article = {
                "titre": f"X/Twitter discussion about {keywords}",
                "url": f"https://x.com/search?q={encoded_keywords}",
                "source": "X (Twitter)",
                "resume": f"Twitter content related to {keywords}. Note: Full Twitter integration requires API access with authentication.",
                "date": datetime.now().isoformat(),
            }
            
            articles.append(article)
        
        return articles
        
    except Exception as e:
        print(f"Error fetching Twitter articles: {e}")
        return []


def fetch_linkedin_articles(keywords, max_items=5):
    """Fetch LinkedIn articles (limited without API)"""
    articles = []
    
    try:
        # LinkedIn also requires API access for proper integration
        # This implementation provides placeholder content
        
        encoded_keywords = quote_plus(keywords)
        
        # Create informative placeholder articles since LinkedIn requires API access
        for i in range(min(max_items, 2)):
            article = {
                "titre": f"LinkedIn professional content about {keywords}",
                "url": f"https://linkedin.com/search/results/content/?keywords={encoded_keywords}",
                "source": "LinkedIn",
                "resume": f"Professional content on LinkedIn related to {keywords}. Note: Full LinkedIn integration requires API access.",
                "date": datetime.now().isoformat(),
            }
            
            articles.append(article)
        
        return articles
        
    except Exception as e:
        print(f"Error fetching LinkedIn articles: {e}")
        return []

# Keep the original function for backward compatibility
def fetch_articles_from_google_news(keywords, max_items=25):
    """Backward compatibility wrapper"""
    return fetch_articles_rss(keywords, max_items)
