"""
EXAMIX AI - AI provider module with robust retries and a forceful mixing prompt.
"""

import os
import json
import re
import requests
import logging
import time
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5


class AIProviderError(Exception):
    pass


def _get_provider_config():
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise AIProviderError("DEEPSEEK_API_KEY is not set")
        return {
            "url": DEEPSEEK_URL,
            "api_key": api_key,
            "model": "deepseek-chat",
            "max_output_tokens": 4096,
        }
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY is not set")
        return {
            "url": OPENAI_URL,
            "api_key": api_key,
            "model": "gpt-4o-mini",
            "max_output_tokens": 16384,
        }
    else:
        raise AIProviderError(f"Unknown provider: {provider}")


def _call_chat_api(system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.4) -> str:
    config = _get_provider_config()
    max_tokens = min(max_tokens, config["max_output_tokens"])

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(config["url"], headers=headers, json=payload, timeout=45)
    except requests.exceptions.RequestException as e:
        raise AIProviderError(f"Network error: {e}")

    if resp.status_code != 200:
        raise AIProviderError(f"API error {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise AIProviderError(f"Malformed response: {e}")


def _repair_truncated_json(candidate: str) -> str:
    open_brackets = candidate.count('[') + candidate.count('{')
    close_brackets = candidate.count(']') + candidate.count('}')
    if open_brackets > close_brackets:
        stack = []
        for ch in candidate:
            if ch in '[{':
                stack.append(ch)
            elif ch in ']}':
                if stack and ((ch == ']' and stack[-1] == '[') or (ch == '}' and stack[-1] == '{')):
                    stack.pop()
        missing = ''.join('}' if s == '{' else ']' for s in reversed(stack))
        return candidate + missing
    return candidate


def _extract_json(raw_text: str) -> Any:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    array_match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    obj_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    candidate = None
    if array_match:
        candidate = array_match.group(1)
    elif obj_match:
        candidate = obj_match.group(1)
    else:
        raise AIProviderError("No JSON array or object found.")

    candidate = _repair_truncated_json(candidate)

    def try_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    result = try_parse(candidate)
    if result is not None:
        return result

    fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
    result = try_parse(fixed)
    if result is not None:
        return result

    try:
        return json.loads(fixed, strict=False)
    except json.JSONDecodeError:
        pass

    try:
        import ast
        py_str = fixed.replace("null", "None").replace("true", "True").replace("false", "False")
        parsed = ast.literal_eval(py_str)
        return parsed
    except Exception:
        pass

    # Partial salvage
    logger.warning("All JSON parsing failed; attempting to salvage partial data.")
    parts = fixed.split('}')
    for i in range(len(parts), 0, -1):
        test = '}'.join(parts[:i]) + ']'
        try:
            parsed = json.loads(test)
            if isinstance(parsed, list) and len(parsed) > 0:
                logger.info(f"Salvaged {len(parsed)} questions from partial response.")
                return parsed
        except:
            continue

    raise AIProviderError("Could not extract valid JSON from AI response.")


def _generate_with_retry(system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return _call_chat_api(system_prompt, user_prompt, max_tokens, temperature)
        except AIProviderError as e:
            last_error = e
            wait = BACKOFF_FACTOR ** attempt
            logger.warning(f"API call failed (attempt {attempt+1}): {e}. Retrying in {wait:.1f}s")
            time.sleep(wait)
    raise AIProviderError(f"All API retries failed: {last_error}")


def identify_concepts(paper_text: str, allowed_concepts):
    concept_list_str = "\n".join(f"- {c}" for c in allowed_concepts)
    system_prompt = (
        "You are a CBSE Class 9 Mathematics expert. You read a question paper's "
        "text and identify which of the following official CBSE Class 9 Maths "
        f"syllabus concepts it covers:\n{concept_list_str}\n\n"
        "Respond with ONLY a JSON array of concept name strings, copied EXACTLY "
        "from the list above. Return between 1 and 6 concepts."
    )
    user_prompt = f"Question paper text:\n\n{paper_text}\n\nWhich concepts?"

    raw = _generate_with_retry(system_prompt, user_prompt, max_tokens=300, temperature=0.4)
    parsed = _extract_json(raw)

    if not isinstance(parsed, list) or not all(isinstance(c, str) for c in parsed):
        raise AIProviderError("Invalid concept list returned.")

    allowed_set = set(allowed_concepts)
    matched = [c for c in parsed if c in allowed_set]
    if not matched:
        raise AIProviderError("No recognizable syllabus concepts found.")
    return matched


def _generate_batch(concepts: List[str], question_type: str, batch_size: int) -> List[Dict]:
    """Generate a single batch with a VERY forceful prompt."""
    type_instruction = {
        "MCQ": "All questions must be Multiple Choice Questions with 4 options.",
        "Short Answer": "All questions must be Short Answer questions (no options).",
        "Long Answer": "All questions must be Long Answer questions requiring multi-step working.",
        "Mixed": "Use a mix of MCQ, Short Answer, and Long Answer questions, roughly evenly.",
    }.get(question_type, "Mixed")

    # Build a list of concept pairs to encourage mixing – we give examples
    concept_pairs = []
    for i in range(len(concepts)):
        for j in range(i+1, len(concepts)):
            concept_pairs.append((concepts[i], concepts[j]))

    examples = ""
    if concept_pairs:
        pair = concept_pairs[0]  # just an example
        examples = f"For example, you could combine '{pair[0]}' and '{pair[1]}' in a question like: 'A linear equation in two variables is used to model the volume of a cylinder. ...'"

    system_prompt = (
        "You are a CBSE Class 9 Mathematics teacher creating a NEW practice paper. "
        "You MUST write questions that genuinely combine AT LEAST TWO concepts from the given list in EACH question. "
        "Do not produce questions that use only one concept. "
        "For each question, list the concepts used in 'concepts_used' – it must have at least two distinct concepts. "
        f"{examples}\n"
        f"{type_instruction}\n"
        "For every question, provide the correct answer, a concise step-by-step solution (under 150 characters), "
        "and the list of concepts used. "
        "Respond with ONLY a valid JSON array, no extra text. "
        "Use this exact format: "
        '[{"type": "mcq|short|long", "question": "...", "options": ["A","B","C","D"] or null, '
        '"answer": "...", "solution": "...", "concepts_used": ["..."]}]'
    )
    user_prompt = (
        f"Concepts to mix: {', '.join(concepts)}\n"
        f"Generate exactly {batch_size} questions.\n"
        f"Question type: {question_type}\n"
        "Output the JSON array now."
    )

    config = _get_provider_config()
    max_tokens = min(4000, config["max_output_tokens"] - 200)

    raw = _generate_with_retry(system_prompt, user_prompt, max_tokens, temperature=0.9)  # higher temperature for creativity
    parsed = _extract_json(raw)

    if not isinstance(parsed, list):
        raise AIProviderError("Batch did not return a list.")

    concept_set = set(concepts)
    for idx, q in enumerate(parsed):
        used = q.get("concepts_used", [])
        if not isinstance(used, list) or len(set(used) & concept_set) < 2:
            raise AIProviderError(f"Question {idx+1} does not combine at least two concepts.")

    return parsed


def generate_questions(concepts: List[str], question_type: str, num_questions: int) -> List[Dict]:
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    BATCH_SIZE = 3 if provider == "deepseek" else 8

    all_questions = []
    remaining = num_questions

    while remaining > 0:
        batch_size = min(BATCH_SIZE, remaining)
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                batch = _generate_batch(concepts, question_type, batch_size)
                all_questions.extend(batch)
                remaining -= len(batch)
                success = True
                break
            except AIProviderError as e:
                logger.warning(f"Batch of {batch_size} failed (attempt {attempt+1}): {e}")
                if batch_size > 2:
                    batch_size = max(2, batch_size // 2)
                else:
                    # Try single question
                    try:
                        single = _generate_batch(concepts, question_type, 1)
                        all_questions.extend(single)
                        remaining -= 1
                        success = True
                        break
                    except:
                        pass
                time.sleep(BACKOFF_FACTOR ** attempt)

        if not success:
            if all_questions:
                logger.warning(f"Partial generation: returning {len(all_questions)} out of {num_questions} questions.")
                return all_questions
            raise AIProviderError("Failed to generate any questions after multiple retries.")

    return all_questions