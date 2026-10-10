"""Turns the model's raw extraction from medical records into a validated,
frontend-ready prefill for the proposal form.

The model is only trusted for *what the documents say*. Everything the form
needs to be strictly valid (allowed option strings, time-since arithmetic,
the 4-year hospitalization window) is enforced here, not in the prompt.
"""
from datetime import date

STATUS_OPTIONS = {
    "I'm completely fine now",
    "I'm taking treatment or medicine",
    "Doctor is keeping a watch",
    "It's under control but not cured",
    "It comes and goes",
    "I have a surgery planned",
    "I'm recovering from surgery",
    "Waiting for test results",
    "It's serious and ongoing",
}

REASON_OPTIONS = {
    "Accident or injury", "Appendicitis / appendectomy", "Childbirth / delivery",
    "Heart problem", "Stroke or neurological event", "Respiratory infection",
    "Severe infection", "Gastrointestinal illness", "Abdominal surgery",
    "Kidney problem", "Liver problem", "Diabetes complication",
    "Cancer treatment or complication", "Planned elective surgery",
    "Emergency surgery", "Mental health admission", "Observation for chest pain",
    "Post‑operative complication",
    "Diagnostic admission for tests / investigations",
    "Other, specified separately",
}

OUTCOME_OPTIONS = {
    "Fully recovered, no ongoing issues", "Recovered but with lasting effects",
    "Improved and stable with ongoing follow‑up",
    "Still under treatment / receiving medication",
    "Ongoing symptoms / not yet recovered",
    "Complication or re‑admission after discharge",
    "Permanent disability or impairment",
    "Transferred to long‑term care / rehabilitation",
    "Deceased (historical record)", "Unknown / prefer not to say",
    "Other (please specify)",
}

HOSP_TYPES = {"Past hospitalization", "Planned hospitalization"}
GENDERS = {"Male", "Female", "Other"}
TOBACCO_FORMS = {"Smoke", "Chew"}
HOSP_WINDOW_MONTHS = 48  # Q4 look-back window


def _bool(v):
    return v if isinstance(v, bool) else None


def _str(v, limit=1000):
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v[:limit] if v else None


def _parse_event_date(raw):
    """Accepts YYYY-MM-DD, YYYY-MM or YYYY. Returns a date (missing parts -> mid-range) or None."""
    raw = _str(raw, 20)
    if not raw:
        return None
    parts = raw.split("-")
    try:
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 6
        d = int(parts[2]) if len(parts) > 2 else (15 if len(parts) > 1 else 1)
        return date(y, m, d)
    except (ValueError, IndexError):
        return None


def _months_between(earlier: date, later: date) -> int:
    months = (later.year - earlier.year) * 12 + (later.month - earlier.month)
    if later.day < earlier.day:
        months -= 1
    return max(months, 0)


def _year(v):
    try:
        y = int(v)
    except (TypeError, ValueError):
        return None
    return str(y) if 1900 <= y <= date.today().year else None


