import importlib

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Kurulu tüm modüller için demo veri oluşturur (tekrar çalıştırmak güvenlidir)."

    def handle(self, *args, **options):
        for config in apps.get_app_configs():
            if not config.name.startswith("apps."):
                continue
            try:
                module = importlib.import_module(f"{config.name}.demo")
            except ModuleNotFoundError as exc:
                if exc.name != f"{config.name}.demo":
                    raise
                continue
            summary = module.seed()
            self.stdout.write(self.style.SUCCESS(f"[{config.label}] {summary}"))
