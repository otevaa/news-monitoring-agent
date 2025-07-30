"""
AI-powered keyword expansion using OpenRouter API or local Ollama
"""
import os
import json
import requests
from typing import List, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OllamaKeywordExpander:
    """AI-powered keyword expander using local Ollama"""
    
    def __init__(self, model: str = "deepseek-r1:1.5b", base_url: str = "http://localhost:11434"):
        """Initialize with Ollama configuration"""
        self.model = model
        self.base_url = base_url
    
    def expand_keywords(self, keywords: List[str]) -> Tuple[List[str], List[str]]:
        """
        Expand keywords using Ollama AI to find related terms
        
        Args:
            keywords: List of original keywords
            
        Returns:
            Tuple of (french_keywords, english_keywords)
        """
        try:
            keywords_str = ", ".join(keywords)
            
            prompt = f"""
            Vous êtes un expert en expansion de mots-clés pour la surveillance de l'actualité.
            
            Mots-clés originaux: {keywords_str}
            
            Générez des mots-clés supplémentaires pertinents pour surveiller l'actualité liée à ces termes.
            
            Règles:
            1. Proposez 5 mots-clés français supplémentaires
            2. Proposez 5 mots-clés anglais supplémentaires
            3. Incluez des synonymes, termes connexes, variations et mots du même champ sémantique
            4. Pensez aux termes que les journalistes utilisent
            5. Évitez les mots-clés trop génériques
            
            Répondez UNIQUEMENT avec un JSON valide dans ce format exact:
            {{
                "french_keywords": ["mot1", "mot2", "mot3", "mot4", "mot5"],
                "english_keywords": ["word1", "word2", "word3", "word4", "word5"]
            }}
            """
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return [], []
            
            response_data = response.json()
            ai_response = response_data.get("response", "")
            
            # Extract JSON from response
            json_start = ai_response.find("{")
            json_end = ai_response.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                return [], []
            
            json_str = ai_response[json_start:json_end]
            result = json.loads(json_str)
            
            french_keywords = result.get("french_keywords", [])
            english_keywords = result.get("english_keywords", [])
            
            # Filter out empty strings and duplicates
            french_keywords = [kw.strip() for kw in french_keywords if kw.strip()]
            english_keywords = [kw.strip() for kw in english_keywords if kw.strip()]
            
            return french_keywords, english_keywords
            
        except (requests.exceptions.RequestException, json.JSONDecodeError, Exception):
            return [], []

class KeywordExpander:
    """AI-powered keyword expander using OpenRouter"""
    
    def __init__(self, model: str = "deepseek/deepseek-r1"):
        """Initialize with OpenRouter configuration"""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = model
    
    def expand_keywords(self, keywords: List[str]) -> Tuple[List[str], List[str]]:
        """
        Expand keywords using AI to find related terms
        
        Args:
            keywords: List of original keywords
            
        Returns:
            Tuple of (french_keywords, english_keywords)
        """
        try:
            keywords_str = ", ".join(keywords)
            
            prompt = f"""
            Vous êtes un expert en expansion de mots-clés pour la surveillance de l'actualité.
            
            Mots-clés originaux: {keywords_str}
            
            Générez des mots-clés supplémentaires pertinents pour surveiller l'actualité liée à ces termes.
            
            Règles:
            1. Proposez 10 mots-clés français supplémentaires
            2. Proposez 10 mots-clés anglais supplémentaires
            3. Incluez des synonymes, termes connexes, variations et mots du meme champ sémantique
            4. Pensez aux termes que les journalistes utilisent
            5. Évitez les mots-clés trop génériques
            
            Répondez uniquement en format JSON:
            {{
                "french_keywords": ["mot1", "mot2", "mot3"],
                "english_keywords": ["word1", "word2", "word3"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un assistant spécialisé dans l'expansion de mots-clés pour la surveillance de l'actualité. Répondez uniquement en JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            if not response_content:
                return [], []
            
            response_content = response_content.strip()
            
            # Clean up the response (remove any markdown formatting)
            if response_content.startswith('```json'):
                response_content = response_content[7:-3]
            elif response_content.startswith('```'):
                response_content = response_content[3:-3]
            
            # Parse JSON
            result = json.loads(response_content)
            
            french_keywords = result.get("french_keywords", [])
            english_keywords = result.get("english_keywords", [])
            
            # Filter out empty strings and duplicates
            french_keywords = [kw.strip() for kw in french_keywords if kw.strip()]
            english_keywords = [kw.strip() for kw in english_keywords if kw.strip()]
            
            return french_keywords, english_keywords
            
        except (json.JSONDecodeError, Exception):
            return [], []

def create_keyword_expander(model: str = "deepseek/deepseek-r1"):
    """
    Factory function to create a KeywordExpander instance
    
    Args:
        model: AI model to use. 
               - For Ollama: use format like "ollama-deepseek-r1:1.5b"
               - For OpenRouter: use format like "deepseek/deepseek-r1"
        
    Returns:
        KeywordExpander or OllamaKeywordExpander instance
    """
    # Check if model is for Ollama (starts with 'ollama-')
    if model.startswith('ollama-'):
        # Extract the actual model name (remove 'ollama-' prefix)
        ollama_model = model[7:]  # Remove 'ollama-' prefix
        return OllamaKeywordExpander(ollama_model)
    else:
        # Use OpenRouter
        return KeywordExpander(model)

# Convenience function for backward compatibility
def ai_keyword_expander(keywords: List[str]) -> Tuple[List[str], List[str]]:
    """
    Direct function to expand keywords
    
    Args:
        keywords: List of original keywords
        
    Returns:
        Tuple of (french_keywords, english_keywords)
    """
    expander = create_keyword_expander()
    return expander.expand_keywords(keywords)
