import json
import re


VALID_ACTIONS = {"COMMIT", "ABSTAIN", "ESCALATE"}


def _normalize_candidate(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _validate_payload(payload):
    action = str(payload.get("action", "")).upper().strip()
    if action not in VALID_ACTIONS:
        raise ValueError("action must be one of COMMIT, ABSTAIN, ESCALATE")

    confidence = payload.get("confidence", 0.0)
    if isinstance(confidence, str):
        confidence = float(confidence)
    confidence = float(confidence)
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0 and 1")

    reason = str(payload.get("reason", "")).strip()
    if not reason:
        raise ValueError("reason must be non-empty")

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason,
        "parse_error": False,
    }


def parse_model_response(raw_text):
    try:
        return _validate_payload(json.loads(_normalize_candidate(raw_text)))
    except Exception:
        pass

    normalized = _normalize_candidate(raw_text)
    start = normalized.find("{")
    end = normalized.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = normalized[start : end + 1]
        try:
            return _validate_payload(json.loads(candidate))
        except Exception:
            pass

    return {
        "action": None,
        "confidence": None,
        "reason": "",
        "parse_error": True,
        "raw_text": raw_text,
    }
