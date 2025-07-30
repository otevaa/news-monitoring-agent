"""
User Profile Manager
Manages user preferences and AI settings using database
"""

from typing import Dict, Optional
from database.managers import get_user_manager

class UserProfileManager:
    """Manages user profiles and AI preferences"""
    
    def __init__(self):
        self.user_manager = get_user_manager()
    
    def get_default_profile(self) -> Dict:
        """Get default profile settings"""
        return {
            'ai_model': 'deepseek/deepseek-r1',
            'ai_filtering_enabled': True,
            'keyword_expansion_enabled': True,
            'priority_alerts_enabled': True,
            'language': 'fr',
            'timezone': 'Europe/Paris'
        }
    
    def get_user_profile(self, user_id: str = 'default') -> Dict:
        """Get user profile or return default"""
        try:
            profile = self.user_manager.get_user_profile(user_id)
            if profile:
                # Convert database booleans (0/1) to Python booleans
                profile['ai_filtering_enabled'] = bool(profile.get('ai_filtering_enabled', 1))
                profile['keyword_expansion_enabled'] = bool(profile.get('keyword_expansion_enabled', 1))
                profile['priority_alerts_enabled'] = bool(profile.get('priority_alerts_enabled', 1))
                return profile
        except Exception as e:
            print(f"Error getting user profile: {e}")
        
        return self.get_default_profile()
    
    def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile"""
        try:
            # Convert boolean values to integers for database storage
            db_updates = {}
            for key, value in updates.items():
                if key in ['ai_filtering_enabled', 'keyword_expansion_enabled', 'priority_alerts_enabled']:
                    db_updates[key] = 1 if value else 0
                else:
                    db_updates[key] = value
            
            return self.user_manager.update_user_profile(user_id, db_updates)
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False
    
    def get_ai_settings(self, user_id: str = 'default') -> Dict:
        """Get AI settings for a user"""
        try:
            return self.user_manager.get_user_ai_settings(user_id)
        except Exception as e:
            print(f"Error getting AI settings: {e}")
            return self.user_manager.get_default_ai_settings()
    
    def get_available_models(self) -> Dict:
        """Get list of available AI models"""
        return {
            'openai-gpt3.5': {
                'name': 'OpenAI GPT-3.5 Turbo',
                'description': 'Rapide et économique',
                'cost': 'Faible',
                'provider': 'OpenAI'
            },
            'openai-gpt4': {
                'name': 'OpenAI GPT-4',
                'description': 'Plus précis mais plus coûteux',
                'cost': 'Élevé',
                'provider': 'OpenAI'
            },
            'huggingface-bert': {
                'name': 'HuggingFace BERT',
                'description': 'Gratuit, traitement local',
                'cost': 'Gratuit',
                'provider': 'HuggingFace'
            },
            'ollama-llama2': {
                'name': 'Ollama Llama 2',
                'description': 'Local, privé, gratuit',
                'cost': 'Gratuit',
                'provider': 'Ollama'
            },
            'deepseek/deepseek-r1': {
                'name': 'DeepSeek R1',
                'description': 'IA avancée, local via Ollama',
                'cost': 'Gratuit',
                'provider': 'Ollama'
            },
            'anthropic-claude': {
                'name': 'Anthropic Claude',
                'description': 'Excellent raisonnement',
                'cost': 'Moyen',
                'provider': 'Anthropic'
            }
        }

# Global instance
user_profile_manager = UserProfileManager()
