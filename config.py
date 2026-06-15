import os
import datetime
from pathlib import Path

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

# Structured Folders (Local & Repo)
DB_DIR = os.path.join(DATA_DIR, "01_Database")
DAILY_DIR = os.path.join(DATA_DIR, "02_Daily_Sheets")
PRINT_DIR = os.path.join(DATA_DIR, "03_Print_PDF")

INDEX_FILE = os.path.join(DB_DIR, "expressions_index.json")
RUN_LOG_FILE = os.path.join(DB_DIR, "run_log.json")
EXCEL_FILENAME = os.path.join(DB_DIR, "chinese_expressions_db.xlsx")

# Local Drive study path
LOCAL_STUDY_PATH = r"G:\내 드라이브\[언어 공부]\2. 중국어 암기"

# Targets
MAX_EXPRESSIONS = 2000
DAILY_TARGET = 30

# Deduplication
FUZZY_MATCH_THRESHOLD = 0.85

# Gemini API Configuration
GEMINI_MODEL = "gemini-2.5-flash"
API_CALL_DELAY = 10  # seconds between Gemini API calls
API_MAX_RETRIES = 3

# Source Configuration (Optimized for Chinese HSK 4-5)
SOURCES = {
    "Sina_Finance": {
        "rss_urls": [
            "https://finance.sina.com.cn/rss/stock.xml",
        ],
        "target_count": 50,
        "type": "news"
    },
    "Baidu_News": {
        "rss_urls": [
            "http://news.baidu.com/n?cmd=4&class=civilnews&tn=rss",
        ],
        "target_count": 50,
        "type": "news"
    }
}
