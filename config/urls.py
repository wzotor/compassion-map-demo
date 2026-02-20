from django.contrib import admin
from django.urls import path, include
from centers import views as centers_views

admin.site.site_header = "Compassion Map Admin"
admin.site.site_title = "Compassion Map Admin"
admin.site.index_title = "National Office Dashboard"

urlpatterns = [
    path("admin/", admin.site.urls),

    # Custom logout (fixes HTTP 405 issue)
    path("accounts/logout/", centers_views.logout_view, name="logout"),

    # Django built-in authentication URLs
    path("accounts/", include("django.contrib.auth.urls")),

    # App URLs
    path("", include("centers.urls")),
]
