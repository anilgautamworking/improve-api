"""
Unified Flask API for frontend integration

This API provides:
- Authentication (signup, login)
- Questions (generate/fetch by category)
- User answers and statistics
- Admin dashboard

Replaces the Express backend from Dailyquestionbank-frontend
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add project root to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, jsonify, request, g
from flask_cors import CORS
import bcrypt
import jwt
from functools import wraps
import logging

from src.database.repositories.question_repository import QuestionRepository
from src.database.repositories.metadata_repository import MetadataRepository
from src.database.repositories.article_repository import ArticleRepository
from src.database.db import SessionLocal, get_migration_status, check_frontend_schema_exists
from src.config.settings import settings
from src.utils.error_handler import (
    error_response, handle_exception, ErrorCode,
    validation_error, not_found_error
)
from sqlalchemy import text

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="../dashboard/templates",
    static_folder="../dashboard/static",
)
app.secret_key = settings.DASHBOARD_SECRET_KEY

# Enable CORS for frontend
# Allow CORS origins from environment variable or default to localhost for development
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
CORS(
    app,
    origins=cors_origins,
    supports_credentials=True,
)

# JWT Configuration
def validate_jwt_secret():
    """Validate JWT secret is set and strong"""
    jwt_secret = os.getenv("JWT_SECRET")
    
    if not jwt_secret:
        raise ValueError(
            "JWT_SECRET environment variable is required. "
            "Please set it in your .env file. "
            "Generate a strong secret: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    
    # Check for default/weak secrets
    weak_secrets = [
        "your-jwt-secret-change-in-production",
        "your-jwt-secret-here-minimum-32-characters",
        "dev-secret",
        "secret",
        "password",
        "123456",
    ]
    
    if jwt_secret in weak_secrets or len(jwt_secret) < 32:
        raise ValueError(
            f"JWT_SECRET is too weak or too short (minimum 32 characters). "
            f"Current value: '{jwt_secret[:20]}...' ({len(jwt_secret)} chars)\n"
            f"Please set a strong secret in your .env file. "
            f"Generate one: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    
    return jwt_secret

JWT_SECRET = validate_jwt_secret()
JWT_ALGORITHM = "HS256"


# Database session management
@app.before_request
def before_request():
    """Create database session before each request"""
    g.db_session = SessionLocal()


@app.teardown_appcontext
def teardown_db(error):
    """Close database session after each request"""
    db_session = g.pop("db_session", None)
    if db_session:
        db_session.close()


def get_repositories():
    """Get repository instances with database session from Flask context"""
    session = g.db_session
    return (
        QuestionRepository(session),
        MetadataRepository(session),
        ArticleRepository(session),
    )


# ==================== Authentication Middleware ====================


def authenticate_token(f):
    """Decorator to require JWT authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return error_response(ErrorCode.AUTH_NO_TOKEN, 401)

        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header

            # Verify and decode token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.user = payload

        except jwt.ExpiredSignatureError:
            return error_response(ErrorCode.AUTH_EXPIRED_TOKEN, 403)
        except jwt.InvalidTokenError:
            return error_response(ErrorCode.AUTH_INVALID_TOKEN, 403)
        except Exception as e:
            return handle_exception(e, ErrorCode.AUTH_INVALID_TOKEN, 403)

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @authenticate_token
    def decorated_function(*args, **kwargs):
        # Check if user has admin role
        user_role = g.user.get("role", "user")
        
        if user_role != "admin":
            logger.warning(f"Non-admin user {g.user.get('userId')} attempted to access admin endpoint")
            return error_response(
                ErrorCode.AUTH_INVALID_TOKEN,
                403,
                message="Admin access required"
            )
        
        return f(*args, **kwargs)
    
    return decorated_function


