# centers/views.py

import csv
import io
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import ProjectCenter, Participant, UserProfile, AuditLog
from .forms import ParticipantForm, ParticipantUploadForm


def _log_action(user, action, project_center=None, participant_id=None, details=""):
    """
    Create an audit log record. Safe by default.
    """
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            project_center=project_center,
            participant_id=participant_id,
            details=details or "",
        )
    except Exception:
        # Never break the app if logging fails
        pass


def is_national_officer(user):
    """
    National Officer = user in Group named 'National Office'
    No need to assign Django admin permissions for this group.
    """
    if not user.is_authenticated:
        return False
    return user.groups.filter(name="National Office").exists()


def is_national_or_superuser(user):
    """
    Allow access to national pages for:
    - Superuser (true backend admin)
    - National Office group users (national officers)
    """
    if not user.is_authenticated:
        return False
    return user.is_superuser or is_national_officer(user)


def _render(request, template_name, context=None):
    """
    Always inject role flags into templates so navbar logic is simple and safe.
    """
    if context is None:
        context = {}
    context["is_national"] = is_national_officer(request.user)
    context["is_national_access"] = is_national_or_superuser(request.user)
    return render(request, template_name, context)


def map_view(request):
    territory = request.GET.get("territory", "")
    cluster = request.GET.get("cluster", "")

    centers = ProjectCenter.objects.all()

    if territory:
        centers = centers.filter(territory=territory)

    if cluster:
        centers = centers.filter(cluster=cluster)

    territories = (
        ProjectCenter.objects.order_by("territory")
        .values_list("territory", flat=True)
        .distinct()
    )

    clusters = []
    if territory:
        clusters = (
            ProjectCenter.objects.filter(territory=territory)
            .order_by("cluster")
            .values_list("cluster", flat=True)
            .distinct()
        )

    context = {
        "centers": centers,
        "territories": territories,
        "clusters": clusters,
        "selected_territory": territory,
        "selected_cluster": cluster,
    }

    return _render(request, "centers/map.html", context)


def _get_user_center(user):
    try:
        return UserProfile.objects.get(user=user).project_center
    except UserProfile.DoesNotExist:
        return None


@login_required
def participant_list(request):
    center = _get_user_center(request.user)

    if center is None:
        if request.user.is_superuser:
            return redirect("/admin/")

        if is_national_officer(request.user):
            return redirect("national_dashboard")

        return HttpResponseForbidden(
            "Your account is not linked to any Project Center. Contact the admin."
        )

    participants = Participant.objects.filter(project_center=center).order_by("participant_name")

    total_count = participants.count()
    male_count = participants.filter(sex="M").count()
    female_count = participants.filter(sex="F").count()

    return _render(
        request,
        "centers/participants_list.html",
        {
            "participants": participants,
            "center": center,
            "total_count": total_count,
            "male_count": male_count,
            "female_count": female_count,
        },
    )


@login_required
def participant_add(request):
    if is_national_officer(request.user) and not request.user.is_superuser:
        return redirect("national_dashboard")

    center = _get_user_center(request.user)

    if center is None:
        if request.user.is_superuser:
            return redirect("/admin/")
        return HttpResponseForbidden(
            "Your account is not linked to any Project Center. Contact the admin."
        )

    if request.method == "POST":
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.project_center = center
            participant.save()

            _log_action(
                user=request.user,
                action="CREATE",
                project_center=center,
                participant_id=participant.participant_id,
                details=f"Created participant: {participant.participant_name}",
            )

            messages.success(request, "Participant saved successfully.")
            return redirect("participant_list")
    else:
        form = ParticipantForm()

    return _render(
        request,
        "centers/participant_form.html",
        {"form": form, "center": center},
    )


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


@login_required
def participant_map(request):
    if is_national_officer(request.user) and not request.user.is_superuser:
        return redirect("national_dashboard")

    center = _get_user_center(request.user)

    if center is None:
        if request.user.is_superuser:
            return redirect("/admin/")
        return HttpResponseForbidden(
            "Your account is not linked to any Project Center. Contact the admin."
        )

    participants = Participant.objects.filter(project_center=center).order_by("participant_name")

    participants_data = [
        {
            "participant_name": p.participant_name,
            "participant_id": p.participant_id,
            "caregiver_name": p.caregiver_name,
            "house_latitude": str(p.house_latitude),
            "house_longitude": str(p.house_longitude),
        }
        for p in participants
    ]

    context = {
        "center": center,
        "participants": participants,
        "participants_json": participants_data,
    }
    return _render(request, "centers/participants_map.html", context)


