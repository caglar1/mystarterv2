import logging
import threading
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.html import escape
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from apps.core.ratelimit import ratelimit

from . import llm
from .forms import SummarizeForm
from .prompts import summary_prompt, summary_system

logger = logging.getLogger(__name__)

JOB_TTL = 300
# Aynı process'te eşzamanlı açık LLM stream'lerini sınırlar: gunicorn thread'leri tükenmesin.
_STREAM_SLOTS = threading.BoundedSemaphore(settings.LLM_MAX_CONCURRENT_STREAMS)


def _job_key(key: str) -> str:
    return f"ai:summary:{key}"


@login_required
@require_GET
def summarize(request):
    return render(
        request,
        "ai/summarize.html",
        {"form": SummarizeForm(), "configured": llm.get_client().configured},
    )


@login_required
@require_POST
@ratelimit("ai-summary", rate="10/h", per_user=True)
def summarize_start(request):
    form = SummarizeForm(request.POST)
    if not form.is_valid():
        return render(request, "ai/summarize.html#form", {"form": form, "configured": True}, status=422)
    key = uuid.uuid4().hex
    # Stream ayrı bir istekte açılır; özetin dili formun gönderildiği dil olsun.
    job = {"user_id": request.user.pk, "language": get_language(), **form.cleaned_data}
    cache.set(_job_key(key), job, JOB_TTL)
    return render(request, "ai/summarize.html#stream", {"key": key})


def _sse(event: str, data: str) -> str:
    lines = data.splitlines() or [""]
    return f"event: {event}\n" + "".join(f"data: {line}\n" for line in lines) + "\n"


def _alert(message: str) -> str:
    return render_to_string("ai/partials/alert.html", {"message": message})


def _summary_events(job: dict):
    # Bu generator view döndükten sonra, yanıt akarken çalışır: dili açıkça sabitle.
    with translation.override(job["language"]):
        yield from _summary_events_in_language(job)


def _summary_events_in_language(job: dict):
    if not _STREAM_SLOTS.acquire(blocking=False):
        yield _sse("failure", _alert(_("The server is busy right now. Please try again in a moment.")))
        yield _sse("done", "")
        return
    try:
        client = llm.get_client()
        prompt = summary_prompt(job["text"], job["length"])
        for chunk in client.stream(prompt, system=summary_system(job["language"])):
            yield _sse("delta", escape(chunk))
    except llm.LLMRefused:
        yield _sse("failure", _alert(_("The model declined to answer this request.")))
    except llm.LLMError as exc:
        logger.warning("Özet üretilemedi: %s", exc)
        yield _sse("failure", _alert(_("Could not generate the summary. Please try again later.")))
    finally:
        _STREAM_SLOTS.release()
    yield _sse("done", f'<span class="text-success">{escape(_("Done"))}</span>')


@login_required
@require_GET
def summarize_stream(request, key: str):
    job = cache.get(_job_key(key))
    if not job or job["user_id"] != request.user.pk:
        raise Http404
    cache.delete(_job_key(key))  # tek kullanımlık
    response = StreamingHttpResponse(_summary_events(job), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Nginx/Caddy tamponlamasın
    return response
