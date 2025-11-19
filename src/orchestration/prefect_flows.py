"""Prefect orchestration for the Daily Question Bank pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from prefect import flow, get_run_logger, task
from prefect.artifacts import create_markdown_artifact

from scripts import crawl_feeds, generate_questions
from src.config.settings import settings
from src.utils.graceful_shutdown import init_graceful_shutdown, is_shutdown_requested


def _run_coroutine_sync(coro):
    """Run the given coroutine in a dedicated loop.

    Prefect tasks commonly execute inside worker threads. Using a dedicated
    event loop avoids "event loop already running" errors that asyncio.run can
    trigger when Prefect uses async-based task runners under the hood.
    """

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        asyncio.set_event_loop(None)


def _stats_to_markdown(title: str, stats: Dict[str, Any], errors: Optional[List[str]] = None) -> str:
    """Render a Markdown table for Prefect artifacts."""

    header = ["| Metric | Value |", "| --- | --- |"]
    for key, value in stats.items():
        display_key = key.replace('_', ' ').title()
        header.append(f"| {display_key} | {value} |")

    markdown = f"## {title}\n\n" + "\n".join(header)
    if errors:
        markdown += "\n\n**Errors**\n"
        markdown += "\n".join(f"- {err}" for err in errors)
    return markdown


def _artifact_key(prefix: str) -> str:
    """Return a timestamped artifact key."""

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{ts}"


@task(
    name="Crawl RSS Feeds",
    log_prints=True,
    retries=max(settings.RETRY_ATTEMPTS, 0),
    retry_delay_seconds=settings.RETRY_DELAY,
    timeout_seconds=settings.PREFECT_CRAWLER_TASK_TIMEOUT,
    task_run_name="crawl-rss-feeds-{flow_run.scheduled_start_time:%Y%m%d-%H%M%S}",
)
def crawl_rss_feeds_task() -> Dict[str, Any]:
    """Run stage 1 (RSS crawl) under Prefect orchestration."""

    logger = get_run_logger()
    logger.info("Starting Prefect-managed RSS crawl stage")

    try:
        stats = _run_coroutine_sync(crawl_feeds.run_crawl(logger=logger))
        
        artifact = _stats_to_markdown("Crawler Stage", {k: v for k, v in stats.items() if k != 'errors'}, stats.get('errors'))
        create_markdown_artifact(
            key=_artifact_key("crawler-stage"),
            markdown=artifact,
            description="RSS crawling summary",
        )
        
        return stats
    except Exception as e:
        logger.error(f"Crawler task failed: {str(e)}", exc_info=True)
        # Create error artifact
        error_artifact = _stats_to_markdown("Crawler Stage - Failed", {}, [str(e)])
        create_markdown_artifact(
            key=_artifact_key("crawler-stage-error"),
            markdown=error_artifact,
            description="RSS crawling failure",
        )
        raise


@task(
    name="Generate Questions",
    log_prints=True,
    retries=max(settings.RETRY_ATTEMPTS, 0),
    retry_delay_seconds=settings.RETRY_DELAY,
    timeout_seconds=settings.PREFECT_QUESTION_TASK_TIMEOUT,
    task_run_name="generate-questions-{flow_run.scheduled_start_time:%Y%m%d-%H%M%S}",
)
def generate_questions_task() -> Dict[str, Any]:
    """Run stage 2 (question generation + persistence) under Prefect."""

    logger = get_run_logger()
    logger.info("Starting Prefect-managed question generation stage")

    try:
        results = generate_questions.run_generation(logger=logger)
        question_stats = results.get('question_stats', {})
        combined_stats = {
            'articles_processed': question_stats.get('articles_processed', 0),
            'articles_skipped': question_stats.get('articles_skipped', 0),
            'articles_failed': question_stats.get('articles_failed', 0),
            'questions_generated': question_stats.get('questions_generated', 0),
            'saved_batches': results.get('saved_batches', 0),
            'frontend_saved': results.get('frontend_saved', 0),
            'frontend_skipped': results.get('frontend_skipped', 0),
        }

        artifact = _stats_to_markdown("Question Generation Stage", combined_stats, question_stats.get('errors'))
        create_markdown_artifact(
            key=_artifact_key("question-stage"),
            markdown=artifact,
            description="Question generation + persistence summary",
        )

        return results
    except Exception as e:
        logger.error(f"Question generation task failed: {str(e)}", exc_info=True)
        # Create error artifact
        error_artifact = _stats_to_markdown("Question Generation Stage - Failed", {}, [str(e)])
        create_markdown_artifact(
            key=_artifact_key("question-stage-error"),
            markdown=error_artifact,
            description="Question generation failure",
        )
        raise


@flow(name="Improve API Pipeline", log_prints=True)
def daily_question_bank_flow(
    run_crawler: bool = True,
    run_question_generation: bool = True,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Prefect flow that coordinates crawler + question generation stages."""

    logger = get_run_logger()
    
    # Initialize graceful shutdown handler
    shutdown_handler = init_graceful_shutdown()
    
    logger.info("Prefect flow started. run_crawler=%s run_question_generation=%s", run_crawler, run_question_generation)

    crawler_stats: Optional[Dict[str, Any]] = None
    question_results: Optional[Dict[str, Any]] = None

    try:
        if run_crawler:
            if is_shutdown_requested():
                logger.warning("Shutdown requested, skipping crawler stage")
            else:
                crawler_stats = crawl_rss_feeds_task()

        if run_question_generation:
            if is_shutdown_requested():
                logger.warning("Shutdown requested, skipping question generation stage")
            else:
                question_results = generate_questions_task()
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        raise
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
        # Re-raise to let Prefect handle it properly
        raise

    summary_stats: Dict[str, Any] = {}
    if crawler_stats:
        summary_stats.update({
            'feeds_processed': crawler_stats.get('feeds_processed', 0),
            'articles_fetched': crawler_stats.get('articles_fetched', 0),
            'articles_stored': crawler_stats.get('articles_stored', 0),
        })
    if question_results:
        q_stats = question_results.get('question_stats', {})
        summary_stats.update({
            'articles_processed': q_stats.get('articles_processed', 0),
            'questions_generated': q_stats.get('questions_generated', 0),
            'batches_saved': question_results.get('saved_batches', 0),
        })

    if summary_stats:
        artifact = _stats_to_markdown("Overall Pipeline Summary", summary_stats)
        create_markdown_artifact(
            key=_artifact_key("pipeline-summary"),
            markdown=artifact,
            description="Aggregated pipeline run overview",
        )

    logger.info("Prefect flow finished")
    return {
        'crawler_stats': crawler_stats,
        'question_generation': question_results,
    }


if __name__ == "__main__":
    daily_question_bank_flow()
