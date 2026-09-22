import subprocess

from django.core.management.base import BaseCommand, CommandError

from apps.core import tailwind


class Command(BaseCommand):
    help = "Tailwind CSS standalone CLI: install | build | watch"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["install", "build", "watch"])
        parser.add_argument("--force", action="store_true", help="install: yeniden indir")

    def handle(self, *args, action, force, **options):
        try:
            if action == "install":
                path = tailwind.install(force=force)
                self.stdout.write(self.style.SUCCESS(f"Tailwind {tailwind.TAILWIND_VERSION}: {path}"))
                return
            args = tailwind.command(watch=action == "watch", minify=action == "build")
        except tailwind.TailwindError as exc:
            raise CommandError(str(exc)) from exc

        try:
            subprocess.run(args, check=True)  # noqa: S603 (sabit, doğrulanmış binary)
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"Tailwind başarısız oldu (çıkış kodu {exc.returncode})") from exc
        except KeyboardInterrupt:
            pass
