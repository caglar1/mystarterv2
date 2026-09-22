from django.core.management.base import BaseCommand, CommandError

from apps.core import sync


class Command(BaseCommand):
    help = "Kayıtlı bir senkronizasyon işini hemen çalıştırır (cron için). Örn: manage.py sync news"

    def add_arguments(self, parser):
        parser.add_argument("job", nargs="?", help="İş adı; boş bırakılırsa kayıtlı işler listelenir")

    def handle(self, *args, job, **options):
        if not job:
            for name, item in sync.JOBS.items():
                self.stdout.write(f"{name}: {item.label}")
            return
        if job not in sync.JOBS:
            raise CommandError(f"Bilinmeyen iş: {job}. Kayıtlı işler: {', '.join(sync.JOBS) or '-'}")
        run = sync.run_job(job)
        if run.status == run.Status.FAILED:
            raise CommandError(f"{job} başarısız: {run.message}")
        self.stdout.write(self.style.SUCCESS(f"{job}: {run.items} öge — {run.message}"))
