from django.db import models
from django.utils import timezone

# Use Django's JSONField (works with PostgreSQL and other backends)
try:
    # Django 3.1+
    from django.db.models import JSONField
except ImportError:
    # older Django: fallback
    from django.contrib.postgres.fields import JSONField


class Proposal(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
        ("Unknown", "Unknown"),
    ]

    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    proposal_data = JSONField(blank=True, null=True)
    response_data = JSONField(blank=True, null=True)
    underwriting_decision = models.CharField(max_length=255, blank=True, null=True)
    identified_health_profile = JSONField(blank=True, null=True)
    decision_rationale = models.TextField(blank=True, null=True)

    waiting_period_details = JSONField(blank=True, null=True)
    refer_to_uwr_details = JSONField(blank=True, null=True)
    more_questions_details = JSONField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Proposal #{self.pk} (age={self.age}, gender={self.get_gender_display()})"


class Ambiguity(models.Model):
    proposal = models.ForeignKey(
        Proposal, related_name="ambiguities", on_delete=models.CASCADE
    )
    ambiguity_proposal_data = JSONField(blank=True, null=True)
    ambiguity_response = JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Ambiguity #{self.pk} for Proposal #{self.proposal_id}"


class Discrepancy(models.Model):
    proposal = models.ForeignKey(
        Proposal, related_name="discrepancies", on_delete=models.CASCADE
    )
    discrepancy_proposal_data = JSONField(blank=True, null=True)
    discrepancy_response = JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Discrepancy #{self.pk} for Proposal #{self.proposal_id}"


class Uwquestions(models.Model):
    proposal = models.ForeignKey(
        Proposal, related_name="uwquestions", on_delete=models.CASCADE
    )
    answers = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Uwquestion #{self.pk} for Proposal #{self.proposal_id}"
