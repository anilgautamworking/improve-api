# AI Provider Configuration Guide

## Quick Switch Between OpenAI and Ollama

The system now supports seamless switching between OpenAI API and local Ollama via environment variables.

## Configuration

All AI provider settings are configured in your `.env` file.

### Option 1: Using OpenAI (Default)

```bash
# In your .env file
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000
```

### Option 2: Using Ollama (Local)

```bash
# In your .env file
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TEMPERATURE=0.7
```

## Setup Steps

### For OpenAI:
1. Get an API key from https://platform.openai.com
2. Add to `.env`:
   ```bash
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4
   ```

### For Ollama:
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

4. **Configure .env**:
   ```bash
   AI_PROVIDER=ollama
   OLLAMA_MODEL=llama3.1:8b
   OLLAMA_BASE_URL=http://localhost:11434
   ```

## Switching Between Providers

Simply change `AI_PROVIDER` in your `.env` file:

```bash
# Switch to Ollama
AI_PROVIDER=ollama

# Switch back to OpenAI
AI_PROVIDER=openai
```

Then restart your pipeline - no code changes needed!

## Recommended Ollama Models

| Model | RAM Required | Quality | Speed | Command |
|-------|-------------|---------|-------|---------|
| **llama3.1:8b** ⭐ | 8GB | Excellent | Fast | `ollama pull llama3.1:8b` |
| llama3.1:70b | 40GB | Best | Slow | `ollama pull llama3.1:70b` |
| mistral | 8GB | Good | Fast | `ollama pull mistral` |
| qwen2.5:7b | 8GB | Good | Fast | `ollama pull qwen2.5:7b` |
| phi3 | 4GB | Fair | Very Fast | `ollama pull phi3` |

## Environment Variables Reference

### AI Provider Selection
- `AI_PROVIDER` - Set to `"openai"` or `"ollama"` (default: `"openai"`)

### OpenAI Settings
- `OPENAI_API_KEY` - Your OpenAI API key (required when `AI_PROVIDER=openai`)
- `OPENAI_MODEL` - Model to use (default: `"gpt-4"`)
- `OPENAI_TEMPERATURE` - Temperature 0.0-2.0 (default: `0.7`)
- `OPENAI_MAX_TOKENS` - Max tokens in response (default: `2000`)

### Ollama Settings
- `OLLAMA_BASE_URL` - Ollama API URL (default: `"http://localhost:11434"`)
- `OLLAMA_MODEL` - Model name to use (default: `"llama3.1:8b"`)
- `OLLAMA_TEMPERATURE` - Temperature 0.0-2.0 (default: `0.7`)

## Troubleshooting

### OpenAI Issues
```bash
# Check if API key is set
echo $OPENAI_API_KEY

# Verify in .env file
cat .env | grep OPENAI
```

### Ollama Issues

**Ollama not running:**
```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

**Model not found:**
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3.1:8b
```

**Connection refused:**
- Make sure Ollama is running: `ollama serve`
- Check the base URL in `.env` matches your Ollama setup
- For remote Ollama, update `OLLAMA_BASE_URL` accordingly

## Example .env File

See `env.example` in the project root for a complete example configuration.

