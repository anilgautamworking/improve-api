# Article Scoring and Selection Guide

## Overview

The system now **evaluates ALL articles** from RSS feeds before processing, then selects only the best ones for question generation. This ensures we don't miss important articles while still processing only the top candidates.

## How It Works

### 1. Fetch All Articles
- Fetches ALL articles from today's RSS feeds
- No articles are skipped at this stage
- All articles are evaluated

### 2. Score Each Article
Articles are scored based on multiple factors:

#### Scoring Factors (Total: 100 points)

1. **Relevance to Exam Topics (40 points)**
   - Checks for exam-relevant keywords (budget, economy, finance, policy, etc.)
   - More relevant keywords = higher score

2. **Category Match (20 points)**
   - How well the article matches the target category
   - Category-specific keywords boost score

3. **High-Value Keywords (20 points)**
   - Policy, scheme, initiative, reform, regulation
   - Budget, GDP, inflation, RBI, monetary policy
   - Government, ministry, commission, report
   - These indicate strong question potential

4. **Data/Statistics Presence (10 points)**
   - Numbers, percentages, comparisons
   - Indicates factual content good for MCQs

5. **Conceptual Content (10 points)**
   - Implications, impacts, relationships
   - Cause-effect, strategies, frameworks
   - Indicates depth suitable for conceptual questions

### 3. Rank and Select
- All articles are ranked by score (highest first)
- Top N articles are selected (default: 5 per category)
- Only selected articles are processed for question generation

### 4. Process Selected Articles
- Full content is scraped only for selected articles
- Questions are generated from selected articles
- Daily limits still apply (12 questions per category)

## Example Flow

```
1. Fetch RSS Feed → 11 articles today
2. Score all 11 articles:
   - Article A: 85.3 points (high relevance, data, concepts)
   - Article B: 72.1 points (good category match)
   - Article C: 68.5 points (moderate relevance)
   - Article D: 45.2 points (low relevance)
   - ... (11 articles total)
3. Select top 5 articles (A, B, C, ...)
4. Process only selected articles
5. Generate questions (12 per category)
```

## Scoring Criteria Details

### High-Value Keywords
These keywords indicate articles with strong question potential:
- Policy, scheme, initiative, reform, regulation, act, bill
- Budget, allocation, expenditure, revenue, fiscal
- GDP, growth, inflation, deficit, surplus
- RBI, reserve bank, monetary, interest rate, repo rate
- Trade, export, import, balance
- Government, ministry, department, commission, committee
- Report, survey, index, indicator

### Data Indicators
- Percentages, numbers, comparisons
- "Increased by", "decreased to", "compared with"
- Crore, billion, million
- Statistical data

### Conceptual Indicators
- Implications, impacts, effects
- Cause-effect relationships
- Strategies, approaches, frameworks
- Significance, importance

## Benefits

1. **No Important Articles Missed**
   - All articles are evaluated
   - Best articles are identified before processing
   - No random selection

2. **Efficient Processing**
   - Only process top articles
   - Saves time and resources
   - Focuses on quality content

3. **Better Question Quality**
   - Articles with high scores = better question potential
   - Data-rich articles = factual questions
   - Conceptual articles = analytical questions

4. **Transparent Selection**
   - Scores are logged for visibility
   - Can see why articles were selected
   - Easy to debug and improve

## Configuration

No additional configuration needed! The scoring happens automatically.

However, you can adjust:
```bash
# Number of top articles to select per category
MAX_ARTICLES_PER_CATEGORY=5

# Increase for more articles (but slower processing)
MAX_ARTICLES_PER_CATEGORY=8

# Decrease for fewer articles (faster processing)
MAX_ARTICLES_PER_CATEGORY=3
```

## Logs

The pipeline logs show:
```
Evaluating 11 articles for category 'Business'...
Article scoring complete. Top score: 85.3, Bottom score: 23.1
Selected top 5 articles for category 'Business' (scores: ['85.3', '72.1', '68.5', '65.2', '58.9'])
```

## Troubleshooting

### Low Scores
If articles score low (< 30):
- Check if RSS feed has descriptions/summaries
- Verify category keywords match
- Articles might genuinely be low relevance

### High Scores But Poor Questions
- Scoring is based on metadata (title, description)
- Full content might differ
- Consider improving scoring algorithm

### Want Different Articles Selected
- Adjust `MAX_ARTICLES_PER_CATEGORY` to process more
- Modify scoring weights in `article_scorer.py`
- Review scoring criteria for your needs

## Customization

To customize scoring, edit `src/utils/article_scorer.py`:

```python
# Adjust scoring weights
score += relevance_score * 0.4  # Change 0.4 to adjust weight

# Add custom keywords
HIGH_VALUE_KEYWORDS = [
    'your', 'custom', 'keywords', 'here'
]
```

## Summary

✅ **Before**: Randomly selected first N articles  
✅ **After**: Evaluates ALL articles, selects best N articles

This ensures we:
- Don't miss important articles
- Process only the best candidates
- Generate higher quality questions
- Use resources efficiently

