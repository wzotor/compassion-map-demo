# centers/urls.py

from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="/participants/", permanent=False), name="home"),

    # Staff routes
    path("map/", views.map_view, name="map"),

    path("participants/", views.participant_list, name="participant_list"),
    path("participants/add/", views.participant_add, name="participant_add"),
    path("participants/map/", views.participant_map, name="participant_map"),
    path("participants/upload/", views.participant_upload, name="participant_upload"),
    path("participants/upload/template/", views.participants_csv_template, name="participants_csv_template"),
    path("participants/<int:pk>/edit/", views.participant_edit, name="participant_edit"),
    path("participants/<int:pk>/delete/", views.participant_delete, name="participant_delete"),

    # =========================
    # National Office - Participants
    # =========================
    path("national/participants/", views.national_participants_home, name="national_participants_home"),
    path("national/participants/list/", views.national_participants_list, name="national_participants_list"),

    # NEW: National participant edit/delete
    path("national/participants/<int:pk>/edit/", views.national_participant_edit, name="national_participant_edit"),
    path("national/participants/<int:pk>/delete/", views.national_participant_delete, name="national_participant_delete"),

    # =========================
    # National Office - Centers
    # =========================
    path("national/centers/", views.national_centers_list, name="national_centers_list"),
    path("national/centers/add/", views.national_center_add, name="national_center_add"),

    # =========================
    # National Dashboard & Map
    # =========================
    path("national-map/", views.national_centers_map, name="national_centers_map"),
    path("dashboard/", views.national_dashboard, name="national_dashboard"),
]