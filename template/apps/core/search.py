"""Hibrit metin araması.

- PostgreSQL: önceden hesaplanmış `SearchVectorField` + GIN index + websearch sözdizimi + sıralama.
- SQLite (geliştirme): `icontains` ile basit arama.

Hata yutan `try/except` yok: Postgres tarafında bir sorun varsa görünür şekilde patlar.
"""

from functools import reduce
from operator import or_

from django.db import connection
from django.db.models import F, Q, QuerySet

SEARCH_CONFIG = "turkish"


def uses_postgres_search() -> bool:
    return connection.vendor == "postgresql"


def hybrid_search(
    queryset: QuerySet, term: str, *, vector_field: str, fallback_fields: list[str]
) -> QuerySet:
    term = (term or "").strip()
    if not term:
        return queryset

    if uses_postgres_search():
        from django.contrib.postgres.search import SearchQuery, SearchRank

        query = SearchQuery(term, search_type="websearch", config=SEARCH_CONFIG)
        return (
            queryset.filter(**{vector_field: query})
            .annotate(rank=SearchRank(F(vector_field), query))
            .order_by("-rank")
        )

    conditions = reduce(or_, (Q(**{f"{field}__icontains": term}) for field in fallback_fields))
    return queryset.filter(conditions)
