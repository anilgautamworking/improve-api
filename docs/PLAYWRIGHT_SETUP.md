# Playwright Setup Guide

## Installation

After installing the Python dependencies, you need to install Playwright browsers:

```bash
# Install Python dependencies first
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Or install all browsers (for testing)
playwright install
```

## Why Playwright?

We use Playwright instead of simple HTTP requests because:

1. **Dynamic Content**: Many modern websites (like Indian Express) load content via JavaScript after the initial page load
2. **Better Reliability**: Playwright waits for network requests to complete, ensuring content is fully loaded
3. **Better Parsing**: Combined with BeautifulSoup and lxml, we get the best of both worlds - reliable fetching and fast parsing

## Configuration

The HTML scraper is configured in `src/fetchers/html_scraper.py`:

- `timeout`: Page load timeout in milliseconds (default: 30000ms = 30 seconds)
- `headless`: Run browser in headless mode (default: True)

## Troubleshooting

If you encounter issues:

1. **Browser not found**: Run `playwright install chromium`
2. **Slow scraping**: Increase timeout or reduce wait times
3. **Memory issues**: Close browser sessions properly - the scraper handles this automatically

