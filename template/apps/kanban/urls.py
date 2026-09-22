from django.urls import path

from . import views

app_name = "kanban"

urlpatterns = [
    path("", views.boards, name="boards"),
    path("<int:pk>/", views.board_detail, name="board"),
    path("<int:pk>/kart/", views.card_create, name="card_create"),
    path("kart/<int:pk>/tasi/", views.card_move, name="card_move"),
    path("kart/<int:pk>/sil/", views.card_delete, name="card_delete"),
]
