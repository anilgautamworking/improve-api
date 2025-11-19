"""Content filtering utilities"""

import re
from typing import List, Optional


# Keywords for exam-relevant content
RELEVANT_KEYWORDS = [
    'budget', 'economy', 'finance', 'banking', 'trade', 'policy',
    'government', 'scheme', 'initiative', 'reform', 'regulation',
    'infrastructure', 'employment', 'energy', 'fiscal', 'monetary',
    'rbi', 'reserve bank', 'union budget', 'economic survey', 'gdp',
    'inflation', 'deficit', 'tax', 'revenue', 'expenditure',
    'ministry', 'department', 'commission', 'committee', 'report',
    'index', 'indicator', 'growth', 'sector', 'industry',
    'parliament', 'supreme court', 'lok sabha', 'rajya sabha',
    'diplomatic', 'bilateral', 'multilateral', 'geopolitics',
    'climate', 'environment', 'science', 'technology', 'innovation',
    'research', 'startup', 'space', 'isro', 'drdo', 'sports',
    'olympics', 'world cup', 'cricket', 'hockey', 'football',
    'agriculture', 'farmer', 'crop', 'irrigation', 'rural',
    'msme', 'manufacturing', 'services', 'digital', 'ai', 'cyber',
    'education', 'healthcare', 'vaccination', 'pandemic'
]

# Categories for classification
CATEGORIES = {
    'Business': ['business', 'corporate', 'company', 'industry', 'merger', 'acquisition', 'sector'],
    'Economy': ['economy', 'economic', 'gdp', 'growth', 'inflation', 'fiscal', 'macro', 'survey'],
    'Markets': ['market', 'stock', 'share', 'sensex', 'nifty', 'capital market', 'bse', 'nse'],
    'Banking': ['bank', 'banking', 'rbi', 'reserve bank', 'monetary', 'interest rate'],
    'Money & Banking': ['money', 'credit', 'nbfc', 'lending', 'financial inclusion'],
    'Macro Economy': ['macro', 'inflation', 'headline', 'cad', 'current account', 'fiscal deficit'],
    'Agri Business': ['agri', 'agriculture', 'farmer', 'crop', 'mandi', 'rabi', 'kharif'],
    'Current Affairs': ['government', 'policy', 'scheme', 'cabinet', 'ministry', 'commission'],
    'India': ['india', 'indian', 'state', 'union territory', 'centre', 'domestic'],
    'World': ['world', 'global', 'international', 'united nations', 'bilateral', 'diplomatic'],
    'Opinion': ['opinion', 'editorial', 'column', 'commentary', 'perspective'],
    'General Knowledge': ['gk', 'general knowledge', 'trivia', 'facts', 'awareness'],
    'Sports': ['sport', 'game', 'match', 'tournament', 'league', 'athlete', 'team', 'olympic'],
    'Science & Technology': ['science', 'technology', 'research', 'innovation', 'space', 'isro', 'drdo'],
    'Technology': ['technology', 'digital', 'software', 'hardware', 'ai', 'cyber', 'it'],
    'Entertainment': ['entertainment', 'film', 'movie', 'cinema', 'bollywood', 'hollywood', 'show'],
    'Lifestyle': ['lifestyle', 'health', 'fitness', 'culture', 'travel', 'fashion', 'food'],
    'Explained': ['explained', 'analysis', 'breakdown', 'context'],
    'Trade': ['trade', 'export', 'import', 'commerce', 'fta', 'tariff'],
    'Polity': ['constitution', 'parliament', 'lok sabha', 'rajya sabha', 'bill', 'act'],
    'History': ['history', 'historical', 'freedom struggle', 'heritage', 'ancient', 'medieval'],
    'Geography': ['geography', 'geological', 'mountain', 'river', 'climate', 'monsoon']
}


def is_relevant_content(text: str, keywords: Optional[List[str]] = None) -> bool:
    """
    Check if content is relevant for exam preparation
    
    Args:
        text: Content text to check
        keywords: List of keywords (defaults to RELEVANT_KEYWORDS)
        
    Returns:
        True if content is relevant, False otherwise
    """
    if not text or len(text.strip()) < 100:
        return False
    
    keywords_to_check = keywords or RELEVANT_KEYWORDS
    text_lower = text.lower()
    
    # Check if any keyword appears in text
    for keyword in keywords_to_check:
        if keyword.lower() in text_lower:
            return True
    
    return False


def classify_category(text: str, title: str = "") -> str:
    """
    Classify content into category
    
    Args:
        text: Content text
        title: Article title (optional)
        
    Returns:
        Category name (defaults to "Business")
    """
    combined_text = (title + " " + text).lower()
    
    # Score each category
    category_scores = {}
    for category, keywords in CATEGORIES.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        # Return category with highest score
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    return "Business"  # Default category


def filter_by_source(source: str) -> bool:
    """
    Check if source should be processed
    
    Args:
        source: Source name
        
    Returns:
        True if source should be processed
    """
    allowed_sources = [
        "The Hindu",
        "The Hindu BusinessLine",
        "Indian Express",
        "PDF",
        "Economic Survey",
        "Union Budget",
        "RBI Bulletin"
    ]
    return source in allowed_sources
