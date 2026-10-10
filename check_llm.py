"""Quick check that the LLM backend works. Run from this folder:

    python check_llm.py

Prints the active configuration, lists the Gemini models your project can use
(Vertex only), and sends one tiny prompt to each configured model.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proposal import llm  # noqa: E402

print("backend         :", llm.backend())
print("project         :", os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("DOCAI_PROJECT_ID"))
print("vertex location :", os.getenv("VERTEX_LOCATION") or "global")
print("fast model      :", llm.fast_model())
print("decision model  :", llm.decision_model())

try:
    names = sorted(m.name for m in llm.client().models.list() if "gemini" in (m.name or "").lower())
    print(f"\n{len(names)} Gemini models visible, for example:")
    for n in names[:25]:
        print("  ", n)
except Exception as e:
    print("\nCould not list models:", e)

for label, model in (("fast", llm.fast_model()), ("decision", llm.decision_model())):
    try:
        out = llm.generate("Reply with exactly: OK", model=model, temperature=0)
        print(f"\n[{label}] {model}: {out.strip()[:60]!r}  -> works")
    except Exception as e:
        print(f"\n[{label}] {model}: FAILED -> {e}")