# ==================== Authentication Routes ====================


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    """User signup endpoint"""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        exam_id = data.get("exam_id")  # Optional exam selection

        if not email or not password:
            return validation_error("email/password", "Email and password are required")

        # Validate exam_id if provided
        if exam_id:
            exam_check = g.db_session.execute(
                text("SELECT id FROM exams WHERE id = CAST(:exam_id AS uuid)"),
                {"exam_id": exam_id}
            ).fetchone()
            if not exam_check:
                return validation_error("exam_id", "Invalid exam_id provided")

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Insert user (role defaults to 'user' via database default)
        if exam_id:
            result = g.db_session.execute(
                text("""
                INSERT INTO users (email, password_hash, exam_id) 
                VALUES (:email, :password_hash, CAST(:exam_id AS uuid)) 
                RETURNING id, email, role, exam_id
            """),
                {"email": email, "password_hash": password_hash, "exam_id": exam_id},
            )
        else:
            result = g.db_session.execute(
                text("""
                INSERT INTO users (email, password_hash) 
                VALUES (:email, :password_hash) 
                RETURNING id, email, role, exam_id
            """),
                {"email": email, "password_hash": password_hash},
            )

        user = result.fetchone()
        g.db_session.commit()

        # Generate JWT token with role
        token = jwt.encode(
            {
                "userId": str(user[0]),
                "email": user[1],
                "role": user[2] or "user",  # Include role in token
                "exam_id": str(user[3]) if user[3] else None,  # Include exam_id if set
                "exp": datetime.utcnow() + timedelta(days=30),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        user_data = {
            "id": str(user[0]),
            "email": user[1],
            "role": user[2] or "user",
            "exam_id": str(user[3]) if user[3] else None
        }

        return jsonify({"user": user_data, "token": token}), 201

    except Exception as e:
        g.db_session.rollback()

        # Check for duplicate email
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return error_response(ErrorCode.AUTH_EMAIL_EXISTS, 400, error=e)

        return handle_exception(e, ErrorCode.SERVER_INTERNAL_ERROR, 400)


@app.route("/api/auth/login", methods=["POST"])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return validation_error("email/password", "Email and password are required")

        # Get user with role and exam_id
        result = g.db_session.execute(
            text("""
            SELECT id, email, password_hash, role, exam_id 
            FROM users 
            WHERE email = :email
        """),
            {"email": email},
        )

        user = result.fetchone()

        if not user:
            return error_response(ErrorCode.AUTH_INVALID_CREDENTIALS, 401)

        # Verify password
        if not bcrypt.checkpw(password.encode("utf-8"), user[2].encode("utf-8")):
            return error_response(ErrorCode.AUTH_INVALID_CREDENTIALS, 401)

        # Generate JWT token with role and exam_id
        token = jwt.encode(
            {
                "userId": str(user[0]),
                "email": user[1],
                "role": user[3] or "user",  # Include role in token
                "exam_id": str(user[4]) if user[4] else None,  # Include exam_id if set
                "exp": datetime.utcnow() + timedelta(days=30),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        user_data = {
            "id": str(user[0]),
            "email": user[1],
            "role": user[3] or "user",
            "exam_id": str(user[4]) if user[4] else None
        }

        return jsonify({"user": user_data, "token": token})

    except Exception as e:
        return handle_exception(e, ErrorCode.SERVER_INTERNAL_ERROR, 400)


# ==================== Exams Route ====================


@app.route("/api/exams", methods=["GET"])
def get_exams():
    """Get all available exams"""
    try:
        result = g.db_session.execute(
            text("""
            SELECT id, name, category, description, created_at
            FROM exams
            ORDER BY name
        """)
        )
        
        exams = []
        for row in result:
            exams.append({
                "id": str(row[0]),
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            })
        
        return jsonify({"exams": exams})
    
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


# ==================== Categories Route ====================


@app.route("/api/categories", methods=["GET"])
@authenticate_token
def get_categories():
    """Get all categories with question counts, filtered by exam_id if provided"""
    # Check if frontend schema exists
    if not check_frontend_schema_exists(g.db_session):
        return jsonify({
            "error": "Frontend schema not found",
            "message": "The frontend schema (questions table) does not exist. Please run: alembic upgrade head"
        }), 503
    
    try:
        # Get exam_id from query param or user's JWT token
        exam_id = request.args.get("exam_id")
        if not exam_id:
            # Try to get from user's JWT token
            exam_id = g.user.get("exam_id") if hasattr(g, "user") else None
        
        # Build query based on exam_id
        if exam_id:
            # Filter categories by exam_id via exam_category junction table
            # Note: DISTINCT not needed due to unique constraint on exam_category
            cat_result = g.db_session.execute(
                text("""
                SELECT c.id, c.name, c.description,
                    CASE c.name
                        WHEN 'News This Month' THEN 1
                        WHEN 'News Last 3 Months' THEN 2
                        WHEN 'Current Affairs' THEN 3
                        WHEN 'India GK' THEN 4
                        WHEN 'History' THEN 5
                        WHEN 'Economy' THEN 6
                        ELSE 7
                    END as sort_order
                FROM categories c
                INNER JOIN exam_category ec ON c.id = ec.category_id
                WHERE ec.exam_id = CAST(:exam_id AS uuid)
                ORDER BY sort_order
            """),
                {"exam_id": exam_id}
            )
        else:
            # Get all categories if no exam_id provided
            cat_result = g.db_session.execute(
                text("""
                SELECT id, name, description
                FROM categories
                ORDER BY 
                    CASE name
                        WHEN 'News This Month' THEN 1
                        WHEN 'News Last 3 Months' THEN 2
                        WHEN 'Current Affairs' THEN 3
                        WHEN 'India GK' THEN 4
                        WHEN 'History' THEN 5
                        WHEN 'Economy' THEN 6
                        ELSE 7
                    END
            """)
            )

        categories = []
        for row in cat_result:
            # Extract category data (ignore sort_order column if present)
            cat_id, cat_name, cat_desc = row[0], row[1], row[2]

            # Build count query with exam_id filter if provided
            if exam_id:
                # For time-based categories, count based on source_date and exam_id
                if cat_name == "News This Month":
                    count_result = g.db_session.execute(
                        text("""
                        SELECT COUNT(*) FROM questions q
                        INNER JOIN exam_category ec ON q.category_id = ec.category_id
                        WHERE q.category_id = CAST(:cat_id AS uuid)
                        AND q.source_date IS NOT NULL 
                        AND q.source_date::DATE >= CURRENT_DATE - INTERVAL '30 days'
                        AND ec.exam_id = CAST(:exam_id AS uuid)
                        """),
                        {"exam_id": exam_id, "cat_id": cat_id}
                    )
                    question_count = count_result.scalar() or 0
                elif cat_name == "News Last 3 Months":
                    count_result = g.db_session.execute(
                        text("""
                        SELECT COUNT(*) FROM questions q
                        INNER JOIN exam_category ec ON q.category_id = ec.category_id
                        WHERE q.category_id = CAST(:cat_id AS uuid)
                        AND q.source_date IS NOT NULL 
                        AND q.source_date::DATE >= CURRENT_DATE - INTERVAL '90 days'
                        AND ec.exam_id = CAST(:exam_id AS uuid)
                        """),
                        {"exam_id": exam_id, "cat_id": cat_id}
                    )
                    question_count = count_result.scalar() or 0
                else:
                    # For regular categories, count by category_id and exam_id
                    count_result = g.db_session.execute(
                        text("""
                        SELECT COUNT(*) FROM questions q
                        INNER JOIN exam_category ec ON q.category_id = ec.category_id
                        WHERE q.category_id = CAST(:cat_id AS uuid)
                        AND ec.exam_id = CAST(:exam_id AS uuid)
                        """),
                        {"cat_id": cat_id, "exam_id": exam_id}
                    )
                    question_count = count_result.scalar() or 0
            else:
                # No exam_id filter - original logic
                if cat_name == "News This Month":
                    count_result = g.db_session.execute(
                        text("""
                        SELECT COUNT(*) FROM questions 
                        WHERE source_date IS NOT NULL 
                        AND source_date::DATE >= CURRENT_DATE - INTERVAL '30 days'
                        """)
                    )
                    question_count = count_result.scalar() or 0
                elif cat_name == "News Last 3 Months":
                    count_result = g.db_session.execute(
                        text("""
                        SELECT COUNT(*) FROM questions 
                        WHERE source_date IS NOT NULL 
                        AND source_date::DATE >= CURRENT_DATE - INTERVAL '90 days'
                        """)
                    )
                    question_count = count_result.scalar() or 0
                else:
                    # For regular categories, count by category_id
                    count_result = g.db_session.execute(
                        text("SELECT COUNT(*) FROM questions WHERE category_id = :cat_id"),
                        {"cat_id": cat_id},
                    )
                    question_count = count_result.scalar() or 0

            categories.append(
                {
                    "id": str(cat_id),
                    "name": cat_name,
                    "description": cat_desc,
                    "question_count": question_count,
                }
            )

        return jsonify({"categories": categories})

    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500, user_id=g.user.get("userId") if hasattr(g, "user") else None)


# ==================== Questions Routes ====================


@app.route("/api/questions/generate", methods=["POST"])
@authenticate_token
def generate_questions():
    """Generate/fetch questions by category, filtered by exam_id if provided"""
    # Check if frontend schema exists
    if not check_frontend_schema_exists(g.db_session):
        return error_response(
            ErrorCode.DB_SCHEMA_MISSING,
            503,
            message="The frontend schema (questions table) does not exist. Please run: alembic upgrade head"
        )
    
    try:
        data = request.get_json()
        category = data.get("category", "all")
        count = data.get("count", 2)
        exam_id = data.get("exam_id")  # Optional exam_id filter
        
        # If no exam_id in request, try to get from user's JWT token
        if not exam_id:
            exam_id = g.user.get("exam_id") if hasattr(g, "user") else None

        logger.info(
            f"[generate_questions] Requested category: '{category}', count: {count}, exam_id: {exam_id}"
        )

        # Build query based on category type and exam_id
        if category == "News This Month":
            # Time-based: Last 30 days
            if exam_id:
                query = text("""
                    SELECT DISTINCT q.* FROM questions q
                    INNER JOIN exam_category ec ON q.category_id = ec.category_id
                    WHERE q.source_date IS NOT NULL 
                    AND q.source_date::DATE >= CURRENT_DATE - INTERVAL '30 days'
                    AND ec.exam_id = CAST(:exam_id AS uuid)
                    ORDER BY q.created_at DESC 
                    LIMIT :limit
                """)
                params = {"exam_id": exam_id, "limit": count * 3}
            else:
                query = text("""
                    SELECT * FROM questions 
                    WHERE source_date IS NOT NULL 
                    AND source_date::DATE >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                params = {"limit": count * 3}

        elif category == "News Last 3 Months":
            # Time-based: Last 90 days
            if exam_id:
                query = text("""
                    SELECT DISTINCT q.* FROM questions q
                    INNER JOIN exam_category ec ON q.category_id = ec.category_id
                    WHERE q.source_date IS NOT NULL 
                    AND q.source_date::DATE >= CURRENT_DATE - INTERVAL '90 days'
                    AND ec.exam_id = CAST(:exam_id AS uuid)
                    ORDER BY q.created_at DESC 
                    LIMIT :limit
                """)
                params = {"exam_id": exam_id, "limit": count * 3}
            else:
                query = text("""
                    SELECT * FROM questions 
                    WHERE source_date IS NOT NULL 
                    AND source_date::DATE >= CURRENT_DATE - INTERVAL '90 days'
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                params = {"limit": count * 3}

        elif category == "all":
            # All questions
            if exam_id:
                query = text("""
                    SELECT DISTINCT q.* FROM questions q
                    INNER JOIN exam_category ec ON q.category_id = ec.category_id
                    WHERE ec.exam_id = CAST(:exam_id AS uuid)
                    ORDER BY q.created_at DESC 
                    LIMIT :limit
                """)
                params = {"exam_id": exam_id, "limit": count * 3}
            else:
                query = text("""
                    SELECT * FROM questions 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                params = {"limit": count * 3}

        else:
            # Specific category
            logger.info(f"[generate_questions] Looking up category: '{category}'")

            # List available categories for debugging
            debug_cats = g.db_session.execute(text("SELECT name FROM categories"))
            available_cats = [row[0] for row in debug_cats]
            logger.info(
                f"[generate_questions] Available categories in DB: {available_cats}"
            )

            cat_result = g.db_session.execute(
                text("""
                SELECT id FROM categories WHERE name = :category
            """),
                {"category": category},
            )

            cat_row = cat_result.fetchone()
            if not cat_row:
                logger.error(
                    f"[generate_questions] Category '{category}' not found in database"
                )
                return jsonify(
                    {
                        "error": f"Category not found: {category}. Available: {available_cats}"
                    }
                ), 404

            # Build query with exam_id filter if provided
            if exam_id:
                # Verify category belongs to exam
                exam_cat_check = g.db_session.execute(
                    text("""
                    SELECT 1 FROM exam_category 
                    WHERE exam_id = CAST(:exam_id AS uuid) 
                    AND category_id = CAST(:category_id AS uuid)
                    """),
                    {"exam_id": exam_id, "category_id": str(cat_row[0])}
                ).fetchone()
                
                if not exam_cat_check:
                    return jsonify({
                        "error": f"Category '{category}' is not available for the selected exam"
                    }), 404
                
                query = text("""
                    SELECT DISTINCT q.* FROM questions q
                    INNER JOIN exam_category ec ON q.category_id = ec.category_id
                    WHERE q.category_id = CAST(:category_id AS uuid)
                    AND ec.exam_id = CAST(:exam_id AS uuid)
                    ORDER BY q.created_at DESC 
                    LIMIT :limit
                """)
                params = {"category_id": str(cat_row[0]), "exam_id": exam_id, "limit": count * 3}
            else:
                query = text("""
                    SELECT * FROM questions 
                    WHERE category_id = CAST(:category_id AS uuid)
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                params = {"category_id": str(cat_row[0]), "limit": count * 3}
            
            logger.info(f"[generate_questions] Querying category_id: {cat_row[0]}, limit: {count * 3}")

        # Fetch questions
        result = g.db_session.execute(query, params)
        questions_data = result.fetchall()
        
        logger.info(f"[generate_questions] Fetched {len(questions_data)} questions from database")

        # Convert to list of dicts
        questions = []
        for row in questions_data:
            # Ensure created_at is always a string (frontend expects non-null string)
            created_at_str = None
            if len(row) > 14 and row[14]:
                created_at_str = row[14].isoformat()
            else:
                # Fallback to current time if missing
                created_at_str = datetime.utcnow().isoformat()

            questions.append(
                {
                    "id": str(row[0]),
                    "category_id": str(row[1]),
                    "question_format": row[2] or "multiple_choice",  # Default if NULL
                    "question_text": row[3] or "",  # Ensure not None
                    "option_a": row[4] if row[4] is not None else None,
                    "option_b": row[5] if row[5] is not None else None,
                    "option_c": row[6] if row[6] is not None else None,
                    "option_d": row[7] if row[7] is not None else None,
                    "correct_answer": row[8] if row[8] is not None else None,
                    "explanation": row[9] or "",  # Ensure not None
                    "difficulty": row[10] or "medium",  # Default if NULL
                    "points": int(row[11])
                    if row[11] is not None
                    else 10,  # Default if NULL
                    "created_at": created_at_str,
                    # Additional fields (not in frontend interface but useful)
                    "source": row[12]
                    if len(row) > 12 and row[12] is not None
                    else None,
                    "source_date": row[13]
                    if len(row) > 13 and row[13] is not None
                    else None,
                }
            )

        # Shuffle and limit
        random.shuffle(questions)
        questions = questions[:count]
        
        logger.info(f"[generate_questions] Returning {len(questions)} questions after shuffle and limit")

        return jsonify({"questions": questions})

    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500, user_id=g.user.get("userId") if hasattr(g, "user") else None)


# ==================== Answers Routes ====================


@app.route("/api/answers", methods=["POST"])
@authenticate_token
def save_answer():
    """Save user answer"""
    try:
        data = request.get_json()
        question_id = data.get("question_id")
        selected_answer = data.get("selected_answer")
        is_correct = data.get("is_correct")
        user_id = g.user["userId"]

        if not question_id:
            return validation_error("question_id", "question_id is required")

        # Cast string UUIDs to UUID type using CAST function
        g.db_session.execute(
            text("""
            INSERT INTO user_answers (user_id, question_id, selected_answer, is_correct)
            VALUES (CAST(:user_id AS uuid), CAST(:question_id AS uuid), :selected_answer, :is_correct)
        """),
            {
                "user_id": user_id,
                "question_id": question_id,
                "selected_answer": selected_answer,
                "is_correct": bool(is_correct),
            },
        )

        g.db_session.commit()

        return jsonify({"success": True})

    except Exception as e:
        g.db_session.rollback()
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500, user_id=g.user.get("userId") if hasattr(g, "user") else None)


@app.route("/api/answers/correct", methods=["GET"])
@authenticate_token
def get_correct_answers():
    """Get list of correctly answered question IDs for user"""
    try:
        user_id = g.user["userId"]

        result = g.db_session.execute(
            text("""
            SELECT question_id 
            FROM user_answers 
            WHERE user_id = CAST(:user_id AS uuid) AND is_correct = true
        """),
            {"user_id": user_id},
        )

        correct_answers = [str(row[0]) for row in result]

        return jsonify({"correctAnswers": correct_answers})

    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500, user_id=g.user.get("userId") if hasattr(g, "user") else None)


# ==================== Statistics Route ====================


@app.route("/api/stats", methods=["GET"])
@authenticate_token
def get_user_stats():
    """Get user statistics"""
    try:
        user_id = g.user["userId"]

        result = g.db_session.execute(
            text("""
            SELECT is_correct 
            FROM user_answers 
            WHERE user_id = CAST(:user_id AS uuid)
        """),
            {"user_id": user_id},
        )

        answers = list(result)
        total_answered = len(answers)
        correct_answers = sum(1 for row in answers if row[0])
        wrong_answers = total_answered - correct_answers

        return jsonify(
            {
                "totalAnswered": total_answered,
                "correctAnswers": correct_answers,
                "wrongAnswers": wrong_answers,
            }
        )

    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500, user_id=g.user.get("userId") if hasattr(g, "user") else None)


# ==================== Admin Dashboard Routes ====================


@app.route("/")
def admin_dashboard():
    """Admin dashboard home page"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        question_repo, metadata_repo, article_repo = get_repositories()

        # Get today's summary
        today_summary = metadata_repo.get_summary_by_date(today)

        # Get recent summaries (last 7 days)
        recent_summaries = metadata_repo.get_recent_summaries(limit=7)

        # Get total questions count
        total_questions = question_repo.get_total_questions_count()

        # Get recent questions
        today_questions = question_repo.get_questions_by_date(today)

        failed_articles = []

        return render_template(
            "dashboard.html",
            today_summary=today_summary,
            recent_summaries=recent_summaries,
            total_questions=total_questions,
            today_questions=today_questions,
            failed_articles=failed_articles,
            datetime=datetime,
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    """API endpoint for admin statistics"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        question_repo, metadata_repo, article_repo = get_repositories()
        today_summary = metadata_repo.get_summary_by_date(today)

        if today_summary:
            stats = {
                "date": today_summary.date,
                "feeds_processed": today_summary.feeds_processed,
                "articles_fetched": today_summary.articles_fetched,
                "articles_processed": today_summary.articles_processed,
                "articles_failed": today_summary.articles_failed,
                "articles_skipped": today_summary.articles_skipped,
                "questions_generated": today_summary.questions_generated,
                "errors_count": today_summary.errors_count,
                "processing_time_seconds": today_summary.processing_time_seconds,
            }
        else:
            stats = {
                "date": today,
                "feeds_processed": 0,
                "articles_fetched": 0,
                "articles_processed": 0,
                "articles_failed": 0,
                "articles_skipped": 0,
                "questions_generated": 0,
                "errors_count": 0,
                "processing_time_seconds": None,
            }

        return jsonify(stats)
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/questions/<date>")
@admin_required
def admin_questions_by_date(date):
    """API endpoint for questions by date (admin)"""
    try:
        question_repo, metadata_repo, article_repo = get_repositories()
        questions = question_repo.get_questions_by_date(date)
        result = []

        for q in questions:
            result.append(
                {
                    "id": q.id,
                    "source": q.source,
                    "category": q.category,
                    "date": q.date,
                    "total_questions": q.total_questions,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
            )

        return jsonify(result)
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/summaries")
@admin_required
def admin_summaries():
    """API endpoint for recent summaries (admin)"""
    try:
        question_repo, metadata_repo, article_repo = get_repositories()
        limit = int(request.args.get("limit", 30))
        summaries = metadata_repo.get_recent_summaries(limit=limit)

        result = []
        for s in summaries:
            result.append(
                {
                    "date": s.date,
                    "feeds_processed": s.feeds_processed,
                    "articles_fetched": s.articles_fetched,
                    "articles_processed": s.articles_processed,
                    "articles_failed": s.articles_failed,
                    "articles_skipped": s.articles_skipped,
                    "questions_generated": s.questions_generated,
                    "errors_count": s.errors_count,
                    "processing_time_seconds": s.processing_time_seconds,
                }
            )

        return jsonify(result)
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/question-library", methods=["GET"])
@admin_required
def admin_get_question_library_stats():
    """Get question library statistics by category and exam"""
    try:
        # Questions by category
        category_stats = g.db_session.execute(
            text("""
                SELECT c.id, c.name, COUNT(q.id) as question_count
                FROM categories c
                LEFT JOIN questions q ON c.id = q.category_id
                GROUP BY c.id, c.name
                ORDER BY question_count DESC, c.name
            """)
        )
        
        questions_by_category = []
        for row in category_stats:
            questions_by_category.append({
                "category_id": str(row[0]),
                "category_name": row[1],
                "question_count": row[2] or 0
            })
        
        # Questions by exam
        exam_stats = g.db_session.execute(
            text("""
                SELECT e.id, e.name, COUNT(DISTINCT q.id) as question_count
                FROM exams e
                LEFT JOIN exam_category ec ON e.id = ec.exam_id
                LEFT JOIN questions q ON ec.category_id = q.category_id
                GROUP BY e.id, e.name
                ORDER BY question_count DESC, e.name
            """)
        )
        
        questions_by_exam = []
        for row in exam_stats:
            questions_by_exam.append({
                "exam_id": str(row[0]),
                "exam_name": row[1],
                "question_count": row[2] or 0
            })
        
        # Total articles
        article_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM articles")
        ).scalar() or 0
        
        # Total questions
        total_questions = g.db_session.execute(
            text("SELECT COUNT(*) FROM questions")
        ).scalar() or 0
        
        # Get orphaned categories (categories not associated with any exam)
        orphaned_categories = g.db_session.execute(
            text("""
                SELECT c.id, c.name, c.description, COUNT(q.id) as question_count
                FROM categories c
                LEFT JOIN exam_category ec ON c.id = ec.category_id
                LEFT JOIN questions q ON c.id = q.category_id
                WHERE ec.category_id IS NULL
                GROUP BY c.id, c.name, c.description
                ORDER BY c.name
            """)
        )
        
        orphaned_list = []
        for row in orphaned_categories:
            orphaned_list.append({
                "category_id": str(row[0]),
                "category_name": row[1],
                "description": row[2],
                "question_count": row[3] or 0
            })
        
        return jsonify({
            "questions_by_category": questions_by_category,
            "questions_by_exam": questions_by_exam,
            "total_articles": article_count,
            "total_questions": total_questions,
            "orphaned_categories": orphaned_list,
            "orphaned_categories_count": len(orphaned_list)
        })
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


# ==================== Admin Exam Management Routes ====================


@app.route("/api/admin/exams", methods=["GET"])
@admin_required
def admin_get_exams():
    """Get all exams (admin)"""
    try:
        result = g.db_session.execute(
            text("""
            SELECT id, name, category, description, created_at
            FROM exams
            ORDER BY name
        """)
        )
        
        exams = []
        for row in result:
            exams.append({
                "id": str(row[0]),
                "name": row[1],
                "category": row[2],
                "description": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            })
        
        return jsonify({"exams": exams})
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams", methods=["POST"])
@admin_required
def admin_create_exam():
    """Create a new exam (admin)"""
    try:
        data = request.get_json()
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")

        if not name:
            return validation_error("name", "Exam name is required")

        result = g.db_session.execute(
            text("""
            INSERT INTO exams (name, category, description)
            VALUES (:name, :category, :description)
            RETURNING id, name, category, description, created_at
        """),
            {"name": name, "category": category, "description": description}
        )
        
        exam_row = result.fetchone()
        g.db_session.commit()

        exam = {
            "id": str(exam_row[0]),
            "name": exam_row[1],
            "category": exam_row[2],
            "description": exam_row[3],
            "created_at": exam_row[4].isoformat() if exam_row[4] else None
        }

        return jsonify(exam), 201
    except Exception as e:
        g.db_session.rollback()
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return error_response(ErrorCode.DB_QUERY_ERROR, 400, message="Exam with this name already exists")
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>", methods=["PUT"])
@admin_required
def admin_update_exam(exam_id):
    """Update an exam (admin)"""
    try:
        data = request.get_json()
        name = data.get("name")
        category = data.get("category")
        description = data.get("description")

        if not name:
            return validation_error("name", "Exam name is required")

        result = g.db_session.execute(
            text("""
            UPDATE exams
            SET name = :name, category = :category, description = :description, updated_at = now()
            WHERE id = CAST(:exam_id AS uuid)
            RETURNING id, name, category, description, created_at
        """),
            {"exam_id": exam_id, "name": name, "category": category, "description": description}
        )
        
        exam_row = result.fetchone()
        if not exam_row:
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Exam not found")

        g.db_session.commit()

        exam = {
            "id": str(exam_row[0]),
            "name": exam_row[1],
            "category": exam_row[2],
            "description": exam_row[3],
            "created_at": exam_row[4].isoformat() if exam_row[4] else None
        }

        return jsonify(exam)
    except Exception as e:
        g.db_session.rollback()
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return error_response(ErrorCode.DB_QUERY_ERROR, 400, message="Exam with this name already exists")
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/orphaned-categories", methods=["GET"])
@admin_required
def admin_get_orphaned_categories():
    """Get categories that are not associated with any exam"""
    try:
        result = g.db_session.execute(
            text("""
                SELECT c.id, c.name, c.description, COUNT(q.id) as question_count
                FROM categories c
                LEFT JOIN exam_category ec ON c.id = ec.category_id
                LEFT JOIN questions q ON c.id = q.category_id
                WHERE ec.category_id IS NULL
                GROUP BY c.id, c.name, c.description
                ORDER BY c.name
            """)
        )
        
        orphaned = []
        for row in result:
            orphaned.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "question_count": row[3] or 0
            })
        
        return jsonify({
            "orphaned_categories": orphaned,
            "count": len(orphaned)
        })
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>/impact", methods=["GET"])
@admin_required
def admin_get_exam_deletion_impact(exam_id):
    """Get impact analysis before deleting an exam (admin)"""
    try:
        # Get exam name
        exam_result = g.db_session.execute(
            text("SELECT name FROM exams WHERE id = CAST(:exam_id AS uuid)"),
            {"exam_id": exam_id}
        )
        exam_row = exam_result.fetchone()
        if not exam_row:
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Exam not found")
        
        exam_name = exam_row[0]
        
        # Count related data
        category_mappings_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM exam_category WHERE exam_id = CAST(:exam_id AS uuid)"),
            {"exam_id": exam_id}
        ).scalar() or 0
        
        user_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE exam_id = CAST(:exam_id AS uuid)"),
            {"exam_id": exam_id}
        ).scalar() or 0
        
        # Get categories that are ONLY associated with this exam (will become orphaned)
        categories_only_this_exam = g.db_session.execute(
            text("""
                SELECT c.id, c.name, COUNT(ec2.exam_id) as other_exam_count
                FROM exam_category ec1
                INNER JOIN categories c ON ec1.category_id = c.id
                LEFT JOIN exam_category ec2 ON c.id = ec2.category_id AND ec2.exam_id != CAST(:exam_id AS uuid)
                WHERE ec1.exam_id = CAST(:exam_id AS uuid)
                GROUP BY c.id, c.name
                HAVING COUNT(ec2.exam_id) = 0
            """),
            {"exam_id": exam_id}
        ).fetchall()
        
        # Count questions that will no longer be accessible through this exam
        # (but questions themselves will NOT be deleted)
        questions_through_exam = g.db_session.execute(
            text("""
                SELECT COUNT(DISTINCT q.id) 
                FROM questions q
                INNER JOIN exam_category ec ON q.category_id = ec.category_id
                WHERE ec.exam_id = CAST(:exam_id AS uuid)
            """),
            {"exam_id": exam_id}
        ).scalar() or 0
        
        orphaned_categories = [{"id": str(row[0]), "name": row[1]} for row in categories_only_this_exam]
        
        return jsonify({
            "exam_name": exam_name,
            "category_mappings_to_remove": category_mappings_count,
            "users_assigned": user_count,
            "questions_no_longer_accessible": questions_through_exam,
            "orphaned_categories": orphaned_categories,
            "orphaned_categories_count": len(orphaned_categories),
            "what_will_happen": {
                "exam_category_mappings": "Will be removed (categories will remain)",
                "user_exam_id": "Will be set to NULL (users will remain)",
                "categories": "Will remain (even if orphaned)",
                "questions": "Will remain (will no longer be accessible through this exam)"
            }
        })
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>", methods=["DELETE"])
@admin_required
def admin_delete_exam(exam_id):
    """Delete an exam (admin)"""
    try:
        result = g.db_session.execute(
            text("""
            DELETE FROM exams
            WHERE id = CAST(:exam_id AS uuid)
            RETURNING id
        """),
            {"exam_id": exam_id}
        )
        
        if not result.fetchone():
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Exam not found")

        g.db_session.commit()
        return jsonify({"success": True})
    except Exception as e:
        g.db_session.rollback()
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


