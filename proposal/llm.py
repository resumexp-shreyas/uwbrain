"""Single place that talks to Gemini.

Two backends, chosen by LLM_BACKEND in .env:
  vertex  (default)  Gemini on Vertex AI. Auth is Application Default Credentials
                     (gcloud auth application-default login), no API key.
  api                Gemini Developer API with GEMINI_API_KEY (fallback / local testing).

Uses the supported `google-genai` SDK (the old `google-generativeai` package is deprecated).
"""
import os

from google import genai
from google.genai import errors, types

_client = None


class LLMError(Exception):
    pass


def backend() -> str:
    return (os.getenv("LLM_BACKEND") or "vertex").strip().lower()


def fast_model() -> str:
    """Used for the two applicant-facing checks (ambiguity, discrepancy)."""
    return (os.getenv("LLM_MODEL_FAST") or "gemini-3.5-flash-lite").strip()


def decision_model() -> str:
    """Used for decisions, follow-up review and records mapping."""
    return (os.getenv("LLM_MODEL_DECISION") or "gemini-3.5-flash").strip()


def client() -> genai.Client:
    global _client
    if _client is None:
        if backend() == "vertex":
            project = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("DOCAI_PROJECT_ID") or "").strip().strip("'\"")
            if not project:
                raise LLMError("Vertex AI needs GOOGLE_CLOUD_PROJECT in .env.")
            location = (os.getenv("VERTEX_LOCATION") or "global").strip()
            _client = genai.Client(vertexai=True, project=project, location=location)
        else:
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                raise LLMError("LLM_BACKEND=api needs GEMINI_API_KEY in .env.")
            _client = genai.Client(api_key=key)
    return _client


def _price_per_million(model: str):
    """(input, output) USD per 1M tokens, or None when not configured.

    Set LLM_PRICE_FAST / LLM_PRICE_DECISION in .env as "input,output" (e.g. "0.10,0.40")
    from the Vertex AI / Gemini pricing page for the models you use. Not hard-coded
    because prices change and differ per model."""
    var = "LLM_PRICE_FAST" if model == fast_model() else "LLM_PRICE_DECISION" if model == decision_model() else None
    raw = os.getenv(var, "") if var else ""
    try:
        inp, out = (float(x) for x in raw.split(","))
        return inp, out
    except ValueError:
        return None


def _usage(response, model: str, label: str) -> dict:
    u = response.usage_metadata
    prompt = (u.prompt_token_count or 0) if u else 0
    candidates = (u.candidates_token_count or 0) if u else 0
    thoughts = (u.thoughts_token_count or 0) if u else 0
    out = candidates + thoughts  # thinking tokens are billed as output
    price = _price_per_million(model)
    cost = round((prompt * price[0] + out * price[1]) / 1_000_000, 6) if price else None
    return {
        "call": label,
        "model": model,
        "input_tokens": prompt,
        "output_tokens": out,
        "thinking_tokens": thoughts,
        "total_tokens": (u.total_token_count or prompt + out) if u else 0,
        "estimated_cost_usd": cost,
    }


def docai_usage(pages: int) -> dict:
    """Usage entry for Document AI OCR, billed per page (DOCAI_PRICE_PER_1000_PAGES, USD)."""
    try:
        per_1000 = float(os.getenv("DOCAI_PRICE_PER_1000_PAGES", ""))
    except ValueError:
        per_1000 = None
    return {
        "call": "Document AI OCR",
        "model": "Enterprise Document OCR",
        "pages": pages,
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": round(pages * per_1000 / 1000, 6) if per_1000 is not None else None,
    }


def generate(prompt: str, *, model: str, temperature: float = 0.3, json_mode: bool = False) -> str:
    return generate_with_usage(prompt, model=model, temperature=temperature, json_mode=json_mode)[0]


def generate_with_usage(prompt: str, *, model: str, temperature: float = 0.3, json_mode: bool = False,
                        label: str = "") -> tuple[str, dict]:
    """Like generate(), but also returns token counts and estimated cost for the call."""
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if json_mode else None,
    )
    response = client().models.generate_content(model=model, contents=prompt, config=config)
    text = response.text
    if not text:
        reason = None
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            reason = response.prompt_feedback.block_reason
        elif response.candidates:
            reason = response.candidates[0].finish_reason
        raise LLMError(f"Model did not return any text. Reason: {reason}.")
    return text, _usage(response, model, label)


def status_for(exc: Exception) -> int:
    """HTTP status to send back for a failed model call."""
    if isinstance(exc, errors.APIError):
        return 429 if exc.code == 429 else 502
    return 500
