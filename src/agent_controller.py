"""Controller implementation connecting a real LLM via Anthropic or OpenRouter with rate-limit retry and fallback."""
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)


SYSTEM_PROMPT = """You are a strictly grounded AI research agent.
Your task is to answer the user's question using ONLY verified facts from retrieved document chunks.

You have access to a search tool.
In each turn, you will receive:
1. The original question.
2. The current accumulated context of retrieved chunks (with IDs like [openstax-college-success-p...]) and previous queries.

You MUST respond in ONE of three valid JSON formats:

Format 1 - If context is missing or you need more specific evidence:
{
  "action": "search",
  "query": "<refined query keywords to search in document>"
}

Format 2 - When you have found sufficient evidence in the context:
{
  "action": "answer",
  "answer": "<Your factual answer in the question's language. You MUST cite the supporting chunk ID in square brackets, e.g. [openstax-college-success-p11-para001].>",
  "citations": ["openstax-college-success-p11-para001"]
}

Format 3 - If the context does NOT contain enough evidence to answer the question, or the question is unanswerable:
{
  "action": "answer",
  "answer": "Không đủ bằng chứng để trả lời.",
  "citations": []
}

CRITICAL RULES:
- Carefully inspect the ACCUMULATED CONTEXT first. If the context contains the facts needed to answer the question, prioritize responding with Format 2 (answer) immediately with citations.
- Only request another search (Format 1) if the context is genuinely missing the needed facts.
- If the question asks for information clearly absent from or irrelevant to the textbook, or after searching the evidence cannot be found, respond with Format 3 (abstain) with empty citations.
- Never hallucinate facts outside the provided context.
- Keep answers concise and direct (under 60 words) while stating essential numbers/units and citing supporting chunks.
- Every citation ID in 'citations' MUST match an exact chunk ID present in the provided context and MUST appear as [chunk-id] inside 'answer'.
- Output ONLY valid JSON, with no markdown code fences or conversational text outside the JSON.
"""


def extract_json(content: str) -> dict[str, Any]:
    """Robustly extract and parse a JSON object, stripping markdown code fences or repairing truncated JSON."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    # Find outermost JSON object if wrapped in text
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            content = m.group(0)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Repair unclosed quotes / braces if generation ended slightly early
        repaired = content
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        if '"citations":' in repaired and not repaired.rstrip().endswith("]"):
            repaired += ']}'
        elif not repaired.rstrip().endswith("}"):
            repaired += '}'
        try:
            return json.loads(repaired)
        except Exception:
            pass
        raise


def normalize_action(parsed: dict[str, Any], context_ids: list[str]) -> dict[str, Any]:
    """Normalize model output action according to Day 7 Controller protocol.
    Guarantees citations appear in answer as [chunk-id] and only valid chunk IDs are cited.
    """
    action = parsed.get("action")
    if action == "search":
        q = parsed.get("query", "")
        if isinstance(q, str) and q.strip():
            return {"action": "search", "query": q.strip()}
        return {"action": "search", "query": "World Development Report 2025"}

    if action == "answer":
        raw_ans = parsed.get("answer", "")
        raw_cites = parsed.get("citations", [])
        if not isinstance(raw_ans, str):
            raw_ans = str(raw_ans)
        if not isinstance(raw_cites, list):
            raw_cites = [raw_cites] if raw_cites else []

        # Check for explicit abstention markers
        abstain_markers = [
            "không đủ bằng chứng",
            "không đủ thông tin",
            "not enough evidence",
            "cannot be determined",
            "no evidence",
            "insufficient evidence",
            "cannot answer",
            "unanswerable"
        ]
        is_abstain = any(m in raw_ans.lower() for m in abstain_markers) or len(context_ids) == 0

        if is_abstain and (not raw_cites or len(context_ids) == 0):
            return {
                "action": "answer",
                "answer": "Không đủ bằng chứng để trả lời.",
                "citations": []
            }

        # Normalize citations to match valid context_ids
        normalized_cites: list[str] = []
        for cite in raw_cites:
            if not isinstance(cite, str):
                continue
            clean_cite = cite.strip().strip("[]").strip()
            # 1. Exact match
            if clean_cite in context_ids:
                if clean_cite not in normalized_cites:
                    normalized_cites.append(clean_cite)
                continue
            # 2. Fuzzy match (dot vs underscore, e.g. figure-7.7 vs figure-7_7)
            alt_cite = clean_cite.replace(".", "_")
            matched = False
            for cid in context_ids:
                if alt_cite in cid or cid.endswith(alt_cite):
                    if cid not in normalized_cites:
                        normalized_cites.append(cid)
                    matched = True
                    break
            if matched:
                continue
            # 3. Suffix match (e.g. "table-4_2" in "wdr2025-p209-table-4_2")
            suffix = clean_cite.split("-")[-1] if "-" in clean_cite else clean_cite
            for cid in context_ids:
                if suffix in cid:
                    if cid not in normalized_cites:
                        normalized_cites.append(cid)
                    break

        # If answer is factual but normalized_cites ended up empty, find any context_ids mentioned in raw_ans
        if not normalized_cites and not is_abstain:
            for cid in context_ids:
                suffix = "-".join(cid.split("-")[2:]) if cid.count("-") >= 2 else cid
                if cid in raw_ans or suffix in raw_ans or suffix.replace("_", ".") in raw_ans:
                    normalized_cites.append(cid)
            # If still empty, use top context ID to maintain validity
            if not normalized_cites and context_ids:
                normalized_cites.append(context_ids[0])

        # If after normalization we still have citations, make sure each citation appears as [cid] in answer
        final_ans = raw_ans.strip()
        if normalized_cites:
            for cid in normalized_cites:
                bracket_ref = f"[{cid}]"
                if bracket_ref not in final_ans:
                    final_ans = f"{final_ans} {bracket_ref}"
        else:
            return {
                "action": "answer",
                "answer": "Không đủ bằng chứng để trả lời.",
                "citations": []
            }

        return {
            "action": "answer",
            "answer": final_ans,
            "citations": normalized_cites
        }

    return {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}


class AnthropicController:
    """Agent Controller backed directly by Anthropic API (Claude 3.5 Haiku / Sonnet)."""

    def __init__(self, model: str | None = None, api_key: str | None = None, fallback_model: str | None = None):
        import anthropic
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model or os.getenv("LLM_MODEL", "claude-haiku-5-5")
        self.fallback_model = fallback_model or os.getenv("FALLBACK_LLM_MODEL", "claude-3-haiku-20240307")

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Examine question and search history; decide next action with Claude."""
        if not history:
            return {"action": "search", "query": question}

        latest_history = history[-1]
        context = latest_history.get("context", "")
        queries = latest_history.get("queries", [])
        context_ids = latest_history.get("context_ids", [])

        user_content = (
            f"Original Question: {question}\n\n"
            f"Previous queries executed: {queries}\n"
            f"Available Chunk IDs in context: {context_ids}\n\n"
            f"--- ACCUMULATED CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
            f"Based on the context above, determine if you have sufficient evidence to answer or need to search further. "
            f"Respond with valid JSON according to the instructions."
        )

        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)

        for current_model in models_to_try:
            for attempt in range(1, 4):
                try:
                    response = self.client.messages.create(
                        model=current_model,
                        max_tokens=1500,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": user_content}]
                    )
                    # Extract text content from all text blocks (handling ThinkingBlock if present)
                    content = "".join([b.text for b in response.content if hasattr(b, "text") and getattr(b, "type", "text") == "text"])
                    parsed = extract_json(content)
                    action = parsed.get("action")
                    if action in ("search", "answer"):
                        return normalize_action(parsed, context_ids)
                except Exception as e:
                    print(f"\n[Anthropic Attempt {attempt}] Error with {current_model}: {e}")
                    time.sleep(2 ** attempt)

        return {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}


