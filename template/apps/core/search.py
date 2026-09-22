"""Hibrit metin araması.

- PostgreSQL: `to_tsvector` fonksiyonel GIN index'i ile tam metin araması (websearch sözdizimi:
  "tam ifade", -hariç, VEYA), başlığa ağırlık veren sıralama.
- SQLite (geliştirme): `icontains` ile basit arama.

Index'in kullanılabilmesi için sorgudaki ifade, migration'da oluşturulan index ifadesiyle aynı
olmalıdır: `SearchVector(*fields, config=SEARCH_CONFIG)` (bkz. apps/news/migrations/0002_*).
Hata yutan `try/except` yok: Postgres tarafında bir sorun varsa görünür şekilde patlar.
"""

from functools import reduce
from operator import or_

from django.db import connection
from django.db.models import Q, QuerySet

SEARCH_CONFIG = "turkish"


def uses_postgres_search() -> bool:
    return connection.vendor == "postgresql"


def search_vector(*fields: str):
    """Index ile birebir aynı ifade (Postgres). psycopg yalnızca Postgres projelerinde kurulu."""
    from django.contrib.postgres.search import SearchVector

    return SearchVector(*fields, config=SEARCH_CONFIG)


def hybrid_search(
    queryset: QuerySet, term: str, *, fields: list[str], weights: list[str] | None = None
) -> QuerySet:
    term = (term or "").strip()
    if not term:
        return queryset

    if uses_postgres_search():
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        query = SearchQuery(term, search_type="websearch", config=SEARCH_CONFIG)
        weights = weights or ["A", "B", "C", "D"][: len(fields)]
        ranked = reduce(
            lambda a, b: a + b,
            (SearchVector(f, weight=w, config=SEARCH_CONFIG) for f, w in zip(fields, weights, strict=True)),
        )
        return (
            queryset.annotate(search=search_vector(*fields))
            .filter(search=query)
            .annotate(rank=SearchRank(ranked, query))
            .order_by("-rank")
        )

    conditions = reduce(or_, (Q(**{f"{field}__icontains": term}) for field in fields))
    return queryset.filter(conditions)
