from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.search import hybrid_search

from .models import Article
from .pipeline import CATEGORIES

PAGE_SIZE = 12


@require_GET
def article_list(request):
    q = request.GET.get("q", "").strip()[:200]
    category = request.GET.get("category", "")
    articles = Article.objects.select_related("feed")
    if category in CATEGORIES:
        articles = articles.filter(category=category)
    articles = hybrid_search(articles, q, fields=["title", "content"])
    page_obj = Paginator(articles, PAGE_SIZE).get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "q": q,
        "category": category,
        "categories": CATEGORIES,
        "show_images": settings.NEWS_SHOW_REMOTE_IMAGES,
    }
    if request.htmx:
        # "Daha fazla" -> yalnızca yeni kartlar; arama/filtre -> sonuç alanının tamamı
        partial = "items" if request.GET.get("page") else "results"
        return render(request, f"news/list.html#{partial}", context)
    return render(request, "news/list.html", context)
