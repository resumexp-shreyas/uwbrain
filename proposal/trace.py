"""Readable, consistently named console log for every model call.

Each call writes one REQUEST block and one RESPONSE block, tied together by a short id:

 08:21:02  >>> REQUEST   a3f9  Ambiguity check      POST /proposal/findambiguity/
              applicant     : 32 / Male
              lifestyle     : tobacco Yes (Chew) | alcohol No
              Q3 conditions : Asthma (2018, I'm taking treatment or medicine)
 08:21:03  <<< RESPONSE  a3f9  Ambiguity check      200 OK | 1.4 s | gemini-3.5-flash-lite | in 1,820 / out 210 tokens | $0.00031
              vague terms   : none

Applicant details are health data. They are shown when DEBUG is on, or when
LOG_APPLICANT_DETAIL=true. Otherwise (for example on Cloud Run) only the
call name, timing, token counts and the decision are logged.
"""
import logging
import os
import time
import uuid

from django.conf import settings

log = logging.getLogger("uwbrain.trace")

PAD = " " * 14  # continuation lines line up under the label column


def _show_detail() -> bool:
    return settings.DEBUG or os.getenv("LOG_APPLICANT_DETAIL", "").strip().lower() in ("1", "true", "yes")


def _clip(text, n=220):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "..."


def _field(name, value):
    return f"{PAD}{name:<14}: {value}"


# --------------------------------------------------------------------------- applicant summary
field = _field  # public alias used by the views


def applicant_lines(data) -> list[str]:
    """One tidy line per questionnaire section, from the front end's proposal object."""
    if not isinstance(data, dict):
        return [_field("payload", _clip(data))]
    out = [_field("applicant", f"{data.get('age', '?')} / {data.get('gender', '?')}")]
    try:
        life = data.get("lifestyle") or []
        parts = []
        for name, item in zip(("tobacco", "alcohol"), life):
            ans = item.get("answer", "?")
            forms = (item.get("details") or {}).get("Tobacco form(s)") if isinstance(item.get("details"), dict) else None
            parts.append(f"{name} {ans}" + (f" ({forms})" if forms else ""))
        if parts:
            out.append(_field("lifestyle", " | ".join(parts)))

        answers = data.get("answers") or []
        get = lambda i: answers[i] if i < len(answers) and isinstance(answers[i], dict) else {}

        q3 = get(0)
        if q3.get("answer") == "Yes" and isinstance(q3.get("details"), dict):
            d = q3["details"]
            names = [c for c in str(d.get("Medical condition", "")).split("||") if c]
            years = dict(p.split(": ", 1) for p in str(d.get("Year Of diagnosis", "")).split("; ") if ": " in p)
            status = dict(p.split(": ", 1) for p in str(d.get("Current Status", "")).split("; ") if ": " in p)
            out.append(_field("Q3 conditions", "; ".join(f"{n} ({years.get(n, '?')}, {status.get(n, '?')})" for n in names) or "Yes"))
        else:
            out.append(_field("Q3 conditions", q3.get("answer", "?")))

        q4 = get(1)
        if q4.get("answer") == "Yes" and isinstance(q4.get("details"), dict):
            d = q4["details"]
            out.append(_field("Q4 hospital", _clip(
                f"{d.get('Type of hospitalization', '?')} | {d.get('Reason(s) for hospitalization/surgery', '?')} | "
                f"{d.get('Time since hospitalization/surgery', '?')} | {d.get('Outcome', '?')} | "
                f"records available: {d.get('Has discharge records', '?')}, uploaded: {d.get('Past medical records uploaded', '?')}", 200)))
        else:
            out.append(_field("Q4 hospital", q4.get("answer", "?")))

        q5 = get(2)
        out.append(_field("Q5 medicines", _clip(q5.get("details"), 120) if q5.get("answer") == "Yes" else q5.get("answer", "?")))

        q6, q7 = get(3), get(4)
        d6 = q6.get("details") if q6.get("answer") == "Yes" else None
        out.append(_field("Q6 / Q7", f"disability: {q6.get('answer', '?')}{' ' + str(d6) if d6 else ''} | "
                                      f"past insurance: {q7.get('answer', '?')}{' (' + _clip(q7.get('details'), 60) + ')' if q7.get('answer') == 'Yes' else ''}"))
    except Exception:  # never let logging break a request
        out.append(_field("raw", _clip(data, 300)))
    return out


