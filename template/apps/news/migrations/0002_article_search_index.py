"""PostgreSQL tam metin araması için fonksiyonel GIN index.

Yalnızca PostgreSQL'de oluşturulur (SQLite'ta atlanır). Index ifadesi, sorgudaki ifadeyle
birebir aynıdır: apps.core.search.search_vector("title", "content").
Import'lar fonksiyon içinde: SQLite projelerinde psycopg kurulu değildir.
"""

from django.db import migrations

INDEX_NAME = "news_article_fts_idx"


def create_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from django.contrib.postgres.indexes import GinIndex

    from apps.core.search import search_vector

    article = apps.get_model("news", "Article")
    schema_editor.add_index(article, GinIndex(search_vector("title", "content"), name=INDEX_NAME))


def drop_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")


class Migration(migrations.Migration):
    dependencies = [("news", "0001_initial")]

    operations = [migrations.RunPython(create_index, drop_index)]
