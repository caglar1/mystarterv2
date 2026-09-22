"""LLM prompt'ları. Prompt metni İngilizce; çıktı dili parametreyle istenir (aktif arayüz dili)."""

from django.conf import settings
from django.utils.translation import get_language

SUMMARY_SYSTEM = (
    "You are a clear, neutral editor. Summarize the text the user provides. "
    "Write only the summary: no introduction, title or commentary. Write in {language}."
)

SUMMARY_LENGTHS = {
    "short": "a short paragraph of 2-3 sentences",
    "bullets": "at most 5 bullet points",
    "detailed": "a detailed summary with headings, without unnecessary repetition",
}


def language_name(code: str | None = None) -> str:
    """Dil kodunu modelin anlayacağı ada çevirir (ör. 'tr' -> 'Turkish')."""
    from django.utils.translation import get_language_info

    code = code or get_language() or settings.LANGUAGE_CODE
    try:
        return get_language_info(code)["name"]
    except KeyError:
        return code


def summary_system(language: str | None = None) -> str:
    return SUMMARY_SYSTEM.format(language=language_name(language))


def summary_prompt(text: str, length: str) -> str:
    return f"Summarize the following text as {SUMMARY_LENGTHS[length]}.\n\n<text>\n{text}\n</text>"
