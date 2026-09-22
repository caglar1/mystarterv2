"""Senkronizasyon işleri için ortak altyapı.

Modüller işlerini `register_job()` ile kaydeder (AppConfig.ready içinde). Bir iş:
- cron'dan yönetim komutuyla senkron çalışabilir: `run_job("news")`
- arayüzden kuyruğa alınabilir: `enqueue_job("news", user)` -> worker `run_sync_job` görevini çalıştırır
Her iki yol da bir `SyncRun` kaydı tutar.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.tasks import task
from django.utils import timezone

from .models import SyncRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncJob:
    name: str
    label: str
    handler: Callable[[], tuple[int, str]]  # (işlenen öge sayısı, özet mesaj)


JOBS: dict[str, SyncJob] = {}


def register_job(name: str, label: str, handler: Callable[[], tuple[int, str]]) -> None:
    JOBS[name] = SyncJob(name=name, label=label, handler=handler)


def execute(run: SyncRun) -> SyncRun:
    job = JOBS[run.job]
    run.status = SyncRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])
    try:
        items, message = job.handler()
    except Exception as exc:
        logger.exception("Senkronizasyon başarısız: %s", run.job)
        run.status = SyncRun.Status.FAILED
        run.message = f"{type(exc).__name__}: {exc}"
    else:
        run.status = SyncRun.Status.SUCCESS
        run.items = items
        run.message = message
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "items", "message", "finished_at"])
    return run


def run_job(name: str) -> SyncRun:
    """Senkron çalıştırır (cron / yönetim komutu)."""
    return execute(SyncRun.objects.create(job=name))


def enqueue_job(name: str, user=None) -> SyncRun:
    """Kuyruğa alır; `db_worker` çalıştırır."""
    run = SyncRun.objects.create(job=name, triggered_by=user if user and user.is_authenticated else None)
    run_sync_job.enqueue(run.pk)
    return run


@task
def run_sync_job(run_id: int) -> None:
    run = SyncRun.objects.get(pk=run_id)
    if run.status == SyncRun.Status.QUEUED:
        execute(run)
