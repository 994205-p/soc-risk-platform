"""
Optional AI-assisted explanation layer.

IMPORTANT: this layer never determines risk and never invents evidence. It
only rewords/summarizes the deterministic explanation and evidence already
produced by app/risk_engine (the authoritative source of risk -- see
docs/responsible_ai.md). If disabled, misconfigured, or the call fails for
any reason, the application falls back to the deterministic explanation
transparently and continues working -- this fallback path is exercised by
default since ENABLE_LLM_EXPLANATIONS=false out of the box.

Every result carries an explicit `source` and `label` so the UI can show
"AI-assisted explanation" vs "Evidence-based deterministic explanation" --
the distinction must never be hidden from the user.
"""
import json
import urllib.request
import urllib.error

from app.config import settings

DETERMINISTIC_LABEL = "Evidence-based deterministic explanation"
AI_ASSISTED_LABEL = "AI-assisted explanation"

SYSTEM_PROMPT = (
    "You are rewording a security risk explanation for a business audience. "
    "You MUST only use the facts given to you in the evidence block below. "
    "Do not invent, assume, or add any vulnerability, incident, control, "
    "statistic, or date that is not explicitly present in the evidence. "
    "Do not change any number. If the evidence is insufficient to explain "
    "something, say so explicitly rather than guessing. Keep the response "
    "to 3-5 sentences, plain business language, no markdown."
)


def get_ai_explanation(deterministic_text: str, evidence: dict) -> dict:
    """
    Attempt an AI-assisted rewording of the deterministic explanation.
    Always returns a dict with keys: text, source, label.
    Falls back to the deterministic explanation on any failure, missing
    key, or when the feature flag is off -- this function NEVER raises.
    """
    if not settings.ENABLE_LLM_EXPLANATIONS or not settings.ANTHROPIC_API_KEY:
        return {"text": deterministic_text, "source": "deterministic", "label": DETERMINISTIC_LABEL}

    try:
        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 400,
            "system": SYSTEM_PROMPT,
            "messages": [{
                "role": "user",
                "content": (
                    f"Deterministic explanation (ground truth, do not contradict):\n{deterministic_text}\n\n"
                    f"Supporting evidence (JSON, the ONLY facts you may reference):\n"
                    f"{json.dumps(evidence, default=str)}"
                ),
            }],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text_blocks = [b["text"] for b in body.get("content", []) if b.get("type") == "text"]
        ai_text = " ".join(text_blocks).strip()
        if not ai_text:
            raise ValueError("empty AI response")
        return {"text": ai_text, "source": "ai_assisted", "label": AI_ASSISTED_LABEL}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as e:
        # Never let an AI/network failure break the app -- fall back silently
        # to the deterministic explanation, which is always correct on its own.
        return {
            "text": deterministic_text,
            "source": "deterministic",
            "label": DETERMINISTIC_LABEL,
            "ai_fallback_reason": str(e),
        }
