"""
Multi-Provider AI Enhancement Module
Supports OpenAI, HuggingFace, Ollama, and other AI providers
"""

import os
import requests
import json
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MultiProviderAIEnhancer:
    """
    AI-powered news analysis supporting multiple providers
    """
    
    def __init__(self, model: str = 'openai-gpt3.5'):
        """Initialize with specified model"""
        self.model = model
        self.relevance_threshold = 70
        
        # Initialize provider based on model
        self._init_provider()
        
        # Priority keywords for intelligent alerts
        self.priority_keywords = [
            'breaking', 'urgent', 'alerte', 'crise', 'emergency',
            'nouveauté', 'lancement', 'annonce', 'révolution',
            'exclusif', 'première', 'inédit'
        ]
    
    def _init_provider(self):
        """Initialize the appropriate AI provider"""
        if self.model.startswith('openai'):
            self._init_openai()
        elif self.model.startswith('huggingface'):
            self._init_huggingface()
        elif self.model.startswith('ollama'):
            self._init_ollama()
        elif self.model.startswith('anthropic'):
            self._init_anthropic()
        else:
            print(f"Unknown model: {self.model}, falling back to basic methods")
            self.provider = 'basic'
    
    def _init_openai(self):
        """Initialize OpenAI provider"""
        self.provider = 'openai'
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            try:
                import openai
                openai.api_key = self.api_key
                self.openai = openai
            except ImportError:
                print("OpenAI library not installed. Install with: pip install openai")
                self.provider = 'basic'
        else:
            print("OpenAI API key not found in environment")
            self.provider = 'basic'
    
    def _init_huggingface(self):
        """Initialize HuggingFace provider"""
        self.provider = 'huggingface'
        try:
            from transformers import pipeline
            self.hf_classifier = pipeline("text-classification", 
                                        model="nlptown/bert-base-multilingual-uncased-sentiment")
            print("HuggingFace BERT model loaded successfully")
        except ImportError:
            print("HuggingFace transformers not installed. Install with: pip install transformers torch")
            self.provider = 'basic'
        except Exception as e:
            print(f"Error loading HuggingFace model: {e}")
            self.provider = 'basic'
    
    def _init_ollama(self):
        """Initialize Ollama provider (local)"""
        self.provider = 'ollama'
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Test Ollama connection
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print("Ollama connection successful")
            else:
                print("Ollama not accessible, falling back to basic methods")
                self.provider = 'basic'
        except:
            print("Ollama not running, falling back to basic methods")
            self.provider = 'basic'
    
    def _init_anthropic(self):
        """Initialize Anthropic Claude provider"""
        self.provider = 'anthropic'
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.anthropic_key:
            print("Anthropic API key not found, falling back to basic methods")
            self.provider = 'basic'
    
    def score_article_relevance(self, article: Dict, keywords: str) -> int:
        """Score article relevance using the configured AI provider"""
        
        if self.provider == 'openai':
            return self._score_with_openai(article, keywords)
        elif self.provider == 'huggingface':
            return self._score_with_huggingface(article, keywords)
        elif self.provider == 'ollama':
            return self._score_with_ollama(article, keywords)
        elif self.provider == 'anthropic':
            return self._score_with_anthropic(article, keywords)
        else:
            return self._score_basic(article, keywords)
    
    def _score_with_openai(self, article: Dict, keywords: str) -> int:
        """Score using OpenAI"""
        try:
            title = article.get('titre', '')
            content = article.get('resume', '')
            
            prompt = f"""Évaluez la pertinence de cet article par rapport aux mots-clés sur une échelle de 0 à 100.

Mots-clés: {keywords}
Titre: {title}
Contenu: {content[:300]}

Répondez UNIQUEMENT avec un nombre entre 0 et 100."""
            
            model_name = "gpt-4" if "gpt4" in self.model else "gpt-3.5-turbo"
            
            response = self.openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            score_text = response.choices[0].message.content or ""
            score = int(re.findall(r'\d+', score_text)[0]) if re.findall(r'\d+', score_text) else 50
            return max(0, min(100, score))
            
        except Exception as e:
            print(f"OpenAI scoring error: {e}")
            return self._score_basic(article, keywords)
    
    def _score_with_huggingface(self, article: Dict, keywords: str) -> int:
        """Score using HuggingFace BERT"""
        try:
            title = article.get('titre', '')
            keywords_list = [k.strip().lower() for k in keywords.split(',')]
            
            # Simple relevance based on keyword matching + sentiment
            text = title.lower()
            matches = sum(1 for keyword in keywords_list if keyword in text)
            keyword_score = (matches / len(keywords_list)) * 80 if keywords_list else 0
            
            # Add sentiment analysis boost
            try:
                sentiment = self.hf_classifier(title)[0]
                sentiment_boost = 20 if sentiment['label'] == 'POSITIVE' else 10
            except:
                sentiment_boost = 10
            
            total_score = min(100, keyword_score + sentiment_boost)
            return int(total_score)
            
        except Exception as e:
            print(f"HuggingFace scoring error: {e}")
            return self._score_basic(article, keywords)
    
    def _score_with_ollama(self, article: Dict, keywords: str) -> int:
        """Score using Ollama (local LLM)"""
        try:
            title = article.get('titre', '')
            
            prompt = f"""Rate relevance of this article to keywords from 0-100:
Keywords: {keywords}
Title: {title}
Answer with only a number."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama2",  # or another installed model
                    "prompt": prompt,
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                score_text = result.get('response', '')
                score = int(re.findall(r'\d+', score_text)[0])
                return max(0, min(100, score))
            else:
                return self._score_basic(article, keywords)
                
        except Exception as e:
            print(f"Ollama scoring error: {e}")
            return self._score_basic(article, keywords)
    
    def _score_with_anthropic(self, article: Dict, keywords: str) -> int:
        """Score using Anthropic Claude"""
        try:
            title = article.get('titre', '')
            
            headers = {
                'x-api-key': self.anthropic_key,
                'content-type': 'application/json'
            }
            
            prompt = f"Rate article relevance to '{keywords}' from 0-100. Article: {title}. Answer with only a number."
            
            response = requests.post(
                'https://api.anthropic.com/v1/complete',
                headers=headers,
                json={
                    "prompt": f"Human: {prompt}\n\nAssistant:",
                    "model": "claude-instant-1",
                    "max_tokens_to_sample": 10
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                score_text = result.get('completion', '')
                score = int(re.findall(r'\d+', score_text)[0])
                return max(0, min(100, score))
            else:
                return self._score_basic(article, keywords)
                
        except Exception as e:
            print(f"Anthropic scoring error: {e}")
            return self._score_basic(article, keywords)
    
    def _score_basic(self, article: Dict, keywords: str) -> int:
        """Fallback scoring without AI"""
        title = article.get('titre', '').lower()
        content = article.get('resume', '').lower()
        text = f"{title} {content}"
        
        keywords_list = [k.strip().lower() for k in keywords.split(',')]
        
        score = 0
        total_possible = len(keywords_list) * 25  # Max 25 points per keyword
        
        for keyword in keywords_list:
            if keyword in title:
                score += 25  # Title matches are worth more
            elif keyword in content:
                score += 15  # Content matches
            
            # Partial matching
            words = keyword.split()
            if len(words) > 1:
                matches = sum(1 for word in words if word in text)
                score += (matches / len(words)) * 10
        
        # Normalize to 0-100
        normalized_score = min(100, (score / total_possible) * 100) if total_possible > 0 else 20
        return max(20, int(normalized_score))  # Minimum 20 for any article
    
    def expand_keywords(self, original_keywords: str, articles: List[Dict]) -> List[str]:
        """Expand keywords using AI or basic analysis"""
        if self.provider == 'openai':
            return self._expand_with_openai(original_keywords, articles)
        elif self.provider in ['huggingface', 'ollama', 'anthropic']:
            return self._expand_with_analysis(original_keywords, articles)
        else:
            return self._expand_semantic_basic(original_keywords, articles)
    
    def _expand_with_openai(self, keywords: str, articles: List[Dict]) -> List[str]:
        """Expand keywords using OpenAI with semantic understanding"""
        try:
            # Analyze article content for semantic context
            titles = [article.get('titre', '') for article in articles[:10]]
            summaries = [article.get('resume', '') for article in articles[:10]]
            combined_text = "\n".join([f"Title: {t}\nSummary: {s}" for t, s in zip(titles, summaries)])
            
            prompt = f"""Analysez ce contenu d'articles et suggérez 5 mots-clés sémantiquement liés à "{keywords}".
            
