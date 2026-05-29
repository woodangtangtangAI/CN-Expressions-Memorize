import os
import json
import time
from google import genai
from google.genai import types
from utils.logger import get_logger
from utils.dedup import is_duplicate

logger = get_logger("processor")

def process_batch(client, texts: list, api_key: str) -> list:
    combined_text = "\n\n---\n\n".join(texts)
    prompt = f"""
You are an expert in Chinese linguistics and HSK 4-5 level daily life and office expressions.
Extract exactly 5 unique, highly natural Chinese expressions from the following text blocks that are suitable for an intermediate learner transitioning from HSK 4 to HSK 5.

Focus on:
- Everyday and workplace Colloquialisms (口语) (e.g., 靠谱, 拖延症)
- Separable Verbs (离合词) (e.g., 帮忙, 请假, 见面)
- Common, practical Four-character Idioms (成语) (e.g., 顺其自然)
- Avoid basic HSK 1-3 vocabulary.
- Avoid overly difficult HSK 6+ literary terms or complex macroeconomic jargon.

Text Blocks:
{combined_text}

Output ONLY a JSON array of objects with the following keys:
- "expression": The target expression in Simplified Chinese
- "pos": Part of Speech (e.g., Separable Verb, Colloquialism, Idiom, Verb, Noun)
- "pinyin": Pinyin with tone marks
- "meaning_kr": Korean meaning
- "original_text": The original sentence where it was found
- "applied_example": ONE highly natural, context-appropriate example sentence reflecting modern Chinese corporate or daily life.

Ensure the output is strictly valid JSON without any markdown formatting.
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            try:
                results = json.loads(response.text)
                if isinstance(results, list):
                    return results
                else:
                    logger.error("JSON is not a list.")
                    return []
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON from LLM response.")
                return []
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"API Error (Attempt {attempt+1}/{max_retries}): {error_msg}")
            if "429" in error_msg or "quota" in error_msg.lower():
                wait_time = (attempt + 1) * 20
                logger.info(f"Rate limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                break
    
    logger.error("Failed to process batch after retries.")
    return []

def process_and_extract(raw_texts: list, index_data: dict, daily_target: int) -> list:
    """Processes scraped texts, extracts expressions using Gemini API, and filters duplicates."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        return []

    client = genai.Client(api_key=api_key)
    valid_expressions = []
    
    # Process in batches of 10 to minimize API hits
    batch_size = 10
    for i in range(0, len(raw_texts), batch_size):
        if len(valid_expressions) >= daily_target:
            logger.info("Daily target reached. Stopping extraction.")
            break

        batch = raw_texts[i:i+batch_size]
        logger.info(f"Sending batch {i//batch_size + 1} ({len(batch)} chunks) to Gemini...")
        
        extracted = process_batch(client, batch, api_key)
        
        # Dedup and validate
        for item in extracted:
            expr = item.get("expression", "")
            if not expr:
                continue
                
            if not is_duplicate(expr, index_data):
                item["source"] = "Scraped_News"
                valid_expressions.append(item)
                logger.info(f"   [Added] {expr} - {item.get('meaning_kr', '')}")
                
                if len(valid_expressions) >= daily_target:
                    break
            else:
                logger.debug(f"   [Duplicate] {expr} skipped.")
                
        # API Delay to avoid rate limit
        time.sleep(5)
        
    return valid_expressions[:daily_target]
