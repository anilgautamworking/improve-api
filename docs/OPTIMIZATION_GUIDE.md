# Optimization Guide

## Overview
This document outlines the optimizations made to reduce token usage and costs, along with recommendations for using Ollama for local inference.

## Optimizations Implemented

### 1. Fixed Answer Validation Bug ✅
**Issue**: Questions were being rejected because the AI returned answers like `"C. WAYMO"` but the validator expected just `"C"`.

**Fix**: Updated validation to extract the letter from formats like:
- `"C. TEXT"` → `"C"`
- `"C TEXT"` → `"C"`
- `"C"` → `"C"`

**Impact**: Previously rejected questions will now be accepted, reducing waste of expensive API calls.

### 2. Reduced Token Usage ✅

#### Content Truncation
- Added `max_content_length = 2500` characters limit
- Content is truncated to first 2500 characters before sending to AI
- Saves ~50-70% of input tokens for long articles

#### Optimized Prompts
- **System Prompt**: Reduced from ~300 tokens to ~80 tokens (73% reduction)
- **User Prompt**: Reduced from ~400 tokens to ~150 tokens (62% reduction)
- Removed verbose instructions and formatting examples
- Kept essential guidelines only

#### Reduced Question Count
- **Max questions**: Reduced from 15 to 10 per article
- **Min questions**: Reduced from 5 to 3 (more flexibility)
- Saves output tokens proportionally

#### Reduced Max Tokens
- OpenAI client `max_tokens`: Reduced from 2000 to 1500
- Still sufficient for 10 questions with explanations

**Total Token Savings**: Approximately **60-70% reduction** per article

## Using Ollama (Local Inference)

### Why Use Ollama?
- **Zero API costs**: Run models locally, no per-token charges
- **Privacy**: Data never leaves your machine
- **Control**: No rate limits or API quotas
- **Speed**: Can be faster for batch processing (no network latency)

### Recommended Models

Based on requirements for structured JSON output and MCQ generation:

#### 1. **llama3.1:8b** ⭐ (Recommended)
```bash
ollama pull llama3.1:8b
```
- **Best balance** of quality, speed, and resource usage
- Excellent instruction following
- Good JSON output
- Requires ~8GB RAM, works on CPU/GPU

#### 2. **llama3.1:70b** (Best Quality)
```bash
ollama pull llama3.1:70b
```
- Highest quality output
- Best for complex content
- Requires ~40GB RAM, needs GPU for reasonable speed

#### 3. **mistral** (Fast & Efficient)
```bash
ollama pull mistral
```
- Good structured outputs
- Smaller model (~7B parameters)
- Faster inference
- Requires ~8GB RAM

#### 4. **qwen2.5:7b** (Alternative)
```bash
ollama pull qwen2.5:7b
```
- Good instruction following
- Efficient token usage
- Requires ~8GB RAM

#### 5. **phi3** (Resource-Constrained)
```bash
ollama pull phi3
```
- Smallest viable option (~3.8B parameters)
- Good for limited RAM (<8GB)
- Lower quality but still functional

### Setup Instructions

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Or download from https://ollama.ai
   ```

2. **Start Ollama Service**:
   ```bash
   ollama serve
   ```

3. **Pull Recommended Model**:
   ```bash
   ollama pull llama3.1:8b
   ```

4. **Configure to Use Ollama**:
   
   **Option A**: Environment Variable
   ```bash
   export USE_OLLAMA=true
   export OLLAMA_MODEL=llama3.1:8b
   export OLLAMA_BASE_URL=http://localhost:11434
   ```

   **Option B**: Code Configuration
   ```python
   from src.ai.ollama_client import OllamaClient
   from src.generators.question_generator import QuestionGenerator
   
   ollama_client = OllamaClient(model="llama3.1:8b")
   generator = QuestionGenerator(client=ollama_client)
   ```

5. **Run Pipeline**:
   ```bash
   python3 ./scripts/run_daily_pipeline.py
   ```

### Hardware Requirements

| Model | RAM | GPU | Speed |
|-------|-----|-----|-------|
| llama3.1:8b | 8GB | Optional | Fast |
| llama3.1:70b | 40GB | Recommended | Slow |
| mistral | 8GB | Optional | Fast |
| qwen2.5:7b | 8GB | Optional | Fast |
| phi3 | 4GB | Optional | Very Fast |

### Performance Comparison

**Token Costs (per 1000 articles)**:
- **GPT-4**: ~$300-500 USD
- **GPT-3.5-turbo**: ~$15-30 USD
- **Ollama (local)**: $0 (hardware/energy costs only)

**Processing Speed**:
- **GPT-4 API**: ~30-60 seconds per article (with network latency)
- **Ollama (GPU)**: ~5-15 seconds per article
- **Ollama (CPU)**: ~20-40 seconds per article

## Expected Results After Optimization

### Before Optimization:
- ❌ 100% question rejection rate (validation bug)
- ❌ ~3000-5000 tokens per article
- ❌ $0.30-0.50 per article (GPT-4)
- ❌ 50-60 seconds per article

### After Optimization:
- ✅ Fixed validation (questions accepted)
- ✅ ~1000-1500 tokens per article (60-70% reduction)
- ✅ $0.09-0.15 per article (GPT-4) or $0 (Ollama)
- ✅ 30-45 seconds per article (with shorter content)

### Cost Savings Example
For processing 100 articles daily:
- **Before**: ~$30-50/day (~$900-1500/month)
- **After (OpenAI)**: ~$9-15/day (~$270-450/month)
- **After (Ollama)**: $0/day (~$0/month, hardware costs only)

## Additional Optimization Tips

1. **Use GPT-3.5-turbo** if OpenAI is required:
   - Set `OPENAI_MODEL=gpt-3.5-turbo` in `.env`
   - 90% cheaper than GPT-4
   - Still good quality for MCQ generation

2. **Batch Processing**: Consider processing articles in parallel (requires async implementation)

3. **Caching**: Cache similar articles to avoid regenerating questions

4. **Content Filtering**: Improve relevance filters to skip non-relevant articles earlier

5. **Content Summarization**: Use a smaller/faster model to summarize before question generation

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3.1:8b
```

### Low Quality Output
- Try a larger model (llama3.1:70b)
- Increase temperature slightly (0.8-0.9)
- Use more specific prompts

### Slow Performance
- Use GPU acceleration if available
- Try smaller models (mistral, phi3)
- Reduce max_content_length further

