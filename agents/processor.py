import os
import json
import time
import re
from google import genai
from google.genai import types
from utils.dedup import normalize_expression, is_duplicate
from utils.logger import get_logger
import config

logger = get_logger("processor")

def _build_extraction_prompt(text_chunk: str, target_count: int) -> str:
    prompt = f"""당신은 한국인을 위한 중국어 네이티브 표현 교육 전문가이자 최고의 큐레이터입니다.

제시된 [텍스트]는 표현 추출을 위한 주제적 영감(Inspiration)과 소재를 제공하는 참고 자료입니다. 텍스트에 등장하는 단어에만 기계적으로 얽매이지 마세요.
당신의 방대한 중국어 원어민 구어체, 영화, 드라마(드라마 겨우 서른 등), 토크쇼, 일상 회화, 글로벌 비즈니스 및 오피스 환경에 대한 지식베이스를 적극 활용하여, 한국인이 일반 중국어 교재나 시험(HSK 1-3)에서는 배우기 어렵지만 실생활에서 네이티브들이 입에 달고 사는 **진짜 알맹이 표현(HSK 4-5급 전환기에 적합한 이합사, 실전 구어, 핵심 관용구 및 일상 어휘)**을 정확히 {target_count}개 엄선하여 생성해 주세요.

[대상 표현 유형]
1. 이합사 (Separable Verbs): 예) 帮忙, 请假, 见面, 说话, 聊天, 散步
2. 실전 구어 및 오피스 표현 (Colloquialism & Workplace): 예) 靠谱, 拖延症, 脑洞, 炒鱿鱼, 吃香, 泡汤
3. 일상 관용구 및 실용 성어 (Idioms & 成语): 예) 顺其自然, 乱糟糟, 莫名其妙, 一干二净

[★ 엄격한 추출 및 생성 규칙 (위반 시 실패)]
1. **무조건 기본형 표기**:
   - `expression` 필드에는 시제, 수 일치, 인칭 대명사의 변형을 모두 배제한 가장 기본적인 원형(단어 기본형)으로만 기록하세요.
2. **단순 어휘 및 단순 명사구 금지**:
   - 일반 명사, 국가명, macro 경제 수치나 지나치게 단순한 시사 용어(예: 股票, 中国, 经济, 价格)는 학습 가치가 없으므로 절대 제외하세요.
3. **지나치게 쉽거나 뻔한 기초 표현 금지**:
   - 중급 이상 학습자 대상이므로 지나치게 쉽거나 뻔한 표현(예: 看书, 吃饭, 写字)은 제외하고, 실전 원어민 느낌이 물씬 나는 표현으로 큐레이션하세요.
4. **문장 파편/임의 대사 금지**:
   - `expression` 필드에는 관용구나 어휘 자체만 들어가야 합니다. 문장 형태(예: 我要去... 等)는 절대 피하세요.

반드시 아래 JSON 배열 형식으로만 응답하세요. 백틱(`) 기호나 markdown json 블록을 쓰지 말고 순수한 JSON 텍스트로만 응답하세요:
[
  {{
    "expression": "중국어 표현 (예: 靠谱)",
    "pos": "이합사 / 구어 / 관용구 / 동사 / 명사 중 하나",
    "pinyin": "정확한 성조 기호가 포함된 한어 병음 (예: kào pǔ)",
    "meaning_kr": "한국어로 번역된 실제 맥락에서의 자연스러운 의미 (사전적 직역 금지)",
    "original_text": "제시된 텍스트의 맥락을 바탕으로 재구성하거나, 미드/일상/비즈니스 대화에서 이 표현이 쓰일 만한 지극히 자연스러운 원어민 구어체 상황의 문장",
    "applied_example": "이 표현을 일상 대화나 비즈니스에서 바로 사용할 수 있는 새로운 실전 예문 (해석 없이 중국어 문장만 작성)"
  }}
]

[텍스트]
{text_chunk}"""
    return prompt

def _build_backfill_prompt(text_chunk: str, target_count: int, avoid_expressions: list[str]) -> str:
    avoid_str = ", ".join(avoid_expressions[:50])
    prompt = f"""당신은 한국인을 위한 중국어 네이티브 표현 교육 전문가이자 최고의 큐레이터입니다.

제시된 [텍스트]를 참고하여, 아래 기존에 추출된 표현들과 겹치지 않는 새로운 HSK 4-5급 수준의 중국어 네이티브 표현을 정확히 {target_count}개 더 생성하여 엄선해 주세요.

[제외할 기존 표현 목록]
{avoid_str}

[대상 표현 유형]
1. 이합사 (Separable Verbs): 예) 帮忙, 请假, 见面
2. 실전 구어 및 오피스 표현 (Colloquialism & Workplace): 예) 靠谱, 拖延症
3. 일상 관용구 및 실용 성어 (Idioms & 成语): 예) 顺其自然, 莫名其妙

[★ 엄격한 추출 및 생성 규칙 (위반 시 실패)]
1. **무조건 기본형 표기**
2. **단순 어휘 및 단순 명사구 금지**
3. **지나치게 쉽거나 뻔한 기초 표현 금지**
4. **문장 파편/임의 대사 금지**

반드시 아래 JSON 배열 형식으로만 응답하세요. 백틱 기호나 markdown 블록을 쓰지 마세요:
[
  {{
    "expression": "중국어 표현 (예: 靠谱)",
    "pos": "이합사 / 구어 / 관용구 / 동사 / 명사 중 하나",
    "pinyin": "정확한 성조 기호가 포함된 한어 병음 (예: kào pǔ)",
    "meaning_kr": "한국어로 번역된 실제 맥락에서의 자연스러운 의미",
    "original_text": "이 표현이 자연스럽게 쓰일 만한 구어체/비즈니스 대화 상황의 문장",
    "applied_example": "새로운 맥락의 실전 예문"
  }}
]

[텍스트]
{text_chunk}"""
    return prompt

