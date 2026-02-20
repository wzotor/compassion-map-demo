from django.contrib import admin
from .models import ProjectCenter, Participant, UserProfile, AuditLog


@admin.register(ProjectCenter)
class ProjectCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "center_code", "territory", "cluster", "beneficiaries")
    search_fields = ("name", "center_code")
    list_filter = ("territory", "cluster")


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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        AuditLog.objects.create(
            user=request.user,
            action="UPDATE" if change else "CREATE",
            project_center=obj.project_center,
            participant_id=obj.participant_id,
            details=("Updated via Admin" if change else "Created via Admin"),
        )

    def delete_model(self, request, obj):
        AuditLog.objects.create(
            user=request.user,
            action="DELETE",
            project_center=obj.project_center,
            participant_id=obj.participant_id,
            details="Deleted via Admin",
        )
        super().delete_model(request, obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "project_center")
    search_fields = ("user__username", "user__email", "project_center__name")
    list_filter = ("project_center",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "user", "project_center", "participant_id")
    list_filter = ("action", "project_center", "timestamp")
    search_fields = (
        "participant_id",
        "details",
        "user__username",
        "project_center__center_code",
        "project_center__name",
    )
    ordering = ("-timestamp",)