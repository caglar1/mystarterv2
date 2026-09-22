.DEFAULT_GOAL := help
MANAGE := uv run python manage.py

help: ## Komutları listele
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## İlk kurulum: bağımlılıklar, .env, Tailwind, vendor doğrulama, veritabanı, demo veri
	uv sync
	uv run python scripts/bootstrap_env.py
	uv run python scripts/vendor.py check
	$(MANAGE) tailwind install
	$(MANAGE) tailwind build
	$(MANAGE) migrate
	$(MANAGE) createcachetable
	$(MANAGE) seed_demo

dev: ## Geliştirme: runserver + tailwind --watch + görev worker'ı
	uv run honcho -f Procfile.dev start

css: ## CSS'i derle (minify)
	$(MANAGE) tailwind build

test: ## Testleri çalıştır
	uv run pytest

lint: ## Ruff kontrolü + format kontrolü
	uv run ruff check .
	uv run ruff format --check .

format: ## Kodu biçimlendir
	uv run ruff check --fix .
	uv run ruff format .

check: lint test ## Commit öncesi: lint + test + migration kontrolü
	$(MANAGE) makemigrations --check --dry-run

superuser: ## Yönetici hesabı oluştur
	$(MANAGE) createsuperuser

.PHONY: help setup dev css test lint format check superuser
