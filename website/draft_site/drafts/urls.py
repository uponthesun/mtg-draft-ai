from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('drafts', views.drafts, name='drafts'),
    path('draft/create', views.create_draft, name='create_draft'),
    path('draft/<int:draft_id>', views.show_draft, name='show_draft'),
    path('draft/<int:draft_id>/seat/<int:seat>', views.show_seat, name='show_seat'),
    path('draft/<int:draft_id>/seat/<int:seat>/auto-build', views.auto_build, name='auto_build'),
    path('draft/<int:draft_id>/seat/<int:seat>/all-picks', views.all_picks, name='all_picks'),
    path('draft/<int:draft_id>/pick-card', views.pick_card, name='pick_card'),
    path('draft/<int:draft_id>/queued-packs', views.api.queued_packs, name='queued_packs')
]
