from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('draft', views.create_draft, name='create_draft'),
    path('draft/<int:draft_id>', views.show_draft, name='show_draft'),
    path('draft/<int:draft_id>/seat/<int:seat>', views.show_seat, name='show_seat'),
    path('draft/pick-card/<int:draft_id>', views.pick_card, name='pick_cards')
]