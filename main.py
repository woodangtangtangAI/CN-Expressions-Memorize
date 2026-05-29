import os
import sys
import json
import datetime
import argparse

import config
from utils.dedup import load_index, save_index, get_total_count, add_expression
from utils.logger import get_logger
from agents.scraper import scrape_all_sources
from agents.processor import process_and_extract
from agents.db_manager import save_expressions

logger = get_logger('main')

def update_run_log(log_file: str, run_info: dict) -> None:
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                log_data = json.load(f)
            except Exception:
                log_data = []
    else:
        log_data = []

    log_data.append(run_info)

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

def main() -> None:
    parser = argparse.ArgumentParser(description="Chinese Expression DB Pipeline")
    parser.add_argument('--dry-run', action='store_true', help="Run without saving to DB")
    args = parser.parse_args()

    # Create directories
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.DB_DIR, exist_ok=True)
    os.makedirs(config.DAILY_DIR, exist_ok=True)
    os.makedirs(config.PRINT_DIR, exist_ok=True)

    start_time = datetime.datetime.now()

    logger.info("=" * 60)
    logger.info("🇨🇳 Chinese Expression DB Pipeline — START")
    logger.info(f"   Timestamp : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Dry-run   : {args.dry_run}")
    logger.info("=" * 60)

    try:
        # Step 0: Load Index & Check Stop Condition
        index_data = load_index(config.INDEX_FILE)
        current_count = get_total_count(index_data)

        if current_count >= config.MAX_EXPRESSIONS:
            logger.info(f"[PIPELINE COMPLETE] {current_count} expressions reached. Target: {config.MAX_EXPRESSIONS}. Shutting down.")
            sys.exit(0)

        logger.info(f"📊 Progress: {current_count}/{config.MAX_EXPRESSIONS} expressions collected so far")

        # Step 1: Scrape
        logger.info("-" * 50)
        logger.info("🔍 Agent 1: Data Scraper starting...")
        raw_texts, _ = scrape_all_sources(config.SOURCES)
        
        logger.info(f"   Scraped {len(raw_texts)} text chunks from news sources")

        if not raw_texts:
            logger.error("❌ No texts scraped. Exiting pipeline.")
            sys.exit(1)

        # Step 2: Process & Extract
        logger.info("-" * 50)
        logger.info("🧠 Agent 2: LLM Processor starting...")
        expressions = process_and_extract(raw_texts, index_data, config.DAILY_TARGET)

        logger.info(f"   Extracted {len(expressions)} unique HSK 4-5 expressions")

        if not expressions:
            logger.error("❌ No expressions extracted. Exiting pipeline.")
            sys.exit(1)

        # Step 3: Save to DB
        logger.info("-" * 50)
        if args.dry_run:
            logger.info(f"[DRY RUN] Skipping DB save. Would save {len(expressions)} expressions.")
            logger.info("Preview (first 3):")
            for i, expr in enumerate(expressions[:3], 1):
                logger.info(f"  {i}. {expr.get('expression')} - {expr.get('meaning_kr')}")
            rows_saved = 0
        else:
            logger.info("💾 Agent 3: Database Manager starting...")
            rows_saved = save_expressions(expressions, index_data)
            logger.info(f"   Saved {rows_saved} expressions to database")

        # Step 4: Update Index
        logger.info("-" * 50)
        logger.info("📝 Updating index...")
        for expr in expressions:
            add_expression(expr["expression"], index_data)

        index_data["last_updated"] = datetime.date.today().isoformat()
        save_index(config.INDEX_FILE, index_data)

        updated_count = get_total_count(index_data)
        logger.info(f"   Index updated. Total: {updated_count}/{config.MAX_EXPRESSIONS}")

        # Step 5: Update Run Log
        run_info = {
            "date": datetime.date.today().isoformat(),
            "expressions_added": len(expressions),
            "total_count": updated_count,
            "status": "dry_run" if args.dry_run else "success",
        }
        update_run_log(config.RUN_LOG_FILE, run_info)

    except Exception:
        logger.exception("🔥 Pipeline failed with unexpected error")
        try:
            update_run_log(
                config.RUN_LOG_FILE,
                {
                    "date": datetime.date.today().isoformat(),
                    "expressions_added": 0,
                    "total_count": get_total_count(load_index(config.INDEX_FILE)),
                    "status": "error",
                }
            )
        except Exception:
            logger.exception("Failed to write error entry to run log")
        sys.exit(1)

    elapsed = datetime.datetime.now() - start_time
    logger.info("=" * 60)
    logger.info("✅ Chinese Pipeline finished successfully")
    logger.info(f"   Total time: {elapsed}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
