"""
Seed categories and exam-category mappings.

This script makes sure every category used by the automation pipeline exists
in the frontend `categories` table and is mapped to the correct exams through
the `exam_category` junction table.

Run this after applying migration `004_add_exam_system` and whenever new
categories are introduced in the pipeline configuration.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from src.database.db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Canonical category catalogue with the exams each category should power
CATEGORY_DEFINITIONS = [
    {
        "name": "Current Affairs",
        "description": "Daily national and international developments relevant for GS and objective papers.",
        "exams": ["UPSC", "Banking", "SSC"]
    },
    {
        "name": "India",
        "description": "Domestic governance, schemes and socio-economic indicators focused on India.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "World",
        "description": "Global diplomacy, geopolitics and worldwide economic shifts.",
        "exams": ["UPSC"]
    },
    {
        "name": "Opinion",
        "description": "Editorial perspectives useful for essays, ethics and interviews.",
        "exams": ["UPSC"]
    },
    {
        "name": "Sports",
        "description": "Major tournaments, sports governance reforms and medals tally.",
        "exams": ["UPSC", "SSC", "Banking"]
    },
    {
        "name": "Business",
        "description": "Corporate affairs, industry trends and strategic business moves.",
        "exams": ["UPSC", "Banking"]
    },
    {
        "name": "Economy",
        "description": "Indian economy, reforms, budgets and macro trends.",
        "exams": ["UPSC", "Banking"]
    },
    {
        "name": "Markets",
        "description": "Capital markets, indices, IPOs and investor sentiment.",
        "exams": ["Banking", "UPSC"]
    },
    {
        "name": "Science & Technology",
        "description": "Technology missions, ISRO/DRDO updates and emerging tech.",
        "exams": ["UPSC", "JEE"]
    },
    {
        "name": "Banking",
        "description": "Banking regulations, digital banking and RBI notifications.",
        "exams": ["Banking"]
    },
    {
        "name": "Macro Economy",
        "description": "Inflation, fiscal metrics, current account and growth outlook.",
        "exams": ["UPSC", "Banking"]
    },
    {
        "name": "Agri Business",
        "description": "Agriculture economy, agri reforms and food processing sector.",
        "exams": ["UPSC"]
    },
    {
        "name": "Money & Banking",
        "description": "Monetary policy, credit flow, NBFCs and financial inclusion.",
        "exams": ["Banking", "UPSC"]
    },
    {
        "name": "Lifestyle",
        "description": "Society, culture and social issues for GS and SSC exams.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "Entertainment",
        "description": "Visual arts, cinema and award circuits relevant for GK.",
        "exams": ["SSC", "UPSC"]
    },
    {
        "name": "Technology",
        "description": "Digital economy, ICT policy, cyber security and AI.",
        "exams": ["UPSC", "JEE", "Banking"]
    },
    {
        "name": "General Knowledge",
        "description": "Static GK and fact-based coverage for prelims.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "Explained",
        "description": "In-depth explainers that decode complex policy issues.",
        "exams": ["UPSC", "Banking"]
    },
    {
        "name": "Trade",
        "description": "Trade policy, export-import data and tariff decisions.",
        "exams": ["UPSC", "Banking"]
    },
    {
        "name": "Polity",
        "description": "Indian Constitution, bills, acts and federal issues.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "History",
        "description": "Ancient, medieval and modern Indian history highlights.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "Geography",
        "description": "Physical and human geography with mapping questions.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "International Relations",
        "description": "Foreign policy, strategic partnerships and multilateral groupings.",
        "exams": ["UPSC"]
    },
    {
        "name": "Environment",
        "description": "Climate change, biodiversity and environmental governance.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "India GK",
        "description": "India-specific static GK and national symbols.",
        "exams": ["UPSC", "SSC"]
    },
    {
        "name": "News This Month",
        "description": "Compiled news capsules for the ongoing month.",
        "exams": ["UPSC", "Banking", "SSC"]
    },
    {
        "name": "News Last 3 Months",
        "description": "Quarterly revision friendly news coverage.",
        "exams": ["UPSC", "Banking", "SSC"]
    },
    {
        "name": "Physics",
        "description": "JEE/NEET physics concepts for STEM competitive exams.",
        "exams": ["JEE", "NEET"]
    },
    {
        "name": "Chemistry",
        "description": "Physical, organic and inorganic chemistry topics.",
        "exams": ["JEE", "NEET"]
    },
    {
        "name": "Mathematics",
        "description": "Core mathematics syllabus for engineering entrance.",
        "exams": ["JEE"]
    },
    {
        "name": "Biology",
        "description": "Botany and zoology concepts required for NEET.",
        "exams": ["NEET"]
    },
]


def _ensure_categories(session):
    """Insert categories if missing and return updated mapping."""
    created = 0
    for definition in CATEGORY_DEFINITIONS:
        result = session.execute(
            text(
                """
                INSERT INTO categories (name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
                """
            ),
            {
                "name": definition["name"],
                "description": definition["description"],
            },
        )
        if result.fetchone():
            created += 1
            logger.info("Created category: %s", definition["name"])

    if created:
        session.commit()

    categories_result = session.execute(text("SELECT id, name FROM categories"))
    categories = {name: cat_id for cat_id, name in categories_result.fetchall()}
    return categories, created


def _map_categories_to_exams(session, exams: dict, categories: dict):
    created = 0
    skipped = 0

    for definition in CATEGORY_DEFINITIONS:
        category_id = categories.get(definition["name"])
        if not category_id:
            logger.warning("Category '%s' missing after insert attempt.", definition["name"])
            continue

        for exam_name in definition["exams"]:
            exam_id = exams.get(exam_name)
            if not exam_id:
                logger.warning("Exam '%s' not found, cannot map category '%s'", exam_name, definition["name"])
                continue

            result = session.execute(
                text(
                    """
                    INSERT INTO exam_category (exam_id, category_id)
                    VALUES (:exam_id, :category_id)
                    ON CONFLICT (exam_id, category_id) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "exam_id": exam_id,
                    "category_id": category_id,
                },
            )

            if result.fetchone():
                created += 1
                logger.info("Mapped %s → %s", exam_name, definition["name"])
            else:
                skipped += 1

    if created:
        session.commit()

    return created, skipped


def seed_exam_categories():
    """Seed categories and exam-category mappings."""
    session = SessionLocal()

    try:
        exams_result = session.execute(text("SELECT id, name FROM exams"))
        exams = {name: exam_id for exam_id, name in exams_result.fetchall()}

        if not exams:
            raise RuntimeError("No exams found. Run the 004_add_exam_system migration first.")

        logger.info("Found exams: %s", ", ".join(sorted(exams.keys())))

        categories, categories_created = _ensure_categories(session)
        logger.info("Total categories in DB: %s (created %s new)", len(categories), categories_created)

        mappings_created, mappings_skipped = _map_categories_to_exams(session, exams, categories)

        logger.info("")
        logger.info("✅ Seeding complete")
        logger.info("   Categories created: %s", categories_created)
        logger.info("   Exam-category mappings created: %s", mappings_created)
        logger.info("   Exam-category mappings skipped (already existed): %s", mappings_skipped)

    except Exception as exc:
        session.rollback()
        logger.error("Error seeding exam-category mappings: %s", exc)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_exam_categories()