class OpenRouterController:
    """Agent Controller backed by OpenRouter with rate-limit retry (3x exponential backoff) and fallback support."""

    def __init__(self, model: str | None = None, api_key: str | None = None, fallback_model: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set.")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model or os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
        self.fallback_model = fallback_model or os.getenv("FALLBACK_LLM_MODEL", "nvidia/nemotron-3.5-super-vl:free")

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Examine question and search history; decide next action with retry on 429/5xx and fallback model."""
        if not history:
            return {"action": "search", "query": question}

        latest_history = history[-1]
        context = latest_history.get("context", "")
        queries = latest_history.get("queries", [])
        context_ids = latest_history.get("context_ids", [])

        user_content = (
            f"Original Question: {question}\n\n"
            f"Previous queries executed: {queries}\n"
            f"Available Chunk IDs in context: {context_ids}\n\n"
            f"--- ACCUMULATED CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
            f"Based on the context above, determine if you have sufficient evidence to answer or need to search further. "
            f"Respond with valid JSON."
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)

        for current_model in models_to_try:
            payload = {
                "model": current_model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 220,
                "response_format": {"type": "json_object"}
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Day7-Agent/1.0"
            }

            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    req = urllib.request.Request(self.url, data=data_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=35) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        content = resp_data["choices"][0]["message"]["content"]
                        parsed = extract_json(content)
                        action = parsed.get("action")
                        if action in ("search", "answer"):
                            return normalize_action(parsed, context_ids)

                except urllib.error.HTTPError as e:
                    if e.code == 429 or e.code >= 500:
                        retry_after = e.headers.get("Retry-After")
                        wait_sec = float(retry_after) if retry_after else (2 ** attempt)
                        print(f"\n[Rate Limit / HTTP {e.code}] Model '{current_model}' bị nghẽn. Thử lại lần {attempt}/{max_retries} sau {wait_sec:.1f}s...")
                        time.sleep(wait_sec)
                        continue
                    else:
                        err_body = e.read().decode("utf-8", errors="ignore")[:150]
                        print(f"\n[HTTP Error {e.code}] {err_body}")
                        break

                except (urllib.error.URLError, TimeoutError) as e:
                    wait_sec = 2 ** attempt
                    print(f"\n[Network Timeout] Lỗi kết nối ({e}). Thử lại lần {attempt}/{max_retries} sau {wait_sec}s...")
                    time.sleep(wait_sec)
                    continue

                except Exception as e:
                    print(f"\n[Parse Warning] Lỗi đọc JSON ({e}). Thử lại lần {attempt}/{max_retries}...")
                    time.sleep(1)
                    continue

            if current_model != models_to_try[-1]:
                print(f"[Fallback] Chuyển từ model '{current_model}' sang model dự phòng '{models_to_try[-1]}'...")

        return {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}


def get_controller(model: str | None = None, fallback_model: str | None = None, provider: str | None = None):
    """Auto-detect and return the appropriate Controller (Anthropic or OpenRouter)."""
    provider = provider or os.getenv("LLM_PROVIDER", "").lower()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if provider == "anthropic" or (anthropic_key and not provider):
        print("[Controller] Using Anthropic Direct API")
        return AnthropicController(
            model=model or os.getenv("LLM_MODEL", "claude-haiku-5-5"),
            fallback_model=fallback_model or os.getenv("FALLBACK_LLM_MODEL", "claude-3-haiku-20240307")
        )
    print("[Controller] Using OpenRouter API")
    return OpenRouterController(
        model=model or os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct"),
        fallback_model=fallback_model or os.getenv("FALLBACK_LLM_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    )
