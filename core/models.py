from django.conf import settings
from datetime import date
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Coach(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="coach_profile")
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="coach_photos/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    coach = models.ForeignKey(Coach, on_delete=models.PROTECT, related_name="groups", null=True, blank=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="player_photos/", blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField()
    phone = models.CharField(max_length=20, blank=True)
    attendance_days = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-calculate age from birth_date if provided
        if self.birth_date:
            today = date.today()
            self.age = today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        super().save(*args, **kwargs)


class PlayerEvaluation(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="evaluation")
    coach = models.ForeignKey(Coach, on_delete=models.PROTECT, related_name="evaluations")

    # Technical Skills
    ball_control = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    passing = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    dribbling = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    shooting = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    using_both_feet = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Physical Abilities
    speed = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    agility = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    endurance = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    strength = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Technical Understanding
    positioning = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    decision_making = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    game_awareness = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    teamwork = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Psychological and Social
    respect = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    sportsmanship = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    confidence = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    leadership = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    # Overall evaluation
    attendance_and_punctuality = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ensure evaluation coach matches player's group coach
        if self.player and self.coach and self.player.group.coach_id != self.coach_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Coach can only evaluate players in their assigned group.")

    @property
    def average_rating(self) -> float:
        values = [
            v for v in [
                self.ball_control,
                self.passing,
                self.dribbling,
                self.shooting,
                self.using_both_feet,
                self.speed,
                self.agility,
                self.endurance,
                self.strength,
                self.positioning,
                self.decision_making,
                self.game_awareness,
                self.teamwork,
                self.respect,
                self.sportsmanship,
                self.confidence,
                self.leadership,
                # Intentionally exclude attendance_and_punctuality from overall skill average
            ]
            if isinstance(v, int)
        ]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def __str__(self):
        return f"Evaluation: {self.player.name} by {self.coach}"


class PlayerAttendance(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="attendance_records")
    # Month stored as date with day=1
    month = models.DateField()
    days = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("player", "month")
        ordering = ["-month"]

    def __str__(self):
        month_str = self.month.strftime("%Y-%m") if self.month else str(self.month)
        return f"{self.player.name} - {month_str}"