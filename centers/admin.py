from django.contrib import admin
from .models import ProjectCenter

@admin.register(ProjectCenter)
class ProjectCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'center_code', 'territory', 'cluster', 'beneficiaries')
    search_fields = ('name', 'center_code')
    list_filter = ('territory', 'cluster')


# Register your models here.
from .models import Participant

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "participant_name",
        "participant_id",
        "project_center",
        "sex",
        "caregiver_name",
    )
    list_filter = ("project_center", "sex")
    search_fields = ("participant_name", "participant_id")

from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "project_center")
    search_fields = ("user__username", "user__email", "project_center__name")
    list_filter = ("project_center",)
