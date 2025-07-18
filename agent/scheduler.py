from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from agent.campaign_manager import CampaignManager
from agent.integrations import IntegrationManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.fetch_multi_source import fetch_articles_rss
from agent.fetch_multi_source import fetch_articles_multi_source

class CampaignScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.campaign_manager = CampaignManager()
        self.integration_manager = IntegrationManager()
        self.sheets_manager = GoogleSheetsManager()
        self.logger = logging.getLogger(__name__)
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        
    def start(self):
        """Start the scheduler"""
        # Run campaign checks every 5 minutes
        self.scheduler.add_job(
            func=self.check_and_run_campaigns,
            trigger=IntervalTrigger(minutes=5),
            id='campaign_checker',
            name='Check and run campaigns',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.logger.info("Campaign scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Campaign scheduler stopped")
    
    def check_and_run_campaigns(self):
        """Check which campaigns need to run and execute them"""
        try:
            campaigns_to_run = self.campaign_manager.get_campaigns_for_execution()
            
            for campaign in campaigns_to_run:
                self.logger.info(f"Running campaign: {campaign['name']}")
                self.run_campaign(campaign)
                
        except Exception as e:
            self.logger.error(f"Error checking campaigns: {e}")
    
    def run_campaign(self, campaign):
        """Run a single campaign with AI enhancements"""
        try:
            # Fetch articles using the campaign keywords from multiple sources
            keywords = campaign['keywords']
            max_articles = campaign.get('max_articles', 25)
            
            # Check if AI features are enabled for this campaign
            use_ai_filtering = campaign.get('ai_filtering_enabled', True)
            relevance_threshold = campaign.get('relevance_threshold', 70)
            
            # Use multi-source fetcher with AI enhancements
            articles = fetch_articles_multi_source(
                keywords, 
                max_items=max_articles,
                use_ai_filtering=use_ai_filtering,
                relevance_threshold=relevance_threshold,
                show_keyword_suggestions=campaign.get('keyword_expansion_enabled', False)
            )
            
            if articles:
                # Check for high-priority articles and send alerts
                priority_articles = [a for a in articles if a.get('is_priority')]
                if priority_articles:
                    self.logger.info(f"🚨 Found {len(priority_articles)} high-priority articles for campaign '{campaign['name']}'")
                    # TODO: Implement notification system for alerts
                
                # Log keyword suggestions if any
                suggestions = [a for a in articles if a.get('is_suggestion')]
                if suggestions:
                    suggested_keywords = suggestions[0].get('suggested_keywords', [])
                    self.logger.info(f"💡 AI suggests expanding keywords with: {', '.join(suggested_keywords[:3])}")
                
                # Filter out suggestion articles before saving to integrations
                actual_articles = [a for a in articles if not a.get('is_suggestion')]
                
                # Send to configured integrations
                integrations = campaign.get('integrations', [])
                success_count = 0
                articles_saved = 0
                
                for integration in integrations:
                    if integration == 'google_sheets':
                        # Use GoogleSheetsManager to save articles
                        if self.sheets_manager.is_google_sheets_connected():
                            spreadsheet_id = campaign.get('spreadsheet_id')
                            if spreadsheet_id:
                                success = self.sheets_manager.save_articles_to_spreadsheet(
                                    spreadsheet_id,
                                    actual_articles,  # Use filtered articles without suggestions
                                    campaign['name'],
                                    keywords
                                )
                                if success:
                                    success_count += 1
                                    # Calculate how many articles were actually saved after filtering
                                    from datetime import datetime, timedelta
                                    end = datetime.now().date()
                                    start = end - timedelta(days=3)  # Updated to match 3-day filter
                                    
                                    # Note: The GoogleSheetsManager now handles duplicate filtering internally
                                    # We'll estimate based on date filtering, but the actual count might be lower
                                    articles_saved = 0
                                    for article in articles:
                                        article_date_str = article.get('date', '')
                                        if article_date_str:
                                            try:
                                                article_date = datetime.fromisoformat(article_date_str.replace('Z', '')).date()
                                                if article_date >= start:
                                                    articles_saved += 1
                                            except:
                                                articles_saved += 1
                                        else:
                                            articles_saved += 1
                                    
                                    self.logger.info(f"Successfully processed {articles_saved} articles for Google Sheets (duplicates filtered automatically)")
                                else:
                                    self.logger.error(f"Failed to save articles to Google Sheets for campaign '{campaign['name']}'")
                            else:
                                self.logger.warning(f"Campaign '{campaign['name']}' has Google Sheets integration but no spreadsheet_id")
                        else:
                            self.logger.warning("Google Sheets not connected - skipping Google Sheets integration")
                    elif integration == 'airtable':
                        # Keep existing airtable logic
                        success = self.integration_manager.send_to_airtable(actual_articles, campaign['name'])
                        if success:
                            success_count += 1
                
                # Use the actual count of articles saved (after filtering)
                saved_count = articles_saved if 'articles_saved' in locals() else 0
                self.logger.info(f"Campaign '{campaign['name']}': {saved_count} articles sent to {success_count}/{len(integrations)} integrations")
                
                # Update campaign statistics with the correct count
                self.campaign_manager.update_campaign_stats(
                    campaign['id'], 
                    saved_count
                )
            else:
                self.logger.info(f"Campaign '{campaign['name']}': No articles found")
                # Still update last check time
                self.campaign_manager.update_campaign_stats(campaign['id'], 0)
                
        except Exception as e:
            self.logger.error(f"Error running campaign '{campaign['name']}': {e}")
            import traceback
            traceback.print_exc()
    
    def run_campaign_now(self, campaign_id: str):
        """Manually trigger a campaign run"""
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if campaign:
            self.run_campaign(campaign)
            return True
        return False

# Global scheduler instance
campaign_scheduler = CampaignScheduler()

# External function to run a campaign
def run_campaign(campaign_id: str):
    """Run a specific campaign by ID"""
    return campaign_scheduler.run_campaign_now(campaign_id)