# --------------------------------------------------------------------------- result summaries
def ambiguity_result(r) -> list[str]:
    items = r.get("ambiguous_conditions_to_clarify") or []
    if not items:
        return [_field("vague terms", "none")]
    return [_field("vague terms", "; ".join(f"{i.get('disclosed_term')} -> {', '.join((i.get('probable_options') or [])[:4])}" for i in items))]


def discrepancy_result(r) -> list[str]:
    items = r.get("discrepancies_detected") or []
    if not items:
        return [_field("discrepancies", "none")]
    return [_field("discrepancies", f"{len(items)}")] + [f"{PAD}{'':<14}  - {_clip(i.get('clarification_question') or i, 160)}" for i in items]


def decision_result(r) -> list[str]:
    out = [_field("decision", r.get("underwriting_decision", "?"))]
    ld = r.get("loading_details") or {}
    if ld.get("applicable"):
        out.append(_field("loading", f"{ld.get('total_loading_percentage')}%  ("
                                      + ", ".join(f"{c.get('condition')} {c.get('loading_percentage')}%" for c in ld.get("loading_conditions", [])) + ")"))
    wp = r.get("waiting_period_details") or []
    if wp:
        out.append(_field("waiting period", ", ".join(f"{w.get('condition')} [{w.get('icd_category_code')}]" for w in wp)))
    ref = r.get("refer_to_uwr_details")
    if ref:
        out.append(_field("referral", f"{ref.get('reason')} | {len(ref.get('suggested_questions') or [])} questions, "
                                      f"{len(ref.get('requested_medical_records') or [])} records, {len(ref.get('suggested_medical_checkups') or [])} checkups"))
    more = r.get("more_questions_details") or []
    if more:
        out.append(_field("asks", f"{len(more)} follow-up question(s)"))
    out.append(_field("rationale", _clip(r.get("decision_rationale"), 240)))
    return out


def records_result(prefill) -> list[str]:
    conds = [c.get("condition") for c in prefill.get("medicalConditions", [])]
    h = prefill.get("hospitalization")
    out = [_field("documents", "; ".join(f"{d.get('document_type')} ({d.get('file_name')})" for d in prefill.get("documents", [])) or "none"),
           _field("pre-filled", f"age {prefill.get('age')}, {prefill.get('gender')} | conditions: {', '.join(conds) or 'none'} | "
                                f"hospitalization: {'yes' if h else 'no'}")]
    if prefill.get("warnings"):
        out.append(_field("warnings", _clip("; ".join(prefill["warnings"]), 200)))
    return out


# --------------------------------------------------------------------------- the trace itself
def _usage_text(usage) -> str:
    items = usage if isinstance(usage, list) else ([usage] if usage else [])
    bits = []
    for u in items:
        if not isinstance(u, dict):
            continue
        cost = u.get("estimated_cost_usd")
        cost_txt = f" ${cost:.5f}" if isinstance(cost, (int, float)) else ""
        if u.get("pages"):
            bits.append(f"{u.get('call', 'OCR')}: {u['pages']} page(s){cost_txt}")
        elif u.get("total_tokens"):
            bits.append(f"{u.get('model', 'model')} | in {u['input_tokens']:,} / out {u['output_tokens']:,} tokens{cost_txt}")
    return " | ".join(bits)


class Trace:
    def __init__(self, label: str, request, lines: list[str] | None = None):
        self.id = uuid.uuid4().hex[:4]
        self.label = label
        self.t0 = time.perf_counter()
        head = f">>> REQUEST   {self.id}  {label:<22} {request.method} {request.path}"
        body = lines if (lines and _show_detail()) else []
        log.info("\n".join([head] + body))

    def _elapsed(self) -> str:
        return f"{time.perf_counter() - self.t0:.1f} s"

    def ok(self, result_lines: list[str] | None = None, usage=None, status: int = 200):
        head = f"<<< RESPONSE  {self.id}  {self.label:<22} {status} OK | {self._elapsed()}"
        extra = _usage_text(usage)
        if extra:
            head += f" | {extra}"
        log.info("\n".join([head] + (result_lines or [])))

    def fail(self, error, status: int = 500):
        log.error(f"!!! ERROR     {self.id}  {self.label:<22} {status} | {self._elapsed()}\n{_field('reason', _clip(error, 400))}")


def start(label: str, request, lines: list[str] | None = None) -> Trace:
    return Trace(label, request, lines)
