# Question Quality Optimization Guide

## Overview
The system has been optimized to generate **10-15 high-quality, modern competitive exam-style MCQs per category per day**, instead of processing all articles and generating many questions.

## Key Improvements

### 1. Modern Question Format
Questions are now generated in modern competitive exam style:
- **Self-contained**: Questions and options provide all necessary context (no need to read the article)
- **Conceptual**: Test understanding and application, not just factual recall
- **Statement-based**: Options are complete statements, not fragments

**Example of Modern Format:**
```
Question: Which of the following statements best explains the relationship between 
inflation and economic growth in the context of monetary policy?

A. High inflation always leads to reduced economic growth due to decreased purchasing power
B. Moderate inflation can stimulate economic growth by encouraging spending and investment
C. Inflation has no direct relationship with economic growth as they are independent variables
D. Economic growth is inversely proportional to inflation regardless of policy measures

Answer: B
```

### 2. Daily Limits Per Category
- **Target**: 12 questions per category per day (configurable)
- **Articles**: Maximum 5 articles processed per category
- **Questions per article**: 3-5 questions (reduced from 10-15)

### 3. Smart Processing
- Checks existing questions for the day before processing
- Stops processing when daily limit is reached
- Focuses on top articles (first N articles from RSS feed)
- Trims questions if needed to fit daily limit

## Configuration

Add these to your `.env` file:

```bash
# Limit articles processed per category
MAX_ARTICLES_PER_CATEGORY=5

# Target questions per category per day
QUESTIONS_PER_CATEGORY_PER_DAY=12

# Questions per article (reduced for quality)
QUESTION_COUNT_MIN=3
QUESTION_COUNT_MAX=5
```

## Expected Results

### Before Optimization:
- Processing all articles (11+ articles)
- Generating 95+ questions from all articles
- Many simple factual questions
- Questions require article context

### After Optimization:
- Processing top 5 articles per category
- Generating 10-15 questions per category (12 default)
- Modern, conceptual questions
- Self-contained questions (no article context needed)

**Example Daily Output:**
```
Business: 12 questions
Economy: 12 questions
Total: 24 questions (instead of 95+)
```

## Question Quality Features

### 1. Self-Contained Questions
Questions include all necessary context:
- Relevant facts mentioned in question stem
- Options are complete statements
- No reference to "the article" or "the passage"

### 2. Modern Question Types
- "Which of the following statements is/are correct?"
- "What is the most significant implication of..."
- "Which of the following best explains..."
- "Consider the following statements about..."

### 3. Conceptual Focus
- Economic implications
- Policy analysis
- Cause-effect relationships
- Comparative understanding
- Conceptual clarity

### 4. Complete Options
Each option is a full statement:
- Not just "Yes" or "No"
- Not just numbers or names
- Complete sentences that stand alone

## Adjusting Limits

### Increase Questions Per Day
```bash
# More questions per category
QUESTIONS_PER_CATEGORY_PER_DAY=15

# More articles to process
MAX_ARTICLES_PER_CATEGORY=8
```

### Decrease Questions Per Day
```bash
# Fewer questions per category
QUESTIONS_PER_CATEGORY_PER_DAY=10

# Fewer articles to process
MAX_ARTICLES_PER_CATEGORY=3
```

### Adjust Questions Per Article
```bash
# More questions per article
QUESTION_COUNT_MIN=4
QUESTION_COUNT_MAX=7

# Fewer questions per article
QUESTION_COUNT_MIN=2
QUESTION_COUNT_MAX=4
```

## Monitoring

The pipeline logs show:
- Questions generated per category
- Progress toward daily limit
- Articles processed per category

Example log output:
```
Category 'Business': 5/12 questions
Category 'Business': 10/12 questions
Category 'Business': 12/12 questions
Reached daily limit for category 'Business'. Stopping article processing.
```

## Troubleshooting

### Not Enough Questions Generated
- Increase `MAX_ARTICLES_PER_CATEGORY`
- Increase `QUESTION_COUNT_MAX`
- Check article relevance (some articles may be skipped)

### Too Many Questions
- Decrease `QUESTIONS_PER_CATEGORY_PER_DAY`
- Decrease `MAX_ARTICLES_PER_CATEGORY`

### Quality Issues
- The prompts are optimized for quality, but if questions aren't conceptual enough:
  - Check AI model (use GPT-4 or llama3.1:70b for best quality)
  - Review prompt in `src/generators/mcq_prompts.py`

