from django.urls import path
from . import views

urlpatterns = [
    path("map/", views.map_view, name="map"),
    path("participants/", views.participant_list, name="participant_list"),
    path("participants/add/", views.participant_add, name="participant_add"),
    path("participants/map/", views.participant_map, name="participant_map"),
    path("participants/upload/", views.participant_upload, name="participant_upload"),
    path("participants/upload/template/", views.participants_csv_template, name="participants_csv_template"),
path("participants/<int:pk>/edit/", views.participant_edit, name="participant_edit"),
path("participants/<int:pk>/delete/", views.participant_delete, name="participant_delete"),
]
