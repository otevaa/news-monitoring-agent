from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import traceback
from database.models import DatabaseManager
from database.managers import DatabaseCampaignManager, DatabaseIntegrationManager
from agent.google_sheets_manager import GoogleSheetsManager
from agent.fetch_multi_source import fetch_articles_rss
from agent.fetch_multi_source import fetch_articles_multi_source

class CampaignScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db_manager = DatabaseManager()
        self.campaign_manager = DatabaseCampaignManager(self.db_manager)
        self.integration_manager = DatabaseIntegrationManager(self.db_manager)
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
            self.logger.info(f"🚀 Starting campaign: {campaign['name']}")
            
            # Get campaign settings
            keywords = campaign.get('keywords', '')
            max_articles = campaign.get('max_articles', 25)
            
            self.logger.info(f"🔍 Searching with keywords: {keywords}")
            
            # Fetch articles with AI keyword expansion handled automatically
            articles = fetch_articles_multi_source(
                keywords, 
                max_items=max_articles, 
                show_keyword_suggestions=True  # AI expansion handled inside fetch function
            )
            
            if articles:
                self.logger.info(f"📰 Found {len(articles)} articles for campaign '{campaign['name']}'")
                
                # Process integrations
                integrations = campaign.get('integrations', [])
                success_count = 0
                
                for integration in integrations:
                    if integration == 'google_sheets':
                        # Google Sheets integration
                        user_id = campaign.get('user_id')
                        if user_id and self._is_google_sheets_connected_for_user(user_id):
                            spreadsheet_id = campaign.get('spreadsheet_id')
                            if spreadsheet_id:
                                # Use the existing sheets manager with user_id context
                                success = self._save_articles_for_user(
                                    user_id,
                                    spreadsheet_id,
                                    articles,
                                    campaign['name'],
                                    keywords
                                )
                                if success:
                                    success_count += 1
                                    self.logger.info(f"✅ Saved articles to Google Sheets")
                                else:
                                    self.logger.error(f"❌ Failed to save articles to Google Sheets")
                            else:
                                self.logger.warning(f"⚠️ Campaign has Google Sheets integration but no spreadsheet_id")
                        else:
                            self.logger.warning(f"⚠️ Google Sheets not connected for user {user_id} - skipping integration")
                    
                    elif integration == 'airtable':
                        # Airtable integration - placeholder for now
                        self.logger.info("Airtable integration not implemented in database version")
                        pass
                
                # Update campaign statistics
                user_id = campaign.get('user_id')
                if user_id:
                    self.campaign_manager.update_campaign_stats(
                        campaign['id'], 
                        user_id,
                        len(articles)
                    )
                
                self.logger.info(f"✅ Campaign '{campaign['name']}' completed: {len(articles)} articles, {success_count}/{len(integrations)} integrations successful")
                
            else:
                self.logger.info(f"📭 No articles found for campaign '{campaign['name']}'")
                
        except Exception as e:
            self.logger.error(f"❌ Error running campaign '{campaign['name']}': {e}")
            traceback.print_exc()

    def _is_google_sheets_connected_for_user(self, user_id: str) -> bool:
        """Check if Google Sheets is connected for a specific user"""
        try:
            # Use the database integration manager method
            return self.integration_manager.is_google_sheets_connected(user_id)
        except Exception as e:
            self.logger.error(f"Error checking Google Sheets connection for user {user_id}: {e}")
            return False

    def _save_articles_for_user(self, user_id: str, spreadsheet_id: str, articles: List[Dict], 
                               campaign_name: str, keywords: str) -> bool:
        """Save articles to Google Sheets for a specific user"""
        try:
            # Create a temporary GoogleSheetsManager instance
            # We'll use the service methods directly with user credentials
            sheets_service = self.sheets_manager.get_sheets_service(user_id)
            if not sheets_service:
                return False
            
            # Filter articles to only include last 2 days
            today = datetime.now().date()
            three_days_ago = today - timedelta(days=2)
            
            filtered_articles = []
            for article in articles:
                article_date_str = article.get('date', '')
                if article_date_str:
                    try:
                        # Parse article date (assuming format like "2025-07-17T10:30:00")
                        article_date = datetime.fromisoformat(article_date_str.replace('Z', '')).date()
                        if article_date >= three_days_ago:
                            filtered_articles.append(article)
                    except (ValueError, TypeError):
                        # If date parsing fails, include the article
                        filtered_articles.append(article)
                else:
                    # No date available, include the article
                    filtered_articles.append(article)
            
            if not filtered_articles:
                self.logger.info(f"No recent articles to save for campaign {campaign_name}")
                return True
            
            # Prepare data for insertion
            values = []
            for article in filtered_articles:
                row = [
                    article.get('date', ''),
                    article.get('source', ''),
                    article.get('titre', ''),  # Changed from 'title' to 'titre'
                    article.get('url', ''),    # Changed from 'link' to 'url'
                    campaign_name
                ]
                values.append(row)
            
            # Get the next available row
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range='A:A'
            ).execute()
            
            existing_rows = len(result.get('values', []))
            next_row = existing_rows + 1
            range_name = f'A{next_row}:E{next_row + len(values) - 1}'
            
            # Insert the data
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
            
            self.logger.info(f"Successfully saved {len(values)} articles to spreadsheet")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving articles for user {user_id}: {e}")
            return False

# Global scheduler instance
campaign_scheduler = CampaignScheduler()

# External function to run a campaign
def run_campaign(campaign_id: str, user_id: str = 'default'):
    """Run a specific campaign by ID"""
    try:
        from database.models import DatabaseManager
        from database.managers import DatabaseCampaignManager
        
        db_manager = DatabaseManager()
        campaign_manager = DatabaseCampaignManager(db_manager)
        campaign = campaign_manager.get_campaign(campaign_id, user_id)
        
        if campaign:
            campaign_scheduler.run_campaign(campaign)
            return True
        else:
            print(f"Campaign {campaign_id} not found for user {user_id}")
            return False
            
    except Exception as e:
        print(f"Error running campaign {campaign_id}: {e}")
        return False
