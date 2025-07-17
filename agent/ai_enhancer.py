"""
AI Enhancement Module for News Monitoring
Implements GenAI features for improved accuracy and relevance
"""

import openai
import os
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime
import json

class NewsAIEnhancer:
    """
    AI-powered news analysis and enhancement system
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI enhancer with OpenAI API key"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
        
        # Default relevance threshold
        self.relevance_threshold = 70
        
        # Priority keywords for intelligent alerts
        self.priority_keywords = [
            'breaking', 'urgent', 'alerte', 'crise', 'emergency',
            'nouveauté', 'lancement', 'annonce', 'révolution'
        ]
    
    def score_article_relevance(self, article: Dict, keywords: str) -> int:
        """
        Score article relevance using AI (0-100)
        
        Args:
            article: Article dictionary with 'titre', 'resume', etc.
            keywords: Campaign keywords
            
        Returns:
            Relevance score (0-100)
        """
        try:
            title = article.get('titre', '')
            content = article.get('resume', '')
            source = article.get('source', '')
            
            # Combine article text
            article_text = f"Titre: {title}\nContenu: {content[:300]}\nSource: {source}"
            
            prompt = f"""
Évaluez la pertinence de cet article par rapport aux mots-clés sur une échelle de 0 à 100.

Mots-clés de surveillance: {keywords}

Article:
{article_text}

Critères d'évaluation:
- Correspondance directe avec les mots-clés (40 points)
- Similarité sémantique et contexte (30 points)
- Pertinence du sujet (20 points)
- Qualité de la source (10 points)

Répondez UNIQUEMENT avec un nombre entre 0 et 100.
"""
            
            if not self.api_key:
                # Fallback: Simple keyword matching
                return self._simple_relevance_score(article_text, keywords)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            score_text = response.choices[0].message.content.strip()
            score = int(re.findall(r'\d+', score_text)[0])
            return max(0, min(100, score))
            
        except Exception as e:
            print(f"Error scoring article relevance: {e}")
            # Fallback to simple scoring
            return self._simple_relevance_score(article.get('titre', '') + ' ' + article.get('resume', ''), keywords)
    
    def _simple_relevance_score(self, text: str, keywords: str) -> int:
        """Fallback relevance scoring without AI"""
        text_lower = text.lower()
        keywords_list = [k.strip().lower() for k in keywords.split(',')]
        
        matches = 0
        total_keywords = len(keywords_list)
        
        for keyword in keywords_list:
            if keyword in text_lower:
                matches += 1
        
        # Basic scoring: 100 if all keywords match, proportional otherwise
        score = int((matches / total_keywords) * 100) if total_keywords > 0 else 0
        return min(100, max(20, score))  # Minimum 20 for any article
    
    def expand_keywords(self, original_keywords: str, articles: List[Dict]) -> List[str]:
        """
        AI-powered keyword expansion based on article analysis
        
        Args:
            original_keywords: Original campaign keywords
            articles: List of articles to analyze
            
        Returns:
            List of suggested additional keywords
        """
        try:
            # Extract article titles and content
            article_texts = []
            for article in articles[:10]:  # Analyze top 10 articles
                text = f"{article.get('titre', '')} {article.get('resume', '')}"
                article_texts.append(text[:200])  # Limit text length
            
            combined_text = "\n".join(article_texts)
            
            prompt = f"""
Analysez ces articles liés aux mots-clés "{original_keywords}" et suggérez 5-8 mots-clés supplémentaires pertinents.

Articles:
{combined_text}

Mots-clés originaux: {original_keywords}

Suggérez des mots-clés qui:
1. Sont sémantiquement liés aux originaux
2. Apparaissent fréquemment dans les articles
3. Peuvent élargir la couverture de veille
4. Sont spécifiques et pertinents

