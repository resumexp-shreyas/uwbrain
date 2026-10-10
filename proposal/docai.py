"""Google Cloud Document AI wrapper: medical record file -> plain text.

Uses a layout-agnostic processor (Enterprise Document OCR recommended) so that
discharge summaries, lab/investigation reports and consultation notes all come
back as text. Mapping that text onto the questionnaire is done separately
(see records.py), because the questionnaire is our own schema.

Auth is Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS pointing
at a service-account JSON with the "Document AI API User" role, or
`gcloud auth application-default login` in dev). This is separate from the
Gemini API key.
"""
import os

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_FILE_BYTES = 20 * 1024 * 1024  # Document AI online processing limit


class DocAINotConfigured(Exception):
    pass


class DocAIError(Exception):
    pass


def _processor_name(client):
    project = (os.getenv("DOCAI_PROJECT_ID") or "").strip().strip("'\"")
    location = (os.getenv("DOCAI_LOCATION") or "us").strip()
    processor = (os.getenv("DOCAI_PROCESSOR_ID") or "").strip()
    if not project or not processor:
        raise DocAINotConfigured(
            "Document AI is not configured. Set DOCAI_PROJECT_ID, DOCAI_LOCATION "
            "and DOCAI_PROCESSOR_ID in .env."
        )
    return client.processor_path(project, location, processor)


def extract_text(content: bytes, mime_type: str) -> tuple[str, int]:
    """Returns (text, page_count) for one document."""
    # Imported lazily so the rest of the API still works without the package.
    try:
        from google.api_core.client_options import ClientOptions
        from google.cloud import documentai
    except ImportError as e:
        raise DocAINotConfigured(
            "google-cloud-documentai is not installed (pip install -r requirements.txt)."
        ) from e

    location = (os.getenv("DOCAI_LOCATION") or "us").strip()
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    )
    name = _processor_name(client)

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=content, mime_type=mime_type),
    )
    try:
        result = client.process_document(request=request)
    except Exception as e:  # google.api_core exceptions carry useful messages
        raise DocAIError(str(e)) from e

    document = result.document
    return document.text or "", len(document.pages)