def _call_gemini(prompt: str) -> list[dict]:
    """Call the Gemini API with automatic failover across different models."""
    models_to_try = [
        "gemini-flash-latest",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro"
    ]
    
    if config.GEMINI_MODEL and config.GEMINI_MODEL not in models_to_try:
        models_to_try.insert(0, config.GEMINI_MODEL)
    elif config.GEMINI_MODEL:
        models_to_try.remove(config.GEMINI_MODEL)
        models_to_try.insert(0, config.GEMINI_MODEL)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        return []

    client = genai.Client(api_key=api_key)

    for model_name in models_to_try:
        logger.info(f"Attempting API call with model: {model_name}...")
        for attempt in range(config.API_MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                if not response or not response.text:
                    logger.warning(f"Empty response from {model_name} (attempt {attempt + 1})")
                    time.sleep(5)
                    continue

                response_text = response.text.strip()
                if response_text.startswith('```'):
                    response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
                    response_text = re.sub(r'\n?```\s*$', '', response_text)
                    response_text = response_text.strip()

                parsed = json.loads(response_text)
                if isinstance(parsed, list):
                    logger.info(f"Successfully extracted {len(parsed)} expressions using {model_name}")
                    config.GEMINI_MODEL = model_name
                    return parsed
                else:
                    logger.warning(f"Response from {model_name} is not a list: {type(parsed)}")
                    time.sleep(5)

            except Exception as e:
                logger.warning(f"API call failed with model {model_name} (attempt {attempt + 1}): {e}")
                err_str = str(e).upper()
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "QUOTA" in err_str:
                    logger.warning(f"Quota limits hit for {model_name}. Transitioning to next model...")
                    break
                
                if attempt < config.API_MAX_RETRIES - 1:
                    time.sleep(5)

    logger.error("All models in failover chain failed to return a valid response.")
    return []

def _validate_expression(expr_dict: dict) -> bool:
    required_keys = ['expression', 'pos', 'pinyin', 'meaning_kr', 'original_text', 'applied_example']
    for key in required_keys:
        if key not in expr_dict or not expr_dict[key]:
            return False
            
    expression = str(expr_dict['expression']).strip()
    if len(expression) < 1:
        return False
        
    return True

def process_and_extract(raw_texts: list, index_data: dict, daily_target: int) -> list:
    """Processes scraped texts, extracts expressions using Gemini API in a single call (with optional backfill), and filters duplicates."""
    if not raw_texts:
        logger.warning("No raw texts provided for processing")
        return []

    # Combine all raw texts into a single corpus
    combined_text = ""
    for text in raw_texts:
        t = text.strip()
        if t:
            combined_text += f"---\n{t}\n\n"

    # Truncate text to a safe size to keep prompt size efficient
    if len(combined_text) > 50000:
        logger.info(f"Combined text size ({len(combined_text)} chars) is large. Slicing to 50,000 characters.")
        combined_text = combined_text[:50000]

    results = []
    batch_seen = set()

    # Call 1: Primary Extraction
    logger.info(f"Call 1: Extracting up to {daily_target} Chinese expressions...")
    prompt = _build_extraction_prompt(combined_text, daily_target)
    extracted = _call_gemini(prompt)

    for expr in extracted:
        if not _validate_expression(expr):
            continue
        expression_text = str(expr['expression']).strip()
        normalized = normalize_expression(expression_text)
        if normalized in batch_seen or is_duplicate(normalized, index_data):
            continue

        expr["source"] = "Scraped_News"
        results.append(expr)
        batch_seen.add(normalized)

    logger.info(f"Call 1 complete. Collected {len(results)} / {daily_target} valid expressions.")

    # Call 2 (Optional Backfill)
    shortfall = daily_target - len(results)
    if shortfall > 0:
        logger.info(f"Target shortfall of {shortfall} expressions detected. Initiating Call 2 (Backfill)...")
        avoid_list = [r['expression'] for r in results]
        
        backfill_prompt = _build_backfill_prompt(combined_text, shortfall, avoid_list)
        time.sleep(5)
        
        extracted_backfill = _call_gemini(backfill_prompt)
        backfill_added = 0
        for expr in extracted_backfill:
            if not _validate_expression(expr):
                continue
            expression_text = str(expr['expression']).strip()
            normalized = normalize_expression(expression_text)
            if normalized in batch_seen or is_duplicate(normalized, index_data):
                continue

            expr["source"] = "Scraped_News"
            results.append(expr)
            batch_seen.add(normalized)
            backfill_added += 1
            if len(results) >= daily_target:
                break
        logger.info(f"Call 2 (Backfill) complete. Added {backfill_added} expressions.")

    if len(results) > daily_target:
        results = results[:daily_target]

    logger.info(f"Extraction complete. Total collected: {len(results)} expressions.")
    return results
