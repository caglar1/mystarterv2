from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import BoardForm, CardForm, MoveForm
from .models import Board, Card


def _counts(board: Board) -> list[tuple[str, int]]:
    totals = dict(board.cards.values_list("status").annotate(total=Count("id")))
    return [(status, totals.get(status, 0)) for status in Card.Status.values]


def _render_with_counts(request, board, template="kanban/_counts_oob.html", context=None, status=200):
    context = {**(context or {}), "counts": _counts(board)}
    return render(request, template, context, status=status)


@login_required
def boards(request):
    services.ensure_starter_board(request.user)
    form = BoardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        board = form.save(commit=False)
        board.owner = request.user
        board.save()
        return redirect("kanban:board", board.pk)
    user_boards = Board.objects.filter(owner=request.user).annotate(card_count=Count("cards"))
    return render(request, "kanban/boards.html", {"boards": user_boards, "form": form})


@login_required
def board_detail(request, pk: int):
    board = get_object_or_404(Board, pk=pk, owner=request.user)
    cards = list(board.cards.all())
    columns = [
        {"value": value, "label": label, "cards": [c for c in cards if c.status == value]}
        for value, label in Card.Status.choices
    ]
    return render(request, "kanban/board.html", {"board": board, "columns": columns, "card_form": CardForm()})


@login_required
@require_POST
def card_create(request, pk: int):
    board = get_object_or_404(Board, pk=pk, owner=request.user)
    form = CardForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Kart başlığı boş olamaz.")
        response = render(request, "kanban/_counts_oob.html", {"counts": _counts(board)}, status=422)
        response["HX-Reswap"] = "none"
        return response
    card = services.add_card(board, form.cleaned_data["title"], form.cleaned_data["status"])
    return _render_with_counts(request, board, "kanban/_card_created.html", {"card": card})


@login_required
@require_POST
def card_move(request, pk: int):
    card = get_object_or_404(Card.objects.select_related("board"), pk=pk, board__owner=request.user)
    form = MoveForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Geçersiz taşıma isteği")
    services.move_card(card, form.cleaned_data["status"], form.cleaned_data["order"])
    return _render_with_counts(request, card.board)


@login_required
@require_POST
def card_delete(request, pk: int):
    card = get_object_or_404(Card.objects.select_related("board"), pk=pk, board__owner=request.user)
    board = card.board
    card.delete()
    return _render_with_counts(request, board)
