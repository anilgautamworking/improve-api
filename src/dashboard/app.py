"""Flask admin dashboard"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.metadata_repository import MetadataRepository
from src.database.repositories.article_repository import ArticleRepository
from src.database.db import SessionLocal
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = settings.DASHBOARD_SECRET_KEY

# Store session in Flask app context
@app.before_request
def before_request():
    """Create database session before each request"""
    from flask import g
    g.db_session = SessionLocal()

@app.teardown_appcontext
def teardown_db(error):
    """Close database session after each request"""
    from flask import g
    db_session = g.pop('db_session', None)
    if db_session:
        db_session.close()

# Initialize repositories with session from Flask context
def get_repositories():
    """Get fresh repository instances with database session from Flask context"""
    from flask import g
    session = g.db_session
    return (
        QuestionRepository(session),
        MetadataRepository(session),
        ArticleRepository(session)
    )


@app.route('/')
def index():
    """Dashboard home page"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        question_repo, metadata_repo, article_repo = get_repositories()
        
        # Get today's summary
        today_summary = metadata_repo.get_summary_by_date(today)
        
        # Get recent summaries (last 7 days)
        recent_summaries = metadata_repo.get_recent_summaries(limit=7)
        
        # Get total questions count
        total_questions = question_repo.get_total_questions_count()
        
        # Get recent questions
        today_questions = question_repo.get_questions_by_date(today)
        
        # Get failed articles (method doesn't exist, so just empty list)
        failed_articles = []
        
        from datetime import datetime as dt
        
        return render_template('dashboard.html',
                             today_summary=today_summary,
                             recent_summaries=recent_summaries,
                             total_questions=total_questions,
                             today_questions=today_questions,
                             failed_articles=failed_articles,
                             datetime=dt)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        question_repo, metadata_repo, article_repo = get_repositories()
        today_summary = metadata_repo.get_summary_by_date(today)
        
        if today_summary:
            stats = {
                'date': today_summary.date,
                'feeds_processed': today_summary.feeds_processed,
                'articles_fetched': today_summary.articles_fetched,
                'articles_processed': today_summary.articles_processed,
                'articles_failed': today_summary.articles_failed,
                'articles_skipped': today_summary.articles_skipped,
                'questions_generated': today_summary.questions_generated,
                'errors_count': today_summary.errors_count,
                'processing_time_seconds': today_summary.processing_time_seconds
            }
        else:
            stats = {
                'date': today,
                'feeds_processed': 0,
                'articles_fetched': 0,
                'articles_processed': 0,
                'articles_failed': 0,
                'articles_skipped': 0,
                'questions_generated': 0,
                'errors_count': 0,
                'processing_time_seconds': None
            }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions/<date>')
def api_questions_by_date(date):
    """API endpoint for questions by date"""
    try:
        question_repo, metadata_repo, article_repo = get_repositories()
        questions = question_repo.get_questions_by_date(date)
        result = []
        
        for q in questions:
            result.append({
                'id': q.id,
                'source': q.source,
                'category': q.category,
                'date': q.date,
                'total_questions': q.total_questions,
                'created_at': q.created_at.isoformat() if q.created_at else None
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching questions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/summaries')
def api_summaries():
    """API endpoint for recent summaries"""
    try:
        question_repo, metadata_repo, article_repo = get_repositories()
        limit = int(request.args.get('limit', 30))
        summaries = metadata_repo.get_recent_summaries(limit=limit)
        
        result = []
        for s in summaries:
            result.append({
                'date': s.date,
                'feeds_processed': s.feeds_processed,
                'articles_fetched': s.articles_fetched,
                'articles_processed': s.articles_processed,
                'articles_failed': s.articles_failed,
                'articles_skipped': s.articles_skipped,
                'questions_generated': s.questions_generated,
                'errors_count': s.errors_count,
                'processing_time_seconds': s.processing_time_seconds
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching summaries: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    # Debug mode configuration - default to False for security
    # Set FLASK_DEBUG=true in .env for development
    flask_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    flask_env = os.getenv("FLASK_ENV", "production").lower()
    
    # Warn if debug mode is enabled in production-like environment
    if flask_debug and flask_env == "production":
        logger.warning("=" * 80)
        logger.warning("⚠️  WARNING: Debug mode is enabled in production environment!")
        logger.warning("This is a security risk. Set FLASK_DEBUG=False for production.")
        logger.warning("=" * 80)
    elif flask_debug:
        logger.info(f"Debug mode enabled (FLASK_ENV={flask_env})")
    
    logger.info(f"Starting Dashboard on {settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}")
    logger.info(f"Debug mode: {flask_debug}, Environment: {flask_env}")
    app.run(host=settings.DASHBOARD_HOST, port=settings.DASHBOARD_PORT, debug=flask_debug)

