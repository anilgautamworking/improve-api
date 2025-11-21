#!/usr/bin/env python3
"""
Debug script to test the transaction abortion fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.db import get_db_session
from src.database.repositories.article_repository import ArticleRepository
from src.database.repositories.article_log_repository import ArticleLogRepository
from src.pipeline.orchestrator import PipelineOrchestrator

def test_transaction_handling():
    """Test that transaction abortion is handled properly"""
    print("Testing transaction handling...")

    with get_db_session() as db_session:
        try:
            article_repo = ArticleRepository(db_session)
            article_log_repo = ArticleLogRepository(db_session)

            orchestrator = PipelineOrchestrator(db_session)

            # Try to process articles - this should handle transaction abortion gracefully
            print("Calling process_articles_from_db...")
            results = orchestrator.process_articles_from_db()

            print(f"Processing completed. Generated {len(results)} question batches.")

            # Check stats
            print(f"Stats: {orchestrator.stats}")

        except Exception as e:
            print(f"Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_transaction_handling()
