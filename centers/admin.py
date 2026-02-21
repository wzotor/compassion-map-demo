import csv
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

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
    list_filter = ("action", "project_center", "timestamp", "user")
    search_fields = (
        "participant_id",
        "details",
        "user__username",
        "user__email",
        "project_center__center_code",
        "project_center__name",
    )
    ordering = ("-timestamp",)

    # Make every field read-only in the admin detail page
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    # Disable add/edit/delete in admin (view-only audit trail)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Use a custom changelist template that adds an export button
    change_list_template = "admin/auditlog_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv),
                name="auditlog_export_csv",
            ),
        ]
        return custom_urls + urls

    def export_csv(self, request):
        """
        Export the current filtered queryset from the changelist.
        This respects all filters/search currently applied in admin.
        """
        cl = self.get_changelist_instance(request)
        qs = cl.get_queryset(request)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_logs_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "timestamp",
                "action",
                "user",
                "user_email",
                "project_center",
                "center_code",
                "participant_id",
                "details",
            ]
        )

        for log in qs.select_related("user", "project_center").iterator():
            writer.writerow(
                [
                    log.timestamp.isoformat() if log.timestamp else "",
                    log.action,
                    getattr(log.user, "username", "") if log.user else "",
                    getattr(log.user, "email", "") if log.user else "",
                    str(log.project_center) if log.project_center else "",
                    getattr(log.project_center, "center_code", "") if log.project_center else "",
                    log.participant_id or "",
                    log.details or "",
                ]
            )

        return response