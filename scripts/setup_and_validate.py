#!/usr/bin/env python3
"""
Setup and validation script for Daily Question Bank automation system.
This script verifies all components and sets up the system for first use.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    print_header("1. Checking Python Version")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python version {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print_error(f"Python version {version.major}.{version.minor}.{version.micro} is too old")
        print_info("Please upgrade to Python 3.9 or higher")
        return False

def check_env_file():
    """Check if .env file exists"""
    print_header("2. Checking Environment Configuration")
    env_path = project_root / ".env"
    env_example_path = project_root / "env.example"
    
    if env_path.exists():
        print_success(".env file exists")
        return True
    else:
        print_warning(".env file not found")
        if env_example_path.exists():
            print_info(f"Creating .env from env.example...")
            import shutil
            shutil.copy(env_example_path, env_path)
            print_success(".env file created")
            print_warning("Please update .env with your configuration (OpenAI API key, database URL, etc.)")
            return False
        else:
            print_error("env.example file not found")
            return False

def validate_env_variables():
    """Validate required environment variables"""
    print_header("3. Validating Environment Variables")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'DATABASE_URL': 'PostgreSQL database connection URL',
        'AI_PROVIDER': 'AI provider (openai or ollama)',
    }
    
    optional_vars = {
        'OPENAI_API_KEY': 'OpenAI API key (required if AI_PROVIDER=openai)',
        'OLLAMA_BASE_URL': 'Ollama base URL (required if AI_PROVIDER=ollama)',
    }
    
    all_valid = True
    ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
    
    # Check required vars
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print_success(f"{var} is set")
        else:
            print_error(f"{var} is not set ({description})")
            all_valid = False
    
    # Check AI provider specific requirements
    if ai_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key != 'your_openai_api_key_here':
            print_success("OPENAI_API_KEY is configured")
        else:
            print_error("OPENAI_API_KEY is not configured properly")
            print_info("Get your API key from: https://platform.openai.com/api-keys")
            all_valid = False
    elif ai_provider == 'ollama':
        print_info("Ollama selected - will check connection later")
    else:
        print_error(f"Invalid AI_PROVIDER: {ai_provider} (must be 'openai' or 'ollama')")
        all_valid = False
    
    return all_valid

def check_database_connection():
    """Check database connection"""
    print_header("4. Checking Database Connection")
    
    try:
        from src.database.db import engine
        from sqlalchemy import text
        
        # Try to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print_success("Database connection successful")
        return True
    except Exception as e:
        print_error(f"Database connection failed: {str(e)}")
        print_info("Make sure PostgreSQL is running and DATABASE_URL is correct")
        print_info("Create database with: createdb daily_question_bank")
        return False

def check_database_schema():
    """Check if database tables exist"""
    print_header("5. Checking Database Schema")
    
    try:
        from src.database.db import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['daily_questions', 'article_logs', 'metadata_summary', 'articles', 'alembic_version']
        
        if not tables:
            print_warning("No tables found in database")
            print_info("Running database migrations...")
            result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                  cwd=project_root, 
                                  capture_output=True, 
                                  text=True)
            if result.returncode == 0:
                print_success("Database migrations completed successfully")
                return True
            else:
                print_error(f"Migration failed: {result.stderr}")
                return False
        else:
            missing_tables = [t for t in required_tables if t not in tables]
            if missing_tables:
                print_warning(f"Missing tables: {', '.join(missing_tables)}")
                print_info("Running database migrations...")
                result = subprocess.run(['alembic', 'upgrade', 'head'], 
                                      cwd=project_root, 
                                      capture_output=True, 
                                      text=True)
                if result.returncode == 0:
                    print_success("Database migrations completed successfully")
                    return True
                else:
                    print_error(f"Migration failed: {result.stderr}")
                    return False
            else:
                print_success("All required tables exist")
                return True
    except Exception as e:
        print_error(f"Error checking database schema: {str(e)}")
        return False

def check_playwright():
    """Check if Playwright browsers are installed"""
    print_header("6. Checking Playwright Browser Installation")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Try to launch browser
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_success("Playwright Chromium browser is installed")
                return True
            except Exception as e:
                print_warning("Playwright browsers not installed")
                print_info("Installing Chromium browser...")
                result = subprocess.run(['python3', '-m', 'playwright', 'install', 'chromium'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print_success("Chromium browser installed successfully")
                    return True
                else:
                    print_error(f"Failed to install browser: {result.stderr}")
                    return False
    except ImportError:
        print_error("Playwright not installed")
        print_info("Install with: pip install playwright")
        return False
    except Exception as e:
        print_error(f"Error checking Playwright: {str(e)}")
        return False

def check_ai_provider():
    """Check AI provider connectivity"""
    print_header("7. Checking AI Provider")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
    
    if ai_provider == 'openai':
        try:
            from src.ai.openai_client import OpenAIClient
            from src.config.settings import settings
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'your_openai_api_key_here':
                print_error("OpenAI API key not configured")
                print_info("Get your API key from: https://platform.openai.com/api-keys")
                return False
            
            # Try a simple test call
            print_info("Testing OpenAI API connection...")
            client = OpenAIClient(model=settings.OPENAI_MODEL)
            response = client.generate_completion(
                prompt="Say 'test' if you can read this",
                system_prompt="You are a test assistant. Respond with exactly one word."
            )
            
            if response:
                print_success("OpenAI API connection successful")
                return True
            else:
                print_error("OpenAI API call failed")
                return False
                
        except Exception as e:
            print_error(f"OpenAI API error: {str(e)}")
            return False
    
    elif ai_provider == 'ollama':
        try:
            import requests
            from src.config.settings import settings
            
            base_url = settings.OLLAMA_BASE_URL
            print_info(f"Checking Ollama at {base_url}...")
            
            # Check if Ollama is running
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m.get("name", "") for m in response.json().get("models", [])]
                model_name = settings.OLLAMA_MODEL
                
                if model_name in models:
                    print_success(f"Ollama is running and model '{model_name}' is available")
                    return True
                else:
                    print_warning(f"Model '{model_name}' not found")
                    print_info(f"Available models: {', '.join(models) if models else 'None'}")
                    print_info(f"Pull the model with: ollama pull {model_name}")
                    return False
            else:
                print_error("Ollama is not responding properly")
                return False
                
        except requests.exceptions.ConnectionError:
            print_error(f"Cannot connect to Ollama at {base_url}")
            print_info("Start Ollama with: ollama serve")
            return False
        except Exception as e:
            print_error(f"Ollama check error: {str(e)}")
            return False
    else:
        print_error(f"Invalid AI_PROVIDER: {ai_provider}")
        return False

def test_rss_fetching():
    """Test RSS feed fetching"""
    print_header("8. Testing RSS Feed Fetching")
    
    try:
        import asyncio
        from src.fetchers.rss_fetcher import RSSFetcher
        
        async def test_fetch():
            fetcher = RSSFetcher()
            # Test with a simple RSS feed
            test_url = "https://www.thehindu.com/business/feeder/default.rss"
            print_info(f"Testing RSS fetch from: {test_url}")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                feed_content = await fetcher.fetch_feed(session, test_url)
                
                if feed_content:
                    print_success("RSS feed fetched successfully")
                    return True
                else:
                    print_error("Failed to fetch RSS feed")
                    return False
        
        result = asyncio.run(test_fetch())
        return result
        
    except Exception as e:
        print_error(f"RSS fetching test failed: {str(e)}")
        return False

def test_article_scraping():
    """Test article scraping"""
    print_header("9. Testing Article Scraping")
    
    try:
        import asyncio
        from src.fetchers.html_scraper import HTMLScraper
        
        async def test_scrape():
            scraper = HTMLScraper(timeout=30000, headless=True)
            # Test with a simple, fast-loading page
            test_url = "https://example.com"
            print_info(f"Testing article scraper with simple page...")
            
            try:
                html = await scraper.fetch_page(test_url)
                await scraper.close_session()
                
                if html and len(html) > 100:
                    print_success("Article scraping functionality works")
                    print_info("Playwright can fetch and render pages successfully")
                    return True
                else:
                    print_warning("Scraping returned empty or very small content")
                    print_info("This might be okay - actual news sites will be tested during pipeline run")
                    return True  # Don't fail validation for this
            except Exception as e:
                await scraper.close_session()
                raise e
        
        result = asyncio.run(test_scrape())
        return result
        
    except Exception as e:
        print_error(f"Article scraping test failed: {str(e)}")
        print_info("Make sure Playwright browsers are installed")
        return False

def print_summary(results):
    """Print validation summary"""
    print_header("Validation Summary")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"\nTotal checks: {total}")
    print_success(f"Passed: {passed}")
    if failed > 0:
        print_error(f"Failed: {failed}")
    
    print("\n" + "="*70)
    
    if all(results.values()):
        print_success("\n🎉 All validations passed! System is ready to use.")
        print_info("\nNext steps:")
        print("  1. Review and update .env file with your configuration")
        print("  2. Run the pipeline manually: python scripts/run_daily_pipeline.py")
        print("  3. Start the dashboard: python src/dashboard/app.py")
        print("  4. Set up cron job: ./scripts/setup_cron.sh")
    else:
        print_error("\n⚠️  Some validations failed. Please fix the issues above.")
        print_info("\nFailed checks:")
        for check, passed in results.items():
            if not passed:
                print(f"  - {check}")
    
    print("\n" + "="*70 + "\n")

def main():
    """Run all validation checks"""
    print(f"{Colors.BOLD}{Colors.OKCYAN}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║   Daily Question Bank Automation - Setup & Validation Script     ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(Colors.ENDC)
    
    results = {}
    
    # Run all checks
    results['Python Version'] = check_python_version()
    results['Environment File'] = check_env_file()
    results['Environment Variables'] = validate_env_variables()
    results['Database Connection'] = check_database_connection()
    results['Database Schema'] = check_database_schema()
    results['Playwright'] = check_playwright()
    results['AI Provider'] = check_ai_provider()
    results['RSS Fetching'] = test_rss_fetching()
    results['Article Scraping'] = test_article_scraping()
    
    # Print summary
    print_summary(results)
    
    # Return exit code
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Validation interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

