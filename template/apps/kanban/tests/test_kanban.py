import pytest
from django.urls import reverse

from apps.kanban.models import Board, Card
from conftest import HTMX


@pytest.fixture
def board(user):
    board = Board.objects.create(name="Pano", owner=user)
    for i, title in enumerate(["A", "B", "C"]):
        Card.objects.create(board=board, title=title, status="todo", position=i)
    Card.objects.create(board=board, title="D", status="doing", position=0)
    return board


def titles(board, status):
    return list(board.cards.filter(status=status).order_by("position").values_list("title", flat=True))


@pytest.mark.django_db
def test_requires_login(client):
    assert client.get(reverse("kanban:boards")).status_code == 302


@pytest.mark.django_db
def test_first_visit_creates_starter_board(user_client, user):
    response = user_client.get(reverse("kanban:boards"))
    assert response.status_code == 200
    assert Board.objects.filter(owner=user).count() == 1
    user_client.get(reverse("kanban:boards"))
    assert Board.objects.filter(owner=user).count() == 1  # tekrar oluşturulmaz


@pytest.mark.django_db
def test_create_board_redirects(user_client, user):
    response = user_client.post(reverse("kanban:boards"), {"name": "Yeni"})
    board = Board.objects.get(name="Yeni")
    assert board.owner == user
    assert response["Location"] == reverse("kanban:board", args=[board.pk])


@pytest.mark.django_db
def test_board_page_renders_columns(user_client, board):
    body = user_client.get(reverse("kanban:board", args=[board.pk])).content.decode()
    assert body.count('x-data="kanbanColumn"') == 3
    assert "Sortable.min.js" in body
    assert 'id="count-todo" class="badge badge-neutral badge-sm">3<' in body


@pytest.mark.django_db
def test_other_users_board_is_404(client, board, django_user_model):
    other = django_user_model.objects.create_user("baska", password="x")
    client.force_login(other)
    assert client.get(reverse("kanban:board", args=[board.pk])).status_code == 404
    card = board.cards.first()
    response = client.post(
        reverse("kanban:card_move", args=[card.pk]), {"status": "done", "order": str(card.pk)}
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_card_appends_and_updates_count(user_client, board):
    response = user_client.post(
        reverse("kanban:card_create", args=[board.pk]), {"title": "E", "status": "doing"}, **HTMX
    )
    body = response.content.decode()
    assert "<li data-card-id=" in body and ">E<" in body
    assert 'id="count-doing" class="badge badge-neutral badge-sm" hx-swap-oob="true">2<' in body
    assert titles(board, "doing") == ["D", "E"]


@pytest.mark.django_db
def test_create_card_rejects_empty_title(user_client, board):
    response = user_client.post(
        reverse("kanban:card_create", args=[board.pk]), {"title": " ", "status": "todo"}, **HTMX
    )
    assert response.status_code == 422
    assert response["HX-Reswap"] == "none"
    assert "cannot be empty" in response.content.decode()  # toast (OOB)


@pytest.mark.django_db
def test_move_card_between_columns_persists_order(user_client, board):
    a, b, c = (board.cards.get(title=t) for t in "ABC")
    d = board.cards.get(title="D")
    # B'yi "doing" sütununun başına taşı: [B, D]
    response = user_client.post(
        reverse("kanban:card_move", args=[b.pk]), {"status": "doing", "order": f"{b.pk},{d.pk}"}, **HTMX
    )
    assert response.status_code == 200
    assert titles(board, "doing") == ["B", "D"]
    assert titles(board, "todo") == ["A", "C"]
    assert (
        'id="count-todo" class="badge badge-neutral badge-sm" hx-swap-oob="true">2<'
        in response.content.decode()
    )

    # Aynı sütunda yeniden sırala: [C, A]
    user_client.post(
        reverse("kanban:card_move", args=[a.pk]), {"status": "todo", "order": f"{c.pk},{a.pk}"}, **HTMX
    )
    assert titles(board, "todo") == ["C", "A"]


@pytest.mark.django_db
def test_move_ignores_foreign_ids_and_rejects_bad_input(user_client, board, django_user_model):
    other_board = Board.objects.create(
        name="X", owner=django_user_model.objects.create_user("x", password="x")
    )
    foreign = Card.objects.create(board=other_board, title="Yabancı", status="done")
    a = board.cards.get(title="A")
    user_client.post(
        reverse("kanban:card_move", args=[a.pk]), {"status": "done", "order": f"{foreign.pk},{a.pk}"}
    )
    assert titles(board, "done") == ["A"]
    foreign.refresh_from_db()
    assert foreign.board == other_board

    bad = user_client.post(reverse("kanban:card_move", args=[a.pk]), {"status": "uzay", "order": "1"})
    assert bad.status_code == 400
    bad = user_client.post(reverse("kanban:card_move", args=[a.pk]), {"status": "todo", "order": "1,x"})
    assert bad.status_code == 400


@pytest.mark.django_db
def test_delete_card(user_client, board):
    card = board.cards.get(title="A")
    response = user_client.post(reverse("kanban:card_delete", args=[card.pk]), **HTMX)
    assert response.status_code == 200
    assert not Card.objects.filter(pk=card.pk).exists()
    assert "<li" not in response.content.decode()