Répondez avec une liste séparée par des virgules, sans numérotation.
"""
            
            if not self.api_key:
                return self._simple_keyword_expansion(original_keywords, articles)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            expanded_keywords = response.choices[0].message.content.strip()
            keywords_list = [k.strip() for k in expanded_keywords.split(',') if k.strip()]
            
            return keywords_list[:8]  # Limit to 8 suggestions
            
        except Exception as e:
            print(f"Error expanding keywords: {e}")
            return self._simple_keyword_expansion(original_keywords, articles)
    
    def _simple_keyword_expansion(self, original_keywords: str, articles: List[Dict]) -> List[str]:
        """Fallback keyword expansion without AI"""
        # Simple approach: extract common words from article titles
        word_freq = {}
        
        for article in articles[:10]:
            title = article.get('titre', '').lower()
            words = re.findall(r'\b\w{4,}\b', title)  # Words with 4+ chars
            
            for word in words:
                if word not in original_keywords.lower():
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:5] if freq >= 2]
    
    def detect_high_priority_articles(self, articles: List[Dict], keywords: str) -> List[Dict]:
        """
        Detect high-priority articles for intelligent alerts
        
        Args:
            articles: List of articles to analyze
            keywords: Campaign keywords
            
        Returns:
            List of high-priority articles with priority scores
        """
        high_priority = []
        
        for article in articles:
            priority_score = self._calculate_priority_score(article, keywords)
            
            if priority_score >= 80:  # High priority threshold
                article_copy = article.copy()
                article_copy['priority_score'] = priority_score
                article_copy['priority_reasons'] = self._get_priority_reasons(article, keywords)
                high_priority.append(article_copy)
        
        # Sort by priority score
        high_priority.sort(key=lambda x: x['priority_score'], reverse=True)
        return high_priority
    
    def _calculate_priority_score(self, article: Dict, keywords: str) -> int:
        """Calculate priority score for an article"""
        score = 0
        title = article.get('titre', '').lower()
        content = article.get('resume', '').lower()
        source = article.get('source', '').lower()
        
        # Check for priority keywords
        for priority_word in self.priority_keywords:
            if priority_word in title:
                score += 30
            elif priority_word in content:
                score += 15
        
        # Check for keyword prominence in title
        keywords_list = [k.strip().lower() for k in keywords.split(',')]
        for keyword in keywords_list:
            if keyword in title:
                score += 20
        
        # Source credibility (simplified)
        credible_sources = ['reuters', 'bbc', 'le monde', 'le figaro', 'france24']
        if any(source_name in source for source_name in credible_sources):
            score += 15
        
        # Recent timing (articles are already filtered to 3 days)
        score += 10  # Base recency score
        
        return min(100, score)
    
    def _get_priority_reasons(self, article: Dict, keywords: str) -> List[str]:
        """Get reasons why an article is high priority"""
        reasons = []
        title = article.get('titre', '').lower()
        content = article.get('resume', '').lower()
        
        # Check priority keywords
        for priority_word in self.priority_keywords:
            if priority_word in title or priority_word in content:
                reasons.append(f"Contient le mot-clé prioritaire: {priority_word}")
        
        # Check keyword prominence
        keywords_list = [k.strip().lower() for k in keywords.split(',')]
        for keyword in keywords_list:
            if keyword in title:
                reasons.append(f"Mot-clé principal dans le titre: {keyword}")
        
        if not reasons:
            reasons.append("Score de pertinence élevé")
        
        return reasons
    
    def filter_articles_by_relevance(self, articles: List[Dict], keywords: str, threshold: Optional[int] = None) -> Tuple[List[Dict], Dict]:
        """
        Filter articles by AI relevance score
        
        Args:
            articles: List of articles to filter
            keywords: Campaign keywords
            threshold: Relevance threshold (default: self.relevance_threshold)
            
        Returns:
            Tuple of (filtered_articles, stats)
        """
        threshold = threshold or self.relevance_threshold
        
        filtered_articles = []
        scores = []
        
        print(f"Filtering {len(articles)} articles with AI relevance scoring (threshold: {threshold})")
        
        for i, article in enumerate(articles):
            relevance_score = self.score_article_relevance(article, keywords)
            scores.append(relevance_score)
            
            if relevance_score >= threshold:
                article_copy = article.copy()
                article_copy['relevance_score'] = relevance_score
                filtered_articles.append(article_copy)
            
            if (i + 1) % 5 == 0:  # Progress update every 5 articles
                print(f"Processed {i + 1}/{len(articles)} articles")
        
        # Calculate statistics
        stats = {
            'total_articles': len(articles),
            'filtered_articles': len(filtered_articles),
            'average_score': sum(scores) / len(scores) if scores else 0,
            'threshold_used': threshold,
            'filter_rate': (len(articles) - len(filtered_articles)) / len(articles) * 100 if articles else 0
        }
        
        print(f"AI Filtering Results:")
        print(f"  - Original articles: {stats['total_articles']}")
        print(f"  - Filtered articles: {stats['filtered_articles']}")
        print(f"  - Average relevance score: {stats['average_score']:.1f}")
        print(f"  - Articles filtered out: {stats['filter_rate']:.1f}%")
        
        return filtered_articles, stats

# Global instance
ai_enhancer = NewsAIEnhancer()
