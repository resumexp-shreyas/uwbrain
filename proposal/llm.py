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


def generate(prompt: str, *, model: str, temperature: float = 0.3, json_mode: bool = False) -> str:
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
    return text


def status_for(exc: Exception) -> int:
    """HTTP status to send back for a failed model call."""
    if isinstance(exc, errors.APIError):
        return 429 if exc.code == 429 else 502
    return 500
