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

messages: ## Çeviri dosyalarını güncelle ve derle (GNU gettext gerekir)
	uv run python scripts/messages.py

superuser: ## Yönetici hesabı oluştur
	$(MANAGE) createsuperuser

# .env'den okunur; ortamdan da verilebilir: make deploy DEPLOY_HOST=kullanici@sunucu
DEPLOY_HOST ?= $(shell [ -f .env ] && sed -n 's/^DEPLOY_HOST=//p' .env)
DEPLOY_PATH ?= $(shell [ -f .env ] && sed -n 's/^DEPLOY_PATH=//p' .env)

deploy: ## Canlıya al (sunucuda: git pull + yedek + compose + sağlık kontrolü)
	@test -n "$(DEPLOY_HOST)" -a -n "$(DEPLOY_PATH)" || \
		{ echo ".env içinde DEPLOY_HOST=kullanici@sunucu ve DEPLOY_PATH=/srv/proje tanımlayın."; exit 1; }
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_PATH) && sh deploy/deploy.sh"

.PHONY: help setup dev css test lint format check messages superuser deploy
