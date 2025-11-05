"""Article scoring and ranking utilities"""

import re
import logging
from typing import List, Dict, Optional
from src.utils.filters import RELEVANT_KEYWORDS, CATEGORIES

logger = logging.getLogger(__name__)


class ArticleScorer:
    """Scores articles for question generation potential"""
    
    # High-value keywords that indicate strong question potential
    HIGH_VALUE_KEYWORDS = [
        'policy', 'scheme', 'initiative', 'reform', 'regulation', 'act', 'bill',
        'budget', 'allocation', 'expenditure', 'revenue', 'fiscal',
        'gdp', 'growth', 'inflation', 'deficit', 'surplus',
        'rbi', 'reserve bank', 'monetary', 'interest rate', 'repo rate',
        'trade', 'export', 'import', 'balance', 'deficit',
        'government', 'ministry', 'department', 'commission', 'committee',
        'report', 'survey', 'index', 'indicator',
        'employment', 'unemployment', 'job', 'skill',
        'energy', 'renewable', 'solar', 'wind', 'power',
        'infrastructure', 'development', 'project'
    ]
    
    # Keywords that indicate data/statistics (good for questions)
    DATA_KEYWORDS = [
        'percent', 'percentage', '%', 'crore', 'billion', 'million',
        'increase', 'decrease', 'growth', 'decline', 'rise', 'fall',
        'compared to', 'compared with', 'versus', 'vs',
        'higher than', 'lower than', 'above', 'below'
    ]
    
    # Keywords that indicate conceptual content (good for questions)
    CONCEPTUAL_KEYWORDS = [
        'implication', 'impact', 'effect', 'influence', 'relationship',
        'cause', 'effect', 'due to', 'because of', 'result',
        'significance', 'importance', 'relevance',
        'strategy', 'approach', 'method', 'framework'
    ]

    @staticmethod
    def score_article(article: Dict, target_category: Optional[str] = None) -> float:
        """
        Score an article based on its potential for generating quality questions
        
        Args:
            article: Article dictionary with title, description, summary, etc.
            target_category: Target category (for bonus scoring)
            
        Returns:
            Score between 0.0 and 100.0 (higher is better)
        """
        score = 0.0
        
        # Combine all text fields for analysis
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        summary = article.get('summary', '').lower()
        
        combined_text = f"{title} {description} {summary}"
        
        # 1. Relevance to exam topics (40 points)
        relevance_score = ArticleScorer._score_relevance(combined_text)
        score += relevance_score * 0.4
        
        # 2. Category match (20 points)
        if target_category:
            category_score = ArticleScorer._score_category_match(combined_text, target_category)
            score += category_score * 0.2
        
        # 3. High-value keywords (20 points)
        high_value_score = ArticleScorer._score_high_value_keywords(combined_text)
        score += high_value_score * 0.2
        
        # 4. Data/statistics presence (10 points)
        data_score = ArticleScorer._score_data_presence(combined_text)
        score += data_score * 0.1
        
        # 5. Conceptual content (10 points)
        conceptual_score = ArticleScorer._score_conceptual_content(combined_text)
        score += conceptual_score * 0.1
        
        # Bonus: Title quality (good titles indicate important articles)
        if len(title.split()) >= 5 and len(title.split()) <= 15:
            score += 2.0  # Well-formed titles
        
        # Penalty: Very short articles (less content = fewer questions)
        if len(combined_text) < 200:
            score *= 0.7
        
        # Normalize to 0-100
        return min(100.0, max(0.0, score))

    @staticmethod
    def _score_relevance(text: str) -> float:
        """Score based on relevance keywords (0-100)"""
        found_keywords = sum(1 for keyword in RELEVANT_KEYWORDS if keyword in text)
        # Normalize: 0-5 keywords = 0-50, 5+ = 50-100
        if found_keywords >= 5:
            return 50 + min(50, (found_keywords - 5) * 5)
        else:
            return found_keywords * 10

    @staticmethod
    def _score_category_match(text: str, category: str) -> float:
        """Score based on category match (0-100)"""
        if category not in CATEGORIES:
            return 50.0  # Neutral score if category unknown
        
        category_keywords = CATEGORIES[category]
        matches = sum(1 for keyword in category_keywords if keyword in text)
        
        # Normalize: 0 matches = 0, 1+ matches = 50-100
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 50.0
        else:
            return 50.0 + min(50, (matches - 1) * 25)

    @staticmethod
    def _score_high_value_keywords(text: str) -> float:
        """Score based on high-value keywords (0-100)"""
        found_keywords = sum(1 for keyword in ArticleScorer.HIGH_VALUE_KEYWORDS if keyword in text)
        # More high-value keywords = higher score
        return min(100.0, found_keywords * 10)

    @staticmethod
    def _score_data_presence(text: str) -> float:
        """Score based on data/statistics presence (0-100)"""
        found_data = sum(1 for keyword in ArticleScorer.DATA_KEYWORDS if keyword in text)
        
        # Check for numbers (indicating statistics)
        numbers = len(re.findall(r'\d+', text))
        
        # Combine both indicators
        score = min(50, found_data * 10) + min(50, numbers * 2)
        return min(100.0, score)

    @staticmethod
    def _score_conceptual_content(text: str) -> float:
        """Score based on conceptual keywords (0-100)"""
        found_concepts = sum(1 for keyword in ArticleScorer.CONCEPTUAL_KEYWORDS if keyword in text)
        return min(100.0, found_concepts * 15)

    @staticmethod
    def rank_articles(articles: List[Dict], target_category: Optional[str] = None, 
                     top_n: int = 5) -> List[Dict]:
        """
        Rank articles by score and return top N
        
        Args:
            articles: List of article dictionaries
            target_category: Target category for scoring
            top_n: Number of top articles to return
            
        Returns:
            List of top N articles sorted by score (highest first)
        """
        scored_articles = []
        
        for article in articles:
            score = ArticleScorer.score_article(article, target_category)
            scored_articles.append({
                **article,
                'score': score
            })
        
        # Sort by score (descending)
        scored_articles.sort(key=lambda x: x['score'], reverse=True)
        
        # Log scoring summary
        if scored_articles:
            logger.info(f"Article scoring complete. Top score: {scored_articles[0]['score']:.1f}, "
                       f"Bottom score: {scored_articles[-1]['score']:.1f}")
        
        # Return top N with scores
        top_articles = scored_articles[:top_n]
        for article in top_articles:
            logger.debug(f"Article '{article.get('title', 'Unknown')[:50]}...' scored: {article['score']:.1f}")
        
        return top_articles

