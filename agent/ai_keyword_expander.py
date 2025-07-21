"""
AI-powered keyword expansion using OpenRouter API
"""
import os
import json
from typing import List, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
            # Prepare the prompt
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
            response_content = response.choices[0].message.content.strip()
            
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
            
            print(f"✅ AI keyword expansion successful: {len(french_keywords)} French + {len(english_keywords)} English keywords")
            
            return french_keywords, english_keywords
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing AI response: {e}")
            return [], []
        except Exception as e:
            print(f"❌ Error expanding keywords with AI: {e}")
            return [], []

def create_keyword_expander(model: str = "deepseek/deepseek-r1") -> KeywordExpander:
    """
    Factory function to create a KeywordExpander instance
    
    Args:
        model: AI model to use (default: deepseek/deepseek-r1 - free tier)
        
    Returns:
        KeywordExpander instance
    """
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
