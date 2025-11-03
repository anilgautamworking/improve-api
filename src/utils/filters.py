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
    'index', 'indicator', 'growth', 'sector', 'industry'
]

# Categories for classification
CATEGORIES = {
    'Business': ['business', 'corporate', 'company', 'market', 'stock', 'share'],
    'Economy': ['economy', 'economic', 'gdp', 'growth', 'inflation', 'fiscal'],
    'Budget': ['budget', 'union budget', 'expenditure', 'revenue', 'allocation'],
    'Polity': ['government', 'ministry', 'policy', 'scheme', 'initiative'],
    'Banking': ['banking', 'rbi', 'reserve bank', 'monetary', 'interest rate'],
    'Trade': ['trade', 'export', 'import', 'commerce', 'trading']
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
    allowed_sources = ["The Hindu", "Indian Express", "PDF", "Economic Survey", "Union Budget", "RBI Bulletin"]
    return source in allowed_sources

