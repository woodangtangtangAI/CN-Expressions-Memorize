import feedparser
import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("scraper")

def fetch_rss(url: str, headers: dict) -> list:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Autodetect encoding or fallback to gbk/utf-8 for Chinese websites
        if response.encoding and response.encoding.lower() == 'iso-8859-1':
            if b'gb2312' in response.content.lower() or b'gbk' in response.content.lower():
                response.encoding = 'gbk'
            else:
                response.encoding = 'utf-8'

        feed = feedparser.parse(response.text)
        
        articles = []
        for entry in feed.entries:
            title = entry.get('title', '')
            description = entry.get('description', '')
            soup = BeautifulSoup(description, "html.parser")
            clean_desc = soup.get_text(separator=' ').strip()
            
            content = f"{title}. {clean_desc}"
            if content and len(content) > 10:
                articles.append(content)
        
        logger.info(f"Successfully fetched {len(articles)} articles from {url}")
        return articles
    except Exception as e:
        logger.error(f"Failed to fetch RSS from {url}: {e}")
        return []

def scrape_all_sources(sources: dict, used_episodes: list = None) -> tuple[list, list]:
    """Scrapes raw text chunks from configured sources.
    Returns:
        tuple: (raw_texts_list, new_episode_urls_list)
    """
    logger.info("Starting scraper for all Chinese news sources...")
    raw_texts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for name, config in sources.items():
        logger.info(f"Processing source: {name}")
        for url in config.get("rss_urls", []):
            articles = fetch_rss(url, headers)
            raw_texts.extend(articles)
            
    # For compatibility with English structure, return empty list for new_episode_urls
    return raw_texts, []
