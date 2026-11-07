"""Step 2 of the pipeline: repair Bangla Unicode and common OCR conjunct errors.

The NCTB 2026 science PDFs are scanned images (no usable text layer), so text comes from
Tesseract OCR (`ben` model, tessdata_best). OCR output is valid Unicode but has two kinds of
error this module fixes or flags:

1. Unicode-level issues: non-NFC sequences, nukta letters written two ways (য় / য + ়),
   stray zero-width characters, Latin "|" used for the dari, ASCII digit look-alikes.
2. Glyph confusions on conjuncts and vowel signs, e.g. ভৌত -> ভোত, যন্ত্র -> যন্দ্র,
   ত্রুটি -> ত্রটি, ধ্রুবক -> ধুবক, শক্তি -> শত্তি. These are fixed with an explicit,
   reviewed word list (never a fuzzy guess), and every applied fix is recorded so the
   hand-check file can show it.

`legacy_encoding_score` detects SutonnyMJ / Bijoy legacy-encoded text (ASCII bytes drawn with
a Bangla font). That never occurs in OCR output but does occur in PDFs that have a text layer
made with legacy fonts; such text must be reported as garbage, not returned.
"""

from __future__ import annotations

import re
import unicodedata

# Word-level OCR confusions observed in the 2026 Physics (Bangla version) OCR.
# Left: OCR output. Right: correct spelling. Only add pairs seen in real output and checked
# against the page image.
WORD_FIXES: dict[str, str] = {
    "ভোত": "ভৌত",
    "যন্দ্রপাতি": "যন্ত্রপাতি",
    "যন্দ্র": "যন্ত্র",
    "ত্রটি": "ত্রুটি",
    "ধুবক": "ধ্রুবক",
    "শত্তি": "শক্তি",
    "শত্তির": "শক্তির",
    "চতুথ": "চতুর্থ",
    "তাত্ত্িক": "তাত্ত্বিক",
    "কিন্ছু": "কিন্তু",
    "দীড়িয়েছে": "দাঁড়িয়েছে",
    "দীঁড়িয়ে": "দাঁড়িয়ে",
    "মিথস্ত্রিয়া": "মিথস্ক্রিয়া",
    "সৃক্ষভাবে": "সূক্ষ্মভাবে",
    "সূক্মনভাবে": "সূক্ষ্মভাবে",
    "প্রবন্তা": "প্রবক্তা",
    "ব্যালাল": "ব্যালান্স",
    "ভেষ্টরের": "ভেক্টরের",
    "ক্কেল": "স্কেল",
}

_ZERO_WIDTH = re.compile("[\u200b\u2060\ufeff\u00ad]")
_BN = "\u0980-\u09ff"
_DIGITS_BN = "০১২৩৪৫৬৭৮৯"


def normalize(text: str) -> str:
    """Unicode clean-up that never changes meaning."""
    t = unicodedata.normalize("NFC", text)
    t = _ZERO_WIDTH.sub("", t)
    # ZWJ / ZWNJ are meaningful in Bangla only between letters; drop them elsewhere.
    t = re.sub(f"(?<![{_BN}])[\u200c\u200d]|[\u200c\u200d](?![{_BN}])", "", t)
    # Latin pipe or "I" used as dari after Bangla text.
    t = re.sub(f"(?<=[{_BN}])\\s*[|]\\s*", "। ", t)
    t = re.sub(r"\s+।", "।", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def fix_words(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Apply WORD_FIXES on whole words. Returns the text and the list of fixes applied."""
    applied: list[tuple[str, str]] = []

    def repl(m: re.Match[str]) -> str:
        w = m.group(0)
        if w in WORD_FIXES:
            applied.append((w, WORD_FIXES[w]))
            return WORD_FIXES[w]
        return w

    out = re.sub(f"[{_BN}]+", repl, text)
    return out, applied


def fix_line(text: str) -> tuple[str, list[tuple[str, str]]]:
    return fix_words(normalize(text))


def bn_to_int(s: str) -> int | None:
    """Bangla (or ASCII) digits to int. OCR often reads ৪ as 8, so 8 is accepted too."""
    s = s.strip()
    if not s:
        return None
    out = ""
    for ch in s:
        if ch in _DIGITS_BN:
            out += str(_DIGITS_BN.index(ch))
        elif ch.isascii() and ch.isdigit():
            out += ch
        else:
            return None
    return int(out)


# --- garbage detection -------------------------------------------------------------------

# Characters typical of Bijoy / SutonnyMJ text read as Latin-1: Avwg (আমি), †K (কে), ‡Q (ছে) ...
_LEGACY_MARKERS = re.compile(r"[†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÐÑØ×÷]")
_LEGACY_WORDS = re.compile(r"\b(Avwg|Ges|Kiv|nq|Zvi|GKwU|n‡q|KviY|evsjv|wbqg)\b")


def legacy_encoding_score(text: str) -> float:
    """0..1 likelihood that `text` is Bijoy/SutonnyMJ legacy-encoded Bangla."""
    if not text:
        return 0.0
    markers = len(_LEGACY_MARKERS.findall(text))
    words = len(_LEGACY_WORDS.findall(text))
    bn = len(re.findall(f"[{_BN}]", text))
    letters = len(re.findall(r"[A-Za-z]", text))
    if bn > letters:
        return 0.0
    score = min(1.0, (markers / max(1, len(text))) * 20 + words * 0.2)
    return round(score, 3)


def ocr_quality(text: str) -> dict[str, float]:
    """Rough quality signals for a page of OCR output."""
    bn = len(re.findall(f"[{_BN}]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    junk = len(re.findall(r"[@#$%^&*~`{}<>\\]", text))
    total = max(1, len(re.sub(r"\s", "", text)))
    return {
        "bangla_ratio": round(bn / total, 3),
        "latin_ratio": round(latin / total, 3),
        "junk_ratio": round(junk / total, 3),
        "legacy_score": legacy_encoding_score(text),
    }