def build_prefill(raw: dict, today: date | None = None) -> dict:
    today = today or date.today()
    warnings = [w for w in (_str(w, 300) for w in (raw.get("warnings") or [])) if w]

    # --- documents --------------------------------------------------------
    documents = []
    for d in raw.get("documents") or []:
        if isinstance(d, dict):
            documents.append({
                "file_name": _str(d.get("file_name"), 255),
                "document_type": _str(d.get("document_type"), 60),
                "summary": _str(d.get("summary"), 300),
            })
    types_found = {(d["document_type"] or "").lower() for d in documents}

    # --- personal ---------------------------------------------------------
    age = raw.get("age")
    age = str(age) if isinstance(age, int) and not isinstance(age, bool) and 0 <= age <= 120 else None
    gender = raw.get("gender") if raw.get("gender") in GENDERS else None

    # --- lifestyle --------------------------------------------------------
    tob = raw.get("tobacco") if isinstance(raw.get("tobacco"), dict) else {}
    forms = [f for f in (tob.get("forms") or []) if f in TOBACCO_FORMS]
    tobacco_answer = _bool(tob.get("answer"))
    if forms:
        tobacco_answer = True
    alc = raw.get("alcohol") if isinstance(raw.get("alcohol"), dict) else {}

    # --- Q3 medical history ----------------------------------------------
    conditions, seen = [], set()
    for c in raw.get("medical_conditions") or []:
        if not isinstance(c, dict):
            continue
        name = _str(c.get("condition"), 120)
        if not name or "||" in name or ";" in name or name.lower() in seen:
            continue  # "||" and ";" are the delimiters used downstream
        seen.add(name.lower())
        status = c.get("current_status")
        conditions.append({
            "condition": name,
            "yearOfDiagnosis": _year(c.get("year_of_diagnosis")),
            "currentStatus": status if status in STATUS_OPTIONS else None,
        })

    # --- Q4 hospitalization ----------------------------------------------
    h = raw.get("hospitalization") if isinstance(raw.get("hospitalization"), dict) else {}
    h_types = [t for t in (h.get("types") or []) if t in HOSP_TYPES]
    reasons = [r for r in (h.get("reasons") or []) if r in REASON_OPTIONS]
    reason_other = _str(h.get("reason_other"), 200)
    if reason_other and "Other, specified separately" not in reasons:
        reasons.append("Other, specified separately")
    outcome = h.get("outcome") if h.get("outcome") in OUTCOME_OPTIONS else None
    outcome_other = _str(h.get("outcome_other"), 200)

    hosp = None
    event = _parse_event_date(h.get("event_date"))
    years_ago = months_ago = None
    if event:
        if event > today:
            if "Planned hospitalization" not in h_types:
                h_types.append("Planned hospitalization")
            h_types = [t for t in h_types if t != "Past hospitalization"]
        else:
            age_months = _months_between(event, today)
            if age_months > HOSP_WINDOW_MONTHS and "Planned hospitalization" not in h_types:
                warnings.append(
                    f"A hospitalization dated {event.isoformat()[:7]} is older than 4 years "
                    "and was not added to Q4."
                )
                reasons, h_types, outcome, outcome_other, reason_other = [], [], None, None, None
            else:
                if "Past hospitalization" not in h_types:
                    h_types.append("Past hospitalization")
                y, m = divmod(age_months, 12)
                years_ago = "10+" if y >= 10 else str(y)
                months_ago = str(m)
    if "Past hospitalization" not in h_types:
        outcome, outcome_other = None, None  # outcome only applies to past events
    if reasons or h_types:
        hosp = {
            "types": h_types,
            "reasons": reasons,
            "reasonOther": reason_other or "",
            "yearsAgo": years_ago or "",
            "monthsAgo": months_ago or "",
            "outcome": outcome or ("Other (please specify)" if outcome_other else ""),
            "outcomeOther": outcome_other or "",
            "hasDischargeRecords": True if "discharge summary" in types_found else None,
        }

    # --- Q6 disability ----------------------------------------------------
    dis = raw.get("disability") if isinstance(raw.get("disability"), dict) else {}
    pct = dis.get("percentage")
    pct = pct if isinstance(pct, int) and not isinstance(pct, bool) and 0 <= pct <= 100 else None
    disability_answer = True if pct is not None else _bool(dis.get("answer"))

    # --- Q7 past insurance ------------------------------------------------
    pi = raw.get("past_insurance") if isinstance(raw.get("past_insurance"), dict) else {}
    pi_details = _str(pi.get("details"), 1000)
    pi_answer = True if pi_details else _bool(pi.get("answer"))

    q5 = _str(raw.get("q5_free_text"), 1500)

    return {
        "age": age,
        "gender": gender,
        "tobacco": {"answer": tobacco_answer, "forms": forms},
        "alcohol": {"answer": _bool(alc.get("answer"))},
        "medicalConditions": conditions,
        "hospitalization": hosp,
        "q5Text": q5,
        "disability": {"answer": disability_answer, "percentage": pct,
                       "certificateProvided": "disability certificate" in types_found},
        "pastInsurance": {"answer": pi_answer, "details": pi_details},
        "documents": documents,
        "warnings": warnings,
    }
