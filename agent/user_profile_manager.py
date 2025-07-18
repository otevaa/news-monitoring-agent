"""
User Profile Manager
Manages user preferences and AI settings
"""

import json
import os
from typing import Dict, Optional

class UserProfileManager:
    """Manages user profiles and AI preferences"""
    
    def __init__(self):
        self.profiles_file = "user_profiles.json"
        self.profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict:
        """Load user profiles from JSON file"""
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _save_profiles(self):
        """Save user profiles to JSON file"""
        try:
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving user profiles: {e}")
    
    def get_default_profile(self) -> Dict:
        """Get default profile settings"""
        return {
            'ai_model': 'openai-gpt3.5',
            'ai_filtering_enabled': True,
            'keyword_expansion_enabled': True,
            'priority_alerts_enabled': True,
            'language': 'fr',
            'timezone': 'Europe/Paris'
        }
    
    def get_user_profile(self, user_id: str = 'default') -> Dict:
        """Get user profile or return default"""
        if user_id in self.profiles:
            return self.profiles[user_id]
        return self.get_default_profile()
    
    def update_user_profile(self, user_id: str, updates: Dict) -> bool:
        """Update user profile"""
        try:
            if user_id not in self.profiles:
                self.profiles[user_id] = self.get_default_profile()
            
            self.profiles[user_id].update(updates)
            self._save_profiles()
            return True
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False
    
    def get_ai_settings(self, user_id: str = 'default') -> Dict:
        """Get AI settings for a user"""
        profile = self.get_user_profile(user_id)
        return {
            'model': profile.get('ai_model', 'openai-gpt3.5'),
            'filtering_enabled': profile.get('ai_filtering_enabled', True),
            'keyword_expansion_enabled': profile.get('keyword_expansion_enabled', True),
            'priority_alerts_enabled': profile.get('priority_alerts_enabled', True)
        }
    
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
            'anthropic-claude': {
                'name': 'Anthropic Claude',
                'description': 'Excellent raisonnement',
                'cost': 'Moyen',
                'provider': 'Anthropic'
            }
        }

# Global instance
user_profile_manager = UserProfileManager()
