from django.contrib import admin
from django.urls import path, include
from centers import views as centers_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Custom logout (fixes HTTP 405 issue)
    path("accounts/logout/", centers_views.logout_view, name="logout"),

    # Django built-in authentication URLs
    path("accounts/", include("django.contrib.auth.urls")),

    # App URLs
    path("", include("centers.urls")),
]
