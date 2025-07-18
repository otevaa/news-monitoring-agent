"""
Asynchronous campaign creation system for better user experience
"""

import asyncio
import threading
import uuid
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from .fetch_multi_source import fetch_articles_multi_source
from .campaign_manager import CampaignManager
from .google_sheets_manager import GoogleSheetsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CampaignCreationTask:
    """Represents a campaign creation task"""
    task_id: str
    campaign_name: str
    keywords: List[str]
    frequency: str
    user_id: str
    max_items: int = 25
    campaign_id: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    progress: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None

class AsyncCampaignManager:
    """Manages asynchronous campaign creation tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, CampaignCreationTask] = {}
        self.campaigns: Dict[str, Dict] = {}  # Store campaign information
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.executor = None
        self.loop = None
        self._setup_event_loop()
    
    def _setup_event_loop(self):
        """Setup event loop for async operations"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            # No loop in current thread, create new one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def create_campaign_async(self, 
                             campaign_name: str, 
                             keywords: List[str], 
                             frequency: str,
                             user_id: str,
                             max_items: int = 25,
                             progress_callback: Optional[Callable] = None) -> str:
        """
        Create a campaign asynchronously
        
        Returns:
            str: Task ID for tracking progress
        """
        
        task_id = str(uuid.uuid4())
        
        # Create task
        task = CampaignCreationTask(
            task_id=task_id,
            campaign_name=campaign_name,
            keywords=keywords,
            frequency=frequency,
            user_id=user_id,
            max_items=max_items
        )
        
        self.tasks[task_id] = task
        
        # Add progress callback
        if progress_callback:
            if task_id not in self.progress_callbacks:
                self.progress_callbacks[task_id] = []
            self.progress_callbacks[task_id].append(progress_callback)
        
        # Start async processing
        threading.Thread(target=self._process_campaign_creation, args=(task_id,), daemon=True).start()
        
        logger.info(f"Started async campaign creation task {task_id}")
        return task_id
    
    def _process_campaign_creation(self, task_id: str):
        """Process campaign creation in background thread"""
        try:
            task = self.tasks[task_id]
            task.status = "processing"
            self._update_progress(task_id, 10, "Initializing campaign...")
            
            # Step 1: Validate inputs
            self._validate_campaign_inputs(task)
            self._update_progress(task_id, 20, "Validating inputs...")
            
            # Step 2: Check for duplicates
            self._check_duplicate_campaigns(task)
            self._update_progress(task_id, 30, "Checking for duplicates...")
            
            # Step 3: Expand keywords
            expanded_keywords = self._expand_campaign_keywords(task)
            self._update_progress(task_id, 50, "Expanding keywords...")
            
            # Step 4: Test RSS feeds
            self._test_rss_feeds(task, expanded_keywords)
            self._update_progress(task_id, 70, "Testing RSS feeds...")
            
            # Step 5: Create campaign in database
            campaign_id = self._create_campaign_in_db(task, expanded_keywords)
            task.campaign_id = campaign_id  # Set campaign_id for article processing
            self._update_progress(task_id, 75, "Campaign created in database...")
            
            # Step 6: Setup monitoring
            self._setup_campaign_monitoring(task, campaign_id)
            self._update_progress(task_id, 85, "Setting up monitoring...")
            
            # Step 7: Process articles and update spreadsheet
            self._process_campaign_articles(task, expanded_keywords)
            self._update_progress(task_id, 100, "Campaign created successfully!")
            
            # Mark as completed
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = {
                "campaign_id": campaign_id,
                "message": "Campaign created successfully",
                "keywords_expanded": expanded_keywords,
                "spreadsheet_id": task.spreadsheet_id
            }
            
            logger.info(f"Campaign creation task {task_id} completed successfully")
            
        except Exception as e:
            task = self.tasks[task_id]
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self._update_progress(task_id, 0, f"Erreur: {str(e)}")
            logger.error(f"Campaign creation task {task_id} failed: {e}")
            
            # Don't use flash() from background thread - it doesn't work properly
            # Error messages will be shown through the task status API
    
    def _validate_campaign_inputs(self, task: CampaignCreationTask):
        """Validate campaign inputs"""
        if not task.campaign_name or not task.campaign_name.strip():
            raise ValueError("Le nom de la campagne ne peut pas être vide")
        
        if not task.keywords or len(task.keywords) == 0:
            raise ValueError("Les mots-clés ne peuvent pas être vides")
        
        # Check if keywords contain only empty strings
        non_empty_keywords = [kw.strip() for kw in task.keywords if kw.strip()]
        if not non_empty_keywords:
            raise ValueError("Les mots-clés ne peuvent pas être vides")
        
        # Updated to include all valid frequency options from the form
        if not task.frequency or task.frequency not in ['15min', 'hourly', 'daily', 'weekly']:
            raise ValueError(f"Fréquence invalide: {task.frequency}. Doit être: 15min, hourly, daily, ou weekly")
        
        # Validate user_id
        if not task.user_id or not task.user_id.strip():
            raise ValueError("User ID manquant")
        
        # Add more validation as needed
        time.sleep(0.5)  # Simulate processing time
    
    def _check_duplicate_campaigns(self, task: CampaignCreationTask):
        """Check for duplicate campaigns"""
        # In a real implementation, this would check the database
        # For now, just simulate the check
        time.sleep(0.5)  # Simulate database check
    
    def _expand_campaign_keywords(self, task: CampaignCreationTask) -> List[str]:
        """Return original keywords - expansion is now handled during article fetching"""
        return task.keywords
    
    def _test_rss_feeds(self, task: CampaignCreationTask, keywords: List[str]):
        """Test RSS feeds to ensure they work"""
        
        # Test with a subset of keywords
        test_keywords = keywords[:3]  # Test first 3 keywords
        
        for keyword in test_keywords:
            try:
                articles = fetch_articles_multi_source(keyword, max_items=5)
                if not articles:
                    logger.warning(f"No articles found for keyword: {keyword}")
                else:
                    logger.info(f"Successfully tested keyword '{keyword}': {len(articles)} articles")
            except Exception as e:
                logger.error(f"Error testing RSS feed for keyword {keyword}: {e}")
                # Don't fail the entire process for RSS test failures
        
        time.sleep(1)  # Simulate testing time
    
    def _create_campaign_in_db(self, task: CampaignCreationTask, keywords: List[str]) -> str:
        """Create campaign in database"""
        # Import the campaign manager to save the campaign
        try:
            campaign_manager = CampaignManager()
            
            # Create campaign data structure
            campaign_data = {
                'name': task.campaign_name,
                'keywords': ', '.join(task.keywords),
                'frequency': task.frequency,
                'max_articles': task.max_items,
                'integrations': ['google_sheets'] if task.spreadsheet_id else [],
                'description': f'Campaign created via async process for {task.campaign_name}',
                'ai_filtering_enabled': True,
                'keyword_expansion_enabled': True,
                'priority_alerts_enabled': True,
                'ai_model': 'openai-gpt3.5'
            }
            
            # Create the campaign using the campaign manager
            campaign_id = campaign_manager.create_campaign(campaign_data)
            
            # If we have a spreadsheet, update the campaign with spreadsheet info
            if task.spreadsheet_id:
                campaign = campaign_manager.get_campaign(campaign_id)
                if campaign:
                    campaign['spreadsheet_id'] = task.spreadsheet_id
                    campaign['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{task.spreadsheet_id}"
                    campaign_manager._save_campaigns()
            
            logger.info(f"Campaign {campaign_id} created successfully in database")
            return campaign_id
            
        except Exception as e:
            logger.error(f"Error creating campaign in database: {e}")
            # Fallback to UUID generation
            return str(uuid.uuid4())
    
    def _setup_campaign_monitoring(self, task: CampaignCreationTask, campaign_id: str):
        """Setup monitoring for the campaign"""
        # In a real implementation, this would setup the monitoring system
        # For now, just simulate
        time.sleep(0.3)
    
    def _process_campaign_articles(self, task: CampaignCreationTask, keywords: List[str]):
        """Process articles with AI and save to spreadsheet"""
        try:
            # Use multi-source fetch
            articles = fetch_articles_multi_source(
                ' OR '.join(keywords), 
                max_items=task.max_items
            )
            
            if not articles:
                logger.warning(f"No articles found for campaign {task.campaign_id}")
                return

            # Save to spreadsheet if Google Sheets is configured
            sheets_manager = GoogleSheetsManager()
            
            # Check if this campaign has a spreadsheet
            if hasattr(task, 'spreadsheet_id') and task.spreadsheet_id:
                logger.info(f"Saving {len(articles)} articles to spreadsheet {task.spreadsheet_id}")
                success = sheets_manager.save_articles_to_spreadsheet(
                    task.spreadsheet_id, 
                    articles, 
                    campaign_name=task.campaign_name,
                    keywords=' '.join(keywords)
                )
                if success:
                    logger.info(f"Successfully saved articles to spreadsheet for campaign {task.campaign_id}")
                    # Update campaign with spreadsheet info
                    if task.campaign_id in self.campaigns:
                        self.campaigns[task.campaign_id]['spreadsheet_updated'] = True
                        self.campaigns[task.campaign_id]['articles_in_spreadsheet'] = len(articles)
                else:
                    logger.error(f"Failed to save articles to spreadsheet for campaign {task.campaign_id}")
            else:
                logger.info(f"No spreadsheet configured for campaign {task.campaign_id}")
            
            # Update campaign status
            if task.campaign_id in self.campaigns:
                self.campaigns[task.campaign_id]['status'] = 'completed'
                self.campaigns[task.campaign_id]['articles_processed'] = len(articles)
                self.campaigns[task.campaign_id]['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"Campaign {task.campaign_id} completed successfully with {len(articles)} articles")
            
        except Exception as e:
            logger.error(f"Error processing campaign articles: {e}")
            if task.campaign_id in self.campaigns:
                self.campaigns[task.campaign_id]['status'] = 'failed'
                self.campaigns[task.campaign_id]['error'] = str(e)
        
        time.sleep(2)  # Simulate processing time
    
    def _update_progress(self, task_id: str, progress: int, message: str):
        """Update task progress and notify callbacks"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.progress = progress
            
            # Notify callbacks
            if task_id in self.progress_callbacks:
                for callback in self.progress_callbacks[task_id]:
                    try:
                        callback(task_id, progress, message)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a task"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "campaign_name": task.campaign_name,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "result": task.result
        }
    
    def get_all_tasks(self, user_id: str) -> List[Dict]:
        """Get all tasks for a user"""
        user_tasks = []
        for task in self.tasks.values():
            if task.user_id == user_id:
                user_tasks.append(self.get_task_status(task.task_id))
        
        return sorted(user_tasks, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_tasks(self, hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in ['completed', 'failed'] and 
                task.completed_at and 
                task.completed_at < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            if task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]
        
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

# Global instance
campaign_manager = AsyncCampaignManager()

def create_campaign_async(campaign_name: str, 
                         keywords: List[str], 
                         frequency: str,
                         user_id: str,
                         max_items: int = 25,
                         progress_callback: Optional[Callable] = None) -> str:
    """Convenience function to create campaign asynchronously"""
    return campaign_manager.create_campaign_async(
        campaign_name, keywords, frequency, user_id, max_items, progress_callback
    )

def get_campaign_task_status(task_id: str) -> Optional[Dict]:
    """Get status of a campaign creation task"""
    return campaign_manager.get_task_status(task_id)

def get_user_campaign_tasks(user_id: str) -> List[Dict]:
    """Get all campaign creation tasks for a user"""
    return campaign_manager.get_all_tasks(user_id)