# ==================== Admin Category Management Routes ====================


@app.route("/api/admin/categories", methods=["GET"])
@admin_required
def admin_get_categories():
    """Get all categories (admin)"""
    try:
        result = g.db_session.execute(
            text("""
            SELECT id, name, description, created_at
            FROM categories
            ORDER BY name
        """)
        )
        
        categories = []
        for row in result:
            categories.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "created_at": row[3].isoformat() if row[3] else None
            })
        
        return jsonify({"categories": categories})
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/categories", methods=["POST"])
@admin_required
def admin_create_category():
    """Create a new category (admin)"""
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description")

        if not name or not description:
            return validation_error("name/description", "Category name and description are required")

        result = g.db_session.execute(
            text("""
            INSERT INTO categories (name, description)
            VALUES (:name, :description)
            RETURNING id, name, description, created_at
        """),
            {"name": name, "description": description}
        )
        
        category_row = result.fetchone()
        g.db_session.commit()

        category = {
            "id": str(category_row[0]),
            "name": category_row[1],
            "description": category_row[2],
            "created_at": category_row[3].isoformat() if category_row[3] else None
        }

        return jsonify(category), 201
    except Exception as e:
        g.db_session.rollback()
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return error_response(ErrorCode.DB_QUERY_ERROR, 400, message="Category with this name already exists")
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/categories/<category_id>", methods=["PUT"])
@admin_required
def admin_update_category(category_id):
    """Update a category (admin)"""
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description")

        if not name or not description:
            return validation_error("name/description", "Category name and description are required")

        result = g.db_session.execute(
            text("""
            UPDATE categories
            SET name = :name, description = :description
            WHERE id = CAST(:category_id AS uuid)
            RETURNING id, name, description, created_at
        """),
            {"category_id": category_id, "name": name, "description": description}
        )
        
        category_row = result.fetchone()
        if not category_row:
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Category not found")

        g.db_session.commit()

        category = {
            "id": str(category_row[0]),
            "name": category_row[1],
            "description": category_row[2],
            "created_at": category_row[3].isoformat() if category_row[3] else None
        }

        return jsonify(category)
    except Exception as e:
        g.db_session.rollback()
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return error_response(ErrorCode.DB_QUERY_ERROR, 400, message="Category with this name already exists")
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/categories/<category_id>/impact", methods=["GET"])
@admin_required
def admin_get_category_deletion_impact(category_id):
    """Get impact analysis before deleting a category (admin)"""
    try:
        # Get category name
        cat_result = g.db_session.execute(
            text("SELECT name FROM categories WHERE id = CAST(:category_id AS uuid)"),
            {"category_id": category_id}
        )
        cat_row = cat_result.fetchone()
        if not cat_row:
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Category not found")
        
        category_name = cat_row[0]
        
        # Count related data
        exam_mappings_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM exam_category WHERE category_id = CAST(:category_id AS uuid)"),
            {"category_id": category_id}
        ).scalar() or 0
        
        # Get which exams use this category
        exams_using_category = g.db_session.execute(
            text("""
                SELECT e.id, e.name
                FROM exams e
                INNER JOIN exam_category ec ON e.id = ec.exam_id
                WHERE ec.category_id = CAST(:category_id AS uuid)
            """),
            {"category_id": category_id}
        ).fetchall()
        
        question_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM questions WHERE category_id = CAST(:category_id AS uuid)"),
            {"category_id": category_id}
        ).scalar() or 0
        
        exams_list = [{"id": str(row[0]), "name": row[1]} for row in exams_using_category]
        
        return jsonify({
            "category_name": category_name,
            "exam_mappings_to_remove": exam_mappings_count,
            "exams_using_category": exams_list,
            "questions_count": question_count,
            "warning": "Deleting this category will remove exam mappings, but questions will NOT be deleted. Consider archiving instead.",
            "what_will_happen": {
                "exam_category_mappings": "Will be removed (exams will remain)",
                "questions": "Will remain (but may become orphaned if no other category exists)"
            }
        })
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/categories/<category_id>", methods=["DELETE"])
@admin_required
def admin_delete_category(category_id):
    """Delete a category (admin) - PREVENTS deletion if category has questions"""
    try:
        # First check if category has questions - we NEVER delete questions
        question_count = g.db_session.execute(
            text("SELECT COUNT(*) FROM questions WHERE category_id = CAST(:category_id AS uuid)"),
            {"category_id": category_id}
        ).scalar() or 0
        
        if question_count > 0:
            return error_response(
                ErrorCode.DB_QUERY_ERROR, 
                400, 
                message=f"Cannot delete category: {question_count} question(s) are associated with this category. Questions are never deleted. Please reassign or archive questions first."
            )
        
        # Get category name for response
        cat_result = g.db_session.execute(
            text("SELECT name FROM categories WHERE id = CAST(:category_id AS uuid)"),
            {"category_id": category_id}
        )
        cat_row = cat_result.fetchone()
        if not cat_row:
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Category not found")
        
        category_name = cat_row[0]
        
        # Delete the category (exam_category mappings will be CASCADE deleted)
        result = g.db_session.execute(
            text("""
            DELETE FROM categories
            WHERE id = CAST(:category_id AS uuid)
            RETURNING id
        """),
            {"category_id": category_id}
        )
        
        if not result.fetchone():
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Category not found")

        g.db_session.commit()
        return jsonify({
            "success": True,
            "message": f"Category '{category_name}' deleted successfully. Exam mappings were removed."
        })
    except Exception as e:
        g.db_session.rollback()
        # Check if error is due to foreign key constraint
        if "foreign key" in str(e).lower() or "constraint" in str(e).lower():
            return error_response(
                ErrorCode.DB_QUERY_ERROR,
                400,
                message="Cannot delete category: It is still referenced by other data. Questions are never deleted."
            )
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>/categories", methods=["GET"])
@admin_required
def admin_get_exam_categories(exam_id):
    """Get categories for a specific exam (admin)"""
    try:
        result = g.db_session.execute(
            text("""
            SELECT c.id, c.name, c.description
            FROM categories c
            INNER JOIN exam_category ec ON c.id = ec.category_id
            WHERE ec.exam_id = CAST(:exam_id AS uuid)
            ORDER BY c.name
        """),
            {"exam_id": exam_id}
        )
        
        categories = []
        for row in result:
            categories.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2]
            })
        
        return jsonify({"categories": categories})
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>/categories", methods=["POST"])
@admin_required
def admin_add_exam_category(exam_id):
    """Add a category to an exam (admin)"""
    try:
        data = request.get_json()
        category_id = data.get("category_id")

        if not category_id:
            return validation_error("category_id", "category_id is required")

        result = g.db_session.execute(
            text("""
            INSERT INTO exam_category (exam_id, category_id)
            VALUES (CAST(:exam_id AS uuid), CAST(:category_id AS uuid))
            ON CONFLICT (exam_id, category_id) DO NOTHING
            RETURNING id
        """),
            {"exam_id": exam_id, "category_id": category_id}
        )
        
        if not result.fetchone():
            return error_response(ErrorCode.DB_QUERY_ERROR, 400, message="Category already mapped to this exam")

        g.db_session.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        g.db_session.rollback()
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/admin/exams/<exam_id>/categories/<category_id>", methods=["DELETE"])
@admin_required
def admin_remove_exam_category(exam_id, category_id):
    """Remove a category from an exam (admin)"""
    try:
        result = g.db_session.execute(
            text("""
            DELETE FROM exam_category
            WHERE exam_id = CAST(:exam_id AS uuid) AND category_id = CAST(:category_id AS uuid)
            RETURNING id
        """),
            {"exam_id": exam_id, "category_id": category_id}
        )
        
        if not result.fetchone():
            return error_response(ErrorCode.DB_QUERY_ERROR, 404, message="Category mapping not found")

        g.db_session.commit()
        return jsonify({"success": True})
    except Exception as e:
        g.db_session.rollback()
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