@login_required
def participant_edit(request, pk):
    if request.user.is_superuser:
        return redirect("/admin/")
    if is_national_officer(request.user):
        return redirect("national_dashboard")

    center = _get_user_center(request.user)
    if center is None:
        return HttpResponseForbidden("You are not assigned to a Project Center.")

    participant = get_object_or_404(Participant, pk=pk, project_center=center)
    old_name = participant.participant_name
    old_caregiver = participant.caregiver_name
    old_sex = participant.sex
    old_lat = str(participant.house_latitude)
    old_lng = str(participant.house_longitude)

    if request.method == "POST":
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.project_center = center
            obj.save()

            details = (
                f"Updated participant {participant.participant_id}. "
                f"Old: name={old_name}, sex={old_sex}, caregiver={old_caregiver}, lat={old_lat}, lng={old_lng}. "
                f"New: name={obj.participant_name}, sex={obj.sex}, caregiver={obj.caregiver_name}, "
                f"lat={obj.house_latitude}, lng={obj.house_longitude}."
            )
            _log_action(
                user=request.user,
                action="UPDATE",
                project_center=center,
                participant_id=obj.participant_id,
                details=details,
            )

            messages.success(request, "Participant updated successfully.")
            return redirect("participant_list")
    else:
        form = ParticipantForm(instance=participant)

    return _render(
        request,
        "centers/participant_form.html",
        {"form": form, "mode": "edit", "center": center},
    )


@login_required
def participant_delete(request, pk):
    if request.user.is_superuser:
        return redirect("/admin/")
    if is_national_officer(request.user):
        return redirect("national_dashboard")

    center = _get_user_center(request.user)
    if center is None:
        return HttpResponseForbidden("You are not assigned to a Project Center.")

    participant = get_object_or_404(Participant, pk=pk, project_center=center)

    if request.method == "POST":
        pid = participant.participant_id
        pname = participant.participant_name

        _log_action(
            user=request.user,
            action="DELETE",
            project_center=center,
            participant_id=pid,
            details=f"Deleted participant: {pname}",
        )

        participant.delete()
        messages.success(request, f"Deleted participant: {pname}")
        return redirect("participant_list")

    return _render(
        request,
        "centers/participant_confirm_delete.html",
        {"participant": participant, "center": center},
    )


@login_required
def participant_upload(request):
    if not is_national_or_superuser(request.user):
        return HttpResponseForbidden("Only National Office can upload participants.")

    SESSION_KEY = "participants_upload_preview_rows"

    def parse_csv(file_obj):
        decoded = file_obj.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        required_cols = [
            "center_code",
            "participant_name",
            "participant_id",
            "sex",
            "caregiver_name",
            "house_latitude",
            "house_longitude",
        ]

        if not reader.fieldnames:
            raise ValueError("CSV has no headers.")

        headers = [h.strip() for h in reader.fieldnames]
        missing = [c for c in required_cols if c not in headers]
        if missing:
            raise ValueError("Missing columns: " + ", ".join(missing))

        rows = []
        for idx, row in enumerate(reader, start=2):
            r = {
                "row_number": idx,
                "center_code": (row.get("center_code") or "").strip(),
                "participant_name": (row.get("participant_name") or "").strip(),
                "participant_id": (row.get("participant_id") or "").strip(),
                "sex": (row.get("sex") or "").strip().upper(),
                "caregiver_name": (row.get("caregiver_name") or "").strip(),
                "house_latitude": (row.get("house_latitude") or "").strip(),
                "house_longitude": (row.get("house_longitude") or "").strip(),
                "is_valid": True,
                "error": "",
            }

            try:
                if not r["center_code"]:
                    raise ValueError("center_code is empty")

                center = ProjectCenter.objects.get(center_code=r["center_code"])

                if not r["participant_id"]:
                    raise ValueError("participant_id is empty")

                if Participant.objects.filter(participant_id=r["participant_id"]).exists():
                    raise ValueError("participant_id already exists")

                p = Participant(
                    project_center=center,
                    participant_name=r["participant_name"],
                    participant_id=r["participant_id"],
                    sex=r["sex"],
                    caregiver_name=r["caregiver_name"],
                    house_latitude=r["house_latitude"],
                    house_longitude=r["house_longitude"],
                )
                p.full_clean()

            except Exception as e:
                r["is_valid"] = False
                r["error"] = str(e)

            rows.append(r)

        return rows

    if request.method == "POST" and request.POST.get("confirm_import") == "1":
        rows = request.session.get(SESSION_KEY)

        if not rows:
            messages.error(request, "No preview data found. Please upload again to preview.")
            return redirect("participant_upload")

        created = 0
        skipped = 0
        errors = []
        created_centers = set()

        for r in rows:
            if not r.get("is_valid"):
                skipped += 1
                continue

            try:
                center = ProjectCenter.objects.get(center_code=r["center_code"])

                if Participant.objects.filter(participant_id=r["participant_id"]).exists():
                    skipped += 1
                    continue

                p = Participant(
                    project_center=center,
                    participant_name=r["participant_name"],
                    participant_id=r["participant_id"],
                    sex=r["sex"],
                    caregiver_name=r["caregiver_name"],
                    house_latitude=r["house_latitude"],
                    house_longitude=r["house_longitude"],
                )
                p.full_clean()
                p.save()
                created += 1
                created_centers.add(center.center_code)

            except Exception as e:
                skipped += 1
                errors.append(f"Row {r.get('row_number')}: {e}")

        _log_action(
            user=request.user,
            action="CSV_IMPORT",
            project_center=None,
            participant_id=None,
            details=f"CSV import completed. Created={created}, Skipped={skipped}, Centers={sorted(created_centers)}",
        )

        request.session.pop(SESSION_KEY, None)

        if created > 0:
            messages.success(request, f"Import complete. Created: {created}, Skipped: {skipped}")
        else:
            messages.warning(request, f"Import complete. Created: {created}, Skipped: {skipped}")

        return _render(
            request,
            "centers/participant_upload.html",
            {
                "form": ParticipantUploadForm(),
                "errors": errors[:50],
            },
        )

    if request.method == "POST":
        form = ParticipantUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                rows = parse_csv(csv_file)
            except Exception as e:
                messages.error(request, str(e))
                return _render(request, "centers/participant_upload.html", {"form": form})

            request.session[SESSION_KEY] = rows

            total = len(rows)
            valid = sum(1 for r in rows if r["is_valid"])
            invalid = total - valid

            preview_rows = rows[:100]

            return _render(
                request,
                "centers/participant_upload.html",
                {
                    "form": ParticipantUploadForm(),
                    "preview_rows": preview_rows,
                    "preview_summary": {"total": total, "valid": valid, "invalid": invalid},
                },
            )

    request.session.pop(SESSION_KEY, None)
    form = ParticipantUploadForm()
    return _render(request, "centers/participant_upload.html", {"form": form})


