import os
import json
import requests
import time
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIKeywordExpander:
    """AI-powered keyword expansion for better article coverage"""
    
    def __init__(self, model: str = "openai-gpt4o-mini"):
        self.model = model
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Rate limiting for OpenAI API (max 3 requests per minute for free tier)
        self.last_request_time = 0
        self.min_request_interval = 20  # seconds between requests
        
    def expand_keywords(self, user_keywords: str) -> Tuple[List[str], List[str]]:
        """
        Expand user keywords using AI to generate related French and English terms
        
        Args:
            user_keywords: Comma-separated string of user keywords
            
        Returns:
            Tuple of (french_words, english_words) - each containing up to 10 words
        """
        
        # Clean and prepare keywords
        keywords = [kw.strip() for kw in user_keywords.split(',') if kw.strip()]
        keywords_str = ', '.join(keywords)
        
        if self.model.startswith('openai-'):
            return self._expand_with_openai(keywords_str)
        elif self.model.startswith('anthropic-'):
            return self._expand_with_anthropic(keywords_str)
        elif self.model.startswith('ollama-'):
            return self._expand_with_ollama(keywords_str)
        else:
            # Invalid model, return empty lists
            return [], []
    
    def _get_openai_model(self) -> str:
        """Get the appropriate OpenAI model name based on the configured model"""
        if self.model == 'openai-gpt3.5':
            return 'gpt-3.5-turbo'
        elif self.model == 'openai-gpt4':
            return 'gpt-4'
        elif self.model == 'openai-gpt4o-mini':
            return 'gpt-4o-mini'
        else:
            # Default to the free model
            return 'gpt-4o-mini'
    
    def _expand_with_openai(self, keywords_str: str) -> Tuple[List[str], List[str]]:
        """Expand keywords using OpenAI API with retry logic and rate limiting"""
        
        if not self.openai_api_key:
            return [], []
        
        # Rate limiting - wait if needed
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            time.sleep(wait_time)
        
        # Retry configuration
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                self.last_request_time = time.time()
                
                # Prepare the prompt
                prompt = f"""Generate exactly 10 French words and 10 English words related to: {keywords_str}

Return only JSON format:
{{
  "french_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"],
  "english_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"]
}}"""

                # Make API request
                headers = {
                    'Authorization': f'Bearer {self.openai_api_key}',
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'model': self._get_openai_model(),
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'max_tokens': 500,
                    'temperature': 0.7
                }
                
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    
                    # Parse JSON response
                    try:
                        keywords_data = json.loads(content)
                        french_words = keywords_data.get('french_words', [])[:10]
                        english_words = keywords_data.get('english_words', [])[:10]
                        return french_words, english_words
                        
                    except json.JSONDecodeError:
                        return [], []
                        
                elif response.status_code == 429:
                    # Check if it's rate limit or quota issue
                    error_response = response.json().get('error', {})
                    error_code = error_response.get('code', '')
                    
                    if error_code == 'insufficient_quota':
                        return [], []
                    else:
                        # Regular rate limit - retry with exponential backoff
                        if attempt < max_retries - 1:
                            delay = base_delay * (3 ** attempt) + 30
                            time.sleep(delay)
                            continue
                        else:
                            return [], []
                        
                elif response.status_code == 401:
                    return [], []
                    
                else:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        return [], []
                        
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return [], []
                    
            except Exception:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return [], []
        
        # If we get here, all retries failed
        return [], []
    
    def _expand_with_anthropic(self, keywords_str: str) -> Tuple[List[str], List[str]]:
        """Expand keywords using Anthropic Claude API"""
        
        if not self.anthropic_api_key:
            return [], []
        
        try:
            # Prepare the prompt
            prompt = f"""Generate exactly 10 French words and 10 English words related to: {keywords_str}

Return only JSON format:
{{
  "french_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"],
  "english_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"]
}}"""

            headers = {
                'Content-Type': 'application/json',
                'x-api-key': self.anthropic_api_key
            }
            
            data = {
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 500,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text'].strip()
                
                try:
                    keywords_data = json.loads(content)
                    french_words = keywords_data.get('french_words', [])[:10]
                    english_words = keywords_data.get('english_words', [])[:10]
                    return french_words, english_words
                except json.JSONDecodeError:
                    return [], []
            else:
                return [], []
                
        except Exception:
            return [], []
    
    def _expand_with_ollama(self, keywords_str: str) -> Tuple[List[str], List[str]]:
        """Expand keywords using Ollama local API"""
        
        try:
            prompt = f"""Generate exactly 10 French words and 10 English words related to: {keywords_str}

Return only JSON format:
{{
  "french_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"],
  "english_words": ["word1", "word2", "word3", "word4", "word5", "word6", "word7", "word8", "word9", "word10"]
}}"""

            # Get model name from config
            model_name = self.model.replace('ollama-', '')
            
            data = {
                'model': model_name,
                'prompt': prompt,
                'stream': False
            }
            
            response = requests.post(
                f'{self.ollama_url}/api/generate',
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                try:
                    # Try to extract JSON from the response (may contain <think> tags)
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        keywords_data = json.loads(json_str)
                        french_words = keywords_data.get('french_words', [])[:10]
                        english_words = keywords_data.get('english_words', [])[:10]
                        return french_words, english_words
                    else:
                        return [], []
                except json.JSONDecodeError:
                    return [], []
            else:
                return [], []
                
        except Exception:
            return [], []

# Factory function for easy use
def create_keyword_expander(user_profile: Optional[dict] = None) -> AIKeywordExpander:
    """
    Factory function to create an AI keyword expander based on user preferences
    
    Args:
        user_profile: Dictionary containing user preferences (ai_model, etc.)
    
    Returns:
        AIKeywordExpander instance configured with the appropriate AI model
    """
    
    # Get model preference from user profile or environment
    if user_profile and 'ai_model' in user_profile:
        model = user_profile['ai_model']
    else:
        model = os.getenv('DEFAULT_AI_MODEL', 'openai-gpt4o-mini')
    
    return AIKeywordExpander(model=model)
