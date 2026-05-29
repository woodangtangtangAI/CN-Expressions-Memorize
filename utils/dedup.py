import json
import os
from difflib import SequenceMatcher

def load_index(filepath):
    if not os.path.exists(filepath):
        return {
            "total_count": 0,
            "expressions": [],
            "daily_uid_counter": {},
            "used_episodes": [],
            "last_updated": ""
        }

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {}

    data.setdefault("total_count", 0)
    data.setdefault("expressions", [])
    data.setdefault("daily_uid_counter", {})
    data.setdefault("used_episodes", [])
    data.setdefault("last_updated", "")

    return data

def save_index(filepath, index_data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    import datetime
    index_data["last_updated"] = datetime.datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

def normalize_expression(expr):
    if not expr:
        return ""
    # Strip whitespace and lowercase (for pinyin/comparison uniformity)
    return expr.strip().lower()

def is_duplicate(expr, index_data, threshold=0.85):
    normalized = normalize_expression(expr)
    existing = index_data.get("expressions", [])

    if not normalized:
        return True

    # Exact match
    if normalized in existing:
        return True

    # Fuzzy match
    for existing_expr in existing:
        ratio = SequenceMatcher(None, normalized, existing_expr).ratio()
        if ratio >= threshold:
            return True

    return False

def add_expression(expr, index_data):
    normalized = normalize_expression(expr)
    index_data["expressions"].append(normalized)
    index_data["total_count"] = len(index_data["expressions"])
    return normalized

def get_total_count(index_data):
    return index_data.get("total_count", 0)

def get_next_uid(index_data, date_str):
    counters = index_data.setdefault("daily_uid_counter", {})
    current = counters.get(date_str, 0)
    next_uid = current + 1
    counters[date_str] = next_uid
    return next_uid
