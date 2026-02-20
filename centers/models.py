from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class ProjectCenter(models.Model):
    name = models.CharField(max_length=200)
    center_code = models.CharField(max_length=50, unique=True)

    territory = models.CharField(max_length=100)
    cluster = models.CharField(max_length=100)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    beneficiaries = models.PositiveIntegerField()
    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.center_code})"


class Participant(models.Model):
    SEX_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    project_center = models.ForeignKey(
        ProjectCenter,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    participant_name = models.CharField(max_length=200)
    participant_id = models.CharField(max_length=50, unique=True)

    sex = models.CharField(max_length=1, choices=SEX_CHOICES)

    caregiver_name = models.CharField(max_length=200)

    house_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    house_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project_center"]),
            models.Index(fields=["participant_id"]),
            models.Index(fields=["project_center", "participant_id"]),
        ]

    def __str__(self):
        return f"{self.participant_name} ({self.participant_id})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    project_center = models.ForeignKey(ProjectCenter, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.project_center.name}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("CSV_IMPORT", "CSV Import"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    project_center = models.ForeignKey(
        ProjectCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    participant_id = models.CharField(max_length=50, null=True, blank=True)

    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"