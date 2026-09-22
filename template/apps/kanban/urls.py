from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "kanban"

urlpatterns = [
    path("", views.boards, name="boards"),
    path("<int:pk>/", views.board_detail, name="board"),
    path(_("<int:pk>/card/"), views.card_create, name="card_create"),
    path(_("card/<int:pk>/move/"), views.card_move, name="card_move"),
    path(_("card/<int:pk>/delete/"), views.card_delete, name="card_delete"),
]
