#!/usr/bin/env python3
"""
Seed an admin user for the application.

This script creates an admin user with the specified email and password.
If the user already exists, it will update their role to admin.

Usage:
    python scripts/seed_admin_user.py [--email EMAIL] [--password PASSWORD]
"""

import sys
import os
import argparse
import bcrypt

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_admin_user(email: str, password: str):
    """Create or update an admin user"""
    session = SessionLocal()
    
    try:
        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), 
            bcrypt.gensalt()
        ).decode("utf-8")
        
        # Check if user exists
        result = session.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": email}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            user_id, existing_email, existing_role = existing_user
            if existing_role == "admin":
                logger.info(f"User {email} is already an admin")
                return user_id
            
            # Update existing user to admin
            logger.info(f"Updating user {email} to admin role")
            session.execute(
                text("""
                    UPDATE users 
                    SET role = 'admin', password_hash = :password_hash
                    WHERE id = CAST(:user_id AS uuid)
                """),
                {"user_id": str(user_id), "password_hash": password_hash}
            )
            session.commit()
            logger.info(f"✅ Updated user {email} to admin role")
            return user_id
        else:
            # Create new admin user
            logger.info(f"Creating new admin user: {email}")
            result = session.execute(
                text("""
                    INSERT INTO users (email, password_hash, role)
                    VALUES (:email, :password_hash, 'admin')
                    RETURNING id
                """),
                {"email": email, "password_hash": password_hash}
            )
            user_id = result.fetchone()[0]
            session.commit()
            logger.info(f"✅ Created admin user: {email} (ID: {user_id})")
            return user_id
            
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error creating admin user: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Seed an admin user")
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Admin email address (default: admin@example.com)"
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="Admin password (default: admin123)"
    )
    
    args = parser.parse_args()
    
    if not args.email or not args.password:
        logger.error("Email and password are required")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Seeding Admin User")
    logger.info("=" * 60)
    logger.info(f"Email: {args.email}")
    logger.info(f"Password: {'*' * len(args.password)}")
    logger.info("")
    
    try:
        user_id = seed_admin_user(args.email, args.password)
        logger.info("")
        logger.info("✅ Admin user seeded successfully!")
        logger.info("")
        logger.info("You can now login with:")
        logger.info(f"  Email: {args.email}")
        logger.info(f"  Password: {args.password}")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Failed to seed admin user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