Utilisez la compréhension sémantique pour identifier des termes connexes, synonymes, et concepts liés qui pourraient être pertinents pour cette recherche.

Contenu des articles:
{combined_text}

Retournez uniquement les 5 mots-clés les plus pertinents, séparés par des virgules, sans explication."""
            
            model_name = "gpt-4" if "gpt4" in self.model else "gpt-3.5-turbo"
            
            response = self.openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            result = response.choices[0].message.content or ""
            expanded = [k.strip() for k in result.split(',') if k.strip()]
            return expanded[:5]
            
        except Exception as e:
            print(f"OpenAI keyword expansion error: {e}")
            return self._expand_semantic_basic(keywords, articles)
    
    def _expand_with_analysis(self, keywords: str, articles: List[Dict]) -> List[str]:
        """Expand keywords using semantic text analysis"""
        return self._expand_semantic_basic(keywords, articles)
    
    def _expand_semantic_basic(self, keywords: str, articles: List[Dict]) -> List[str]:
        """Advanced semantic keyword expansion using context analysis"""
        # Common semantic patterns and related terms
        semantic_patterns = {
            'intelligence artificielle': ['ia', 'ai', 'machine learning', 'deep learning', 'algorithme', 'automatisation'],
            'ia': ['intelligence artificielle', 'ai', 'machine learning', 'deep learning', 'algorithme', 'automatisation'],
            'santé': ['médecine', 'hôpital', 'patient', 'traitement', 'diagnostic', 'thérapie'],
            'technologie': ['tech', 'innovation', 'numérique', 'digital', 'startup', 'développement'],
            'finance': ['banque', 'investissement', 'économie', 'bourse', 'marché', 'fintech'],
            'environnement': ['écologie', 'climat', 'durable', 'vert', 'pollution', 'énergie'],
            'éducation': ['école', 'université', 'formation', 'apprentissage', 'enseignement', 'étudiant'],
            'sport': ['football', 'basketball', 'tennis', 'jeux', 'compétition', 'équipe'],
            'politique': ['gouvernement', 'élection', 'président', 'ministre', 'parlement', 'politique'],
            'culture': ['art', 'musique', 'cinéma', 'livre', 'théâtre', 'festival']
        }
        
        original_words = set(keywords.lower().split())
        suggested_keywords = set()
        
        # 1. Direct semantic matches
        for original_word in original_words:
            if original_word in semantic_patterns:
                suggested_keywords.update(semantic_patterns[original_word])
        
        # 2. Context-based analysis from articles
        word_context = {}
        for article in articles[:15]:  # Analyze more articles
            title = article.get('titre', '').lower()
            content = article.get('resume', '').lower()
            combined_text = f"{title} {content}"
            
            # Extract meaningful phrases (2-3 words)
            words = re.findall(r'\b\w{3,}\b', combined_text)
            
            for i, word in enumerate(words):
                if word in original_words:
                    # Look at surrounding context
                    context_start = max(0, i-3)
                    context_end = min(len(words), i+4)
                    context = words[context_start:context_end]
                    
                    for context_word in context:
                        if (context_word not in original_words and 
                            len(context_word) > 3 and 
                            context_word.isalpha()):
                            word_context[context_word] = word_context.get(context_word, 0) + 1
        
        # 3. Frequency-based filtering with semantic relevance
        relevant_words = []
        for word, freq in word_context.items():
            if freq >= 2:  # Appears in at least 2 articles
                # Check if word is semantically relevant
                if self._is_semantically_relevant(word, keywords, articles):
                    relevant_words.append((word, freq))
        
        # Sort by frequency and relevance
        relevant_words.sort(key=lambda x: x[1], reverse=True)
        
        # Combine semantic matches with context analysis
        final_suggestions = list(suggested_keywords)[:3]  # Top 3 semantic matches
        final_suggestions.extend([word for word, _ in relevant_words[:3]])  # Top 3 context words
        
        return final_suggestions[:5]
    
    def _is_semantically_relevant(self, word: str, keywords: str, articles: List[Dict]) -> bool:
        """Check if a word is semantically relevant to the keywords"""
        # Simple semantic relevance check
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'pour', 'par', 'avec', 'dans', 'sur', 'sous', 'vers', 'chez', 'depuis', 'pendant', 'avant', 'après', 'selon', 'sans', 'comme', 'entre', 'parmi', 'malgré', 'grâce', 'à', 'ce', 'cette', 'ces', 'son', 'sa', 'ses', 'leur', 'leurs', 'notre', 'nos', 'votre', 'vos', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'qui', 'que', 'quoi', 'dont', 'où', 'comment', 'pourquoi', 'quand', 'si', 'alors', 'ainsi', 'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'plus', 'moins', 'très', 'trop', 'assez', 'bien', 'mal', 'mieux', 'pire', 'tout', 'tous', 'toute', 'toutes', 'quelque', 'plusieurs', 'chaque', 'autre', 'même', 'seul', 'premier', 'dernier', 'nouveau', 'nouvelle', 'ancien', 'ancienne', 'grand', 'grande', 'petit', 'petite', 'bon', 'bonne', 'mauvais', 'mauvaise', 'peut', 'être', 'avoir', 'faire', 'dire', 'aller', 'venir', 'voir', 'savoir', 'vouloir', 'pouvoir', 'devoir', 'falloir', 'year', 'years', 'today', 'yesterday', 'tomorrow', 'this', 'that', 'these', 'those', 'here', 'there', 'now', 'then', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'the', 'and', 'but', 'because', 'while', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
        
        if word in stop_words:
            return False
            
        # Check if word appears in context with keywords
        co_occurrence = 0
        for article in articles:
            title = article.get('titre', '').lower()
            content = article.get('resume', '').lower()
            combined_text = f"{title} {content}"
            
            if word in combined_text:
                for keyword in keywords.lower().split():
                    if keyword in combined_text:
                        co_occurrence += 1
                        break
        
        return co_occurrence >= 2
    
    def detect_high_priority_articles(self, articles: List[Dict], keywords: str) -> List[Dict]:
        """Detect high priority articles"""
        high_priority = []
        
        for article in articles:
            priority_score = self._calculate_priority_score(article, keywords)
            
            if priority_score >= 80:
                article_copy = article.copy()
                article_copy['priority_score'] = priority_score
                article_copy['priority_reasons'] = self._get_priority_reasons(article, keywords)
                high_priority.append(article_copy)
        
        high_priority.sort(key=lambda x: x['priority_score'], reverse=True)
        return high_priority
    
    def _calculate_priority_score(self, article: Dict, keywords: str) -> int:
        """Calculate priority score"""
        score = 0
        title = article.get('titre', '').lower()
        content = article.get('resume', '').lower()
        
        # Priority keywords
        for priority_word in self.priority_keywords:
            if priority_word in title:
                score += 30
            elif priority_word in content:
                score += 15
        
        # Keyword prominence
        keywords_list = [k.strip().lower() for k in keywords.split(',')]
        for keyword in keywords_list:
            if keyword in title:
                score += 20
        
        return min(100, score)
    
    def _get_priority_reasons(self, article: Dict, keywords: str) -> List[str]:
        """Get priority reasons"""
        reasons = []
        title = article.get('titre', '').lower()
        
        for priority_word in self.priority_keywords:
            if priority_word in title:
                reasons.append(f"Mot-clé prioritaire: {priority_word}")
        
        if not reasons:
            reasons.append("Score de pertinence élevé")
        
        return reasons
    
    def filter_articles_by_relevance(self, articles: List[Dict], keywords: str, threshold: Optional[int] = None) -> Tuple[List[Dict], Dict]:
        """Filter articles by relevance"""
        threshold = threshold or self.relevance_threshold
        
        filtered_articles = []
        scores = []
        
        print(f"Filtering {len(articles)} articles with {self.provider} AI (threshold: {threshold})")
        
        for i, article in enumerate(articles):
            relevance_score = self.score_article_relevance(article, keywords)
            scores.append(relevance_score)
            
            if relevance_score >= threshold:
                article_copy = article.copy()
                article_copy['relevance_score'] = relevance_score
                filtered_articles.append(article_copy)
        
        stats = {
            'total_articles': len(articles),
            'filtered_articles': len(filtered_articles),
            'average_score': sum(scores) / len(scores) if scores else 0,
            'threshold_used': threshold,
            'provider_used': self.provider,
            'model_used': self.model
        }
        
        print(f"AI Filtering Results ({self.provider}):")
        print(f"  - Filtered articles: {stats['filtered_articles']}/{stats['total_articles']}")
        print(f"  - Average score: {stats['average_score']:.1f}")
        
        return filtered_articles, stats

def create_ai_enhancer(model: Optional[str] = None, user_profile: Optional[Dict] = None) -> MultiProviderAIEnhancer:
    """Factory function to create AI enhancer based on user preferences"""
    if user_profile:
        model = user_profile.get('ai_model', 'openai-gpt3.5')
        threshold = user_profile.get('relevance_threshold', 70)
    else:
        model = model or os.getenv('DEFAULT_AI_MODEL', 'openai-gpt3.5')
        threshold = int(os.getenv('DEFAULT_RELEVANCE_THRESHOLD', '70'))
    
    enhancer = MultiProviderAIEnhancer(model or 'openai-gpt3.5')
    enhancer.relevance_threshold = threshold
    return enhancer