@login_required
def participants_csv_template(request):
    if not is_national_or_superuser(request.user):
        return HttpResponseForbidden("Only National Office can download the template.")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="participants_template.csv"'

    writer = csv.writer(response)

    writer.writerow(
        [
            "center_code",
            "participant_name",
            "participant_id",
            "sex",
            "caregiver_name",
            "house_latitude",
            "house_longitude",
        ]
    )

    writer.writerow(
        [
            "MD1111",
            "John Doe",
            "MD1111-001",
            "M",
            "Jane Doe",
            "39.2904",
            "-76.6122",
        ]
    )

    return response


@login_required
@user_passes_test(is_national_or_superuser)
def national_centers_map(request):
    centers = ProjectCenter.objects.all()
    return _render(request, "centers/national_centers_map.html", {"centers": centers})


@login_required
@user_passes_test(is_national_or_superuser)
def national_dashboard(request):
    now = timezone.now()
    days_7 = now - timedelta(days=7)
    days_30 = now - timedelta(days=30)

    total_centers = ProjectCenter.objects.count()
    total_participants = Participant.objects.count()

    logs_last_7 = AuditLog.objects.filter(timestamp__gte=days_7).count()
    logs_last_30 = AuditLog.objects.filter(timestamp__gte=days_30).count()

    deletes_last_30 = AuditLog.objects.filter(timestamp__gte=days_30, action="DELETE").count()
    csv_imports_last_30 = AuditLog.objects.filter(timestamp__gte=days_30, action="CSV_IMPORT").count()

    by_territory_qs = (
        Participant.objects.select_related("project_center")
        .values("project_center__territory")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    territory_labels = [(r["project_center__territory"] or "Unknown") for r in by_territory_qs]
    territory_values = [r["total"] for r in by_territory_qs]

    by_sex_qs = Participant.objects.values("sex").annotate(total=Count("id")).order_by("sex")
    sex_labels = []
    sex_values = []
    for r in by_sex_qs:
        label = r["sex"] or "Unknown"
        if label == "M":
            label = "Male"
        elif label == "F":
            label = "Female"
        sex_labels.append(label)
        sex_values.append(r["total"])

    logs_by_day_qs = (
        AuditLog.objects.filter(timestamp__gte=days_30)
        .annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    logs_by_day_map = {str(r["day"]): r["total"] for r in logs_by_day_qs}

    date_labels = []
    date_values = []
    for i in range(30, -1, -1):
        d = (now - timedelta(days=i)).date()
        key = str(d)
        date_labels.append(key)
        date_values.append(int(logs_by_day_map.get(key, 0)))

    actions_qs = (
        AuditLog.objects.filter(timestamp__gte=days_30)
        .values("action")
        .annotate(total=Count("id"))
        .order_by("action")
    )
    action_labels = [r["action"] for r in actions_qs]
    action_values = [r["total"] for r in actions_qs]

    top_centers = (
        AuditLog.objects.filter(timestamp__gte=days_30)
        .values("project_center__center_code", "project_center__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    top_users = (
        AuditLog.objects.filter(timestamp__gte=days_30)
        .values("user__username", "user__email")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    recent_logs = AuditLog.objects.select_related("user", "project_center").order_by("-timestamp")[:20]

    context = {
        "total_centers": total_centers,
        "total_participants": total_participants,
        "logs_last_7": logs_last_7,
        "logs_last_30": logs_last_30,
        "deletes_last_30": deletes_last_30,
        "csv_imports_last_30": csv_imports_last_30,
        "territory_labels": territory_labels,
        "territory_values": territory_values,
        "sex_labels": sex_labels,
        "sex_values": sex_values,
        "date_labels": date_labels,
        "date_values": date_values,
        "action_labels": action_labels,
        "action_values": action_values,
        "top_centers": top_centers,
        "top_users": top_users,
        "recent_logs": recent_logs,
        "now": now,
    }

    return _render(request, "centers/national_dashboard.html", context)