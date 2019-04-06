from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('draft', views.create_draft, name='create_draft'),
    path('draft/<int:draft_id>', views.draft, name='draft')
]