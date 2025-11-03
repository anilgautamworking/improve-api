"""Content cleaning utilities"""

import re


def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Raw text content
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_relevant_sections(text: str, keywords: list = None) -> str:
    """
    Extract sections containing relevant keywords
    
    Args:
        text: Full text content
        keywords: List of keywords to search for
        
    Returns:
        Filtered text containing relevant sections
    """
    if not keywords:
        return text
    
    # Default keywords for exam-relevant content
    if not keywords:
        keywords = [
            'budget', 'economy', 'finance', 'banking', 'trade', 'policy',
            'government', 'scheme', 'initiative', 'reform', 'regulation',
            'infrastructure', 'employment', 'energy', 'fiscal', 'monetary'
        ]
    
    paragraphs = text.split('\n\n')
    relevant_paragraphs = []
    
    for para in paragraphs:
        para_lower = para.lower()
        if any(keyword.lower() in para_lower for keyword in keywords):
            relevant_paragraphs.append(para)
    
    if relevant_paragraphs:
        return '\n\n'.join(relevant_paragraphs)
    else:
        # If no keywords found, return original text
        return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text"""
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

