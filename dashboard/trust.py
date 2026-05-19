"""Trust and provenance helpers for the Streamlit dashboard UI."""

from __future__ import annotations

from html import escape


TRUST_LIVE = "live"
TRUST_REPLAY = "replay"
TRUST_DERIVED = "derived"
TRUST_MODEL_UNAVAILABLE = "model_unavailable"
TRUST_NOT_CHECKED = "not_checked"

TRUST_TONES = {
    TRUST_LIVE: "ok",
    TRUST_REPLAY: "info",
    TRUST_DERIVED: "warn",
    TRUST_MODEL_UNAVAILABLE: "warn",
    TRUST_NOT_CHECKED: "risk",
}

TRUST_LABELS = {
    "en": {
        TRUST_LIVE: "Live",
        TRUST_REPLAY: "Replay",
        TRUST_DERIVED: "Derived",
        TRUST_MODEL_UNAVAILABLE: "Model unavailable",
        TRUST_NOT_CHECKED: "Not checked",
    },
    "th": {
        TRUST_LIVE: "ข้อมูลสด",
        TRUST_REPLAY: "ข้อมูลย้อนหลัง",
        TRUST_DERIVED: "คำนวณจากข้อมูล",
        TRUST_MODEL_UNAVAILABLE: "ยังไม่มีโมเดล",
        TRUST_NOT_CHECKED: "ยังไม่ตรวจ",
    },
    "zh": {
        TRUST_LIVE: "实时",
        TRUST_REPLAY: "回放",
        TRUST_DERIVED: "派生",
        TRUST_MODEL_UNAVAILABLE: "模型不可用",
        TRUST_NOT_CHECKED: "未检查",
    },
    "ja": {
        TRUST_LIVE: "ライブ",
        TRUST_REPLAY: "リプレイ",
        TRUST_DERIVED: "派生",
        TRUST_MODEL_UNAVAILABLE: "モデル未利用",
        TRUST_NOT_CHECKED: "未確認",
    },
}


def trust_label(level: str, lang: str = "en") -> str:
    """Return a localized trust label."""
    return TRUST_LABELS.get(lang, TRUST_LABELS["en"]).get(level, TRUST_LABELS["en"].get(level, level))


def trust_badge_html(level: str, lang: str = "en") -> str:
    """Return a compact trust/provenance badge."""
    tone = TRUST_TONES.get(level, "info")
    return f'<span class="trust-badge trust-{escape(tone)}">{escape(trust_label(level, lang))}</span>'


def trust_badges_html(levels: list[str], lang: str = "en") -> str:
    """Return multiple trust badges as one HTML fragment."""
    unique_levels = list(dict.fromkeys(levels))
    return '<span class="trust-badge-row">' + "".join(trust_badge_html(level, lang) for level in unique_levels) + "</span>"
