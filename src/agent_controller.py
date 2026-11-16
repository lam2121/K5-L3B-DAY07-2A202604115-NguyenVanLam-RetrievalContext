"""Controller implementation connecting a real LLM via OpenRouter with rate-limit retry and fallback."""
import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Any


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
- Every citation ID in 'citations' MUST match an exact chunk ID present in the provided context and MUST appear as [chunk-id] inside 'answer'.
- Output ONLY valid JSON, with no markdown code fences or conversational text outside the JSON.
"""


def extract_json(content: str) -> dict[str, Any]:
    """Robustly extract and parse a JSON object, stripping markdown code fences or surrounding text."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    # Find outermost JSON object if wrapped in text
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if m:
        content = m.group(0)
    return json.loads(content)


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
        # If no history yet, initiate search with the original question
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
                "max_tokens": 500,
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
                            return parsed

                except urllib.error.HTTPError as e:
                    # Handle Rate Limit (429) or transient server errors (500, 502, 503, 504)
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
