import re

SUPERSCRIPT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

# common unicode escapes the LLM outputs as raw strings
UNICODE_FIXES = {
    r"\u221e": "∞",
    r"\u221E": "∞",
    r"\u2265": "≥",
    r"\u2264": "≤",
    r"\u2260": "≠",
    r"\u00b2": "²",
    r"\u00b3": "³",
    r"\u03b1": "α",
    r"\u03b2": "β",
    r"\u03b8": "θ",
    r"\u03c0": "π",
    r"\u00b0": "°",
    r"\u2212": "−",
    r"\u00d7": "×",
    r"\u00f7": "÷",
    r"\u221a": "√",
}


def fix_unicode(text):
    """Replace raw unicode escapes with actual characters."""
    for escape, char in UNICODE_FIXES.items():
        text = text.replace(escape, char)
    # also handle actual unicode escape sequences
    try:
        import codecs

        text = codecs.decode(text.encode(), "unicode_escape").decode(
            "utf-8", errors="ignore"
        )
    except:
        pass
    return text


def render_exponents(text):
    """Convert 10^24 -> 10²⁴, x^2 -> x², etc."""

    def replace(m):
        base = m.group(1)
        exp = m.group(2).translate(SUPERSCRIPT)
        return f"{base}{exp}"

    return re.sub(r"(\w+)\^([-+]?\d+)", replace, text)


def clean_text(text):
    """Apply all text fixes."""
    text = fix_unicode(text)
    text = render_exponents(text)
    return text