# ==================== Health Check ====================


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint with migration status"""
    try:
        migration_status = get_migration_status()
        
        health_data = {
            "status": "healthy",
            "service": "DailyQuestionBank API",
            "migration": {
                "schema_exists": migration_status["schema_exists"],
                "questions_migrated": migration_status["questions_migrated"],
                "question_count": migration_status["question_count"],
                "batch_count": migration_status["batch_count"],
                "categories_count": migration_status["categories_count"],
                "status": migration_status["status"],
                "message": migration_status["message"]
            }
        }
        
        # Return 503 if schema is missing (service degraded)
        if not migration_status["schema_exists"]:
            health_data["status"] = "degraded"
            return jsonify(health_data), 503
        
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "service": "DailyQuestionBank API",
            "error": "Health check failed"
        }), 500


@app.route("/api/health/migration", methods=["GET"])
def migration_health_check():
    """Detailed migration status endpoint"""
    try:
        migration_status = get_migration_status()
        return jsonify(migration_status)
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


@app.route("/api/health/consistency", methods=["GET"])
def consistency_health_check():
    """Data consistency check endpoint"""
    try:
        from src.utils.data_consistency import get_consistency_status
        consistency_status = get_consistency_status(g.db_session)
        return jsonify(consistency_status)
    except Exception as e:
        return handle_exception(e, ErrorCode.DB_QUERY_ERROR, 500)


# ==================== Startup Checks ====================

def check_migration_on_startup():
    """Check migration status on startup and log warnings if needed"""
    try:
        migration_status = get_migration_status()
        
        if not migration_status["schema_exists"]:
            logger.warning("=" * 80)
            logger.warning("⚠️  FRONTEND SCHEMA NOT FOUND")
            logger.warning("=" * 80)
            logger.warning("The frontend schema (questions table) does not exist.")
            logger.warning("To fix this, run:")
            logger.warning("  alembic upgrade head")
            logger.warning("")
            logger.warning("The API will start but frontend endpoints may not work correctly.")
            logger.warning("=" * 80)
        elif migration_status["status"] == "data_migration_needed":
            logger.warning("=" * 80)
            logger.warning("⚠️  QUESTIONS NOT MIGRATED")
            logger.warning("=" * 80)
            logger.warning(f"Found {migration_status['batch_count']} batches in daily_questions table")
            logger.warning("but no questions in the frontend questions table.")
            logger.warning("To migrate questions, run:")
            logger.warning("  python scripts/migrate_questions_to_frontend_schema.py")
            logger.warning("")
            logger.warning("The API will start but may return empty question lists.")
            logger.warning("=" * 80)
        elif migration_status["status"] == "ready":
            logger.info(f"✓ Migration status: {migration_status['message']}")
            logger.info(f"  Questions: {migration_status['question_count']}")
            logger.info(f"  Categories: {migration_status['categories_count']}")
        else:
            logger.info(f"Migration status: {migration_status['message']}")
            
    except Exception as e:
        logger.error(f"Failed to check migration status on startup: {str(e)}")
        logger.error("API will start but migration status is unknown.")


# Note: Startup checks are run directly in __main__ block
# before_first_request is deprecated in Flask 2.2+


if __name__ == "__main__":
    # Configure port (use environment variable or default)
    port = int(os.getenv("API_PORT", 3001))
    host = os.getenv("API_HOST", "0.0.0.0")
    
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

    # Check migration status before starting
    check_migration_on_startup()
    
    logger.info(f"Starting DailyQuestionBank API on {host}:{port}")
    logger.info(f"Debug mode: {flask_debug}, Environment: {flask_env}")
    app.run(host=host, port=port, debug=flask_debug)
