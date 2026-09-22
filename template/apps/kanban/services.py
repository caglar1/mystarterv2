from django.db import transaction
from django.db.models import Max

from .models import Board, Card

STARTER_CARDS = [
    ("Kanban'ı keşfet", Card.Status.TODO),
    ("Kartları sürükleyip bırak", Card.Status.DOING),
    ("Panoyu oluştur", Card.Status.DONE),
]


def ensure_starter_board(user) -> None:
    """İlk ziyarette örnek bir pano oluşturur (boş ekran yerine)."""
    if Board.objects.filter(owner=user).exists():
        return
    board = Board.objects.create(name="İlk panom", owner=user)
    Card.objects.bulk_create(
        [
            Card(board=board, title=title, status=status, position=i)
            for i, (title, status) in enumerate(STARTER_CARDS)
        ]
    )


def add_card(board: Board, title: str, status: str) -> Card:
    last = board.cards.filter(status=status).aggregate(last=Max("position"))["last"]
    return Card.objects.create(board=board, title=title, status=status, position=(last or 0) + 1)


@transaction.atomic
def move_card(card: Card, status: str, ordered_ids: list[int]) -> None:
    """Kartı hedef sütuna taşır ve o sütunun sırasını istemcinin gönderdiği sıraya göre yazar.

    Yalnızca aynı panodaki ve hedef sütundaki kartlar dikkate alınır; bilinmeyen kimlikler yok sayılır.
    """
    card.status = status
    card.save(update_fields=["status", "updated_at"])
    column = {c.pk: c for c in Card.objects.select_for_update().filter(board=card.board, status=status)}
    ordered = [column[pk] for pk in ordered_ids if pk in column]
    ordered += [c for pk, c in column.items() if pk not in ordered_ids]  # eksik gönderilenler sona
    for position, item in enumerate(ordered):
        item.position = position
    Card.objects.bulk_update(ordered, ["position"])
