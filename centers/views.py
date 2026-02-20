import csv
import io

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods

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

    return render(request, "centers/map.html", context)


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
        return HttpResponseForbidden(
            "Your account is not linked to any Project Center. Contact the admin."
        )

    participants = Participant.objects.filter(project_center=center).order_by(
        "participant_name"
    )

    total_count = participants.count()
    male_count = participants.filter(sex="M").count()
    female_count = participants.filter(sex="F").count()

    return render(
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

    return render(
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
    center = _get_user_center(request.user)

    if center is None:
        if request.user.is_superuser:
            return redirect("/admin/")
        return HttpResponseForbidden(
            "Your account is not linked to any Project Center. Contact the admin."
        )

    participants = Participant.objects.filter(project_center=center).order_by(
        "participant_name"
    )

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
    return render(request, "centers/participants_map.html", context)


@login_required
def participant_edit(request, pk):
    if request.user.is_superuser:
        return redirect("/admin/")

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

    return render(
        request,
        "centers/participant_form.html",
        {"form": form, "mode": "edit", "center": center},
    )


@login_required
def participant_delete(request, pk):
    if request.user.is_superuser:
        return redirect("/admin/")

    center = _get_user_center(request.user)
    if center is None:
        return HttpResponseForbidden("You are not assigned to a Project Center.")

    participant = get_object_or_404(Participant, pk=pk, project_center=center)

    if request.method == "POST":
        pid = participant.participant_id
        pname = participant.participant_name

        # Log BEFORE deleting so we never lose reference details
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

    return render(
        request,
        "centers/participant_confirm_delete.html",
        {"participant": participant, "center": center},
    )


@login_required
def participant_upload(request):
    if not request.user.is_superuser:
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

    # CONFIRM IMPORT
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

        # Log the import summary (one log record per import)
        _log_action(
            user=request.user,
            action="CSV_IMPORT",
            project_center=None,
            participant_id=None,
            details=f"CSV import completed. Created={created}, Skipped={skipped}, Centers={sorted(created_centers)}",
        )

        # clear preview after import attempt
        request.session.pop(SESSION_KEY, None)

        if created > 0:
            messages.success(request, f"Import complete. Created: {created}, Skipped: {skipped}")
        else:
            messages.warning(request, f"Import complete. Created: {created}, Skipped: {skipped}")

        return render(
            request,
            "centers/participant_upload.html",
            {
                "form": ParticipantUploadForm(),
                "errors": errors[:50],
            },
        )

    # PREVIEW
    if request.method == "POST":
        form = ParticipantUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                rows = parse_csv(csv_file)
            except Exception as e:
                messages.error(request, str(e))
                return render(request, "centers/participant_upload.html", {"form": form})

            request.session[SESSION_KEY] = rows

            total = len(rows)
            valid = sum(1 for r in rows if r["is_valid"])
            invalid = total - valid

            preview_rows = rows[:100]

            return render(
                request,
                "centers/participant_upload.html",
                {
                    "form": ParticipantUploadForm(),
                    "preview_rows": preview_rows,
                    "preview_summary": {"total": total, "valid": valid, "invalid": invalid},
                },
            )

    # GET
    request.session.pop(SESSION_KEY, None)
    form = ParticipantUploadForm()
    return render(request, "centers/participant_upload.html", {"form": form})


@login_required
def participants_csv_template(request):
    if not request.user.is_superuser:
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


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def national_centers_map(request):
    centers = ProjectCenter.objects.all()
    return render(request, "centers/national_centers_map.html", {"centers": centers})