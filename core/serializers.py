from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Coach, Group, Player, PlayerEvaluation, PlayerAttendance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_staff"]


class CoachSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Coach
        fields = ["id", "user", "bio", "photo", "phone"]


class CoachDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = Coach
        fields = ["id", "user", "bio", "photo", "phone", "groups"]

    def get_groups(self, obj):
        qs = getattr(obj, "groups", None)
        if qs is None:
            return []
        return [{"id": g.id, "name": g.name} for g in qs.all()]


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value


class PlayerEvaluationSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    coach = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PlayerEvaluation
        fields = [
            "id",
            "player",
            "coach",
            # Technical Skills
            "ball_control",
            "passing",
            "dribbling",
            "shooting",
            "using_both_feet",
            # Physical Abilities
            "speed",
            "agility",
            "endurance",
            "strength",
            # Technical Understanding
            "positioning",
            "decision_making",
            "game_awareness",
            "teamwork",
            # Psychological and Social
            "respect",
            "sportsmanship",
            "confidence",
            "leadership",
            # Overall evaluation
            "attendance_and_punctuality",
            "notes",
            "updated_at",
            "average_rating",
        ]
        read_only_fields = ["updated_at", "average_rating", "coach"]

    def validate(self, attrs):
        # Ensure the evaluation's coach matches the player's group coach
        player = attrs.get("player") or getattr(self.instance, "player", None)
        coach = attrs.get("coach") or getattr(self.instance, "coach", None)
        if player and coach and player.group.coach_id != coach.id:
            raise serializers.ValidationError("Coach can only evaluate players within their assigned group.")
        return attrs


class PlayerSerializer(serializers.ModelSerializer):
    evaluation = PlayerEvaluationSerializer(read_only=True)
    attendance_days = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            "id",
            "group",
            "name",
            "photo",
            "birth_date",
            "age",
            "phone",
            "attendance_days",
            "evaluation",
        ]
        extra_kwargs = {"age": {"read_only": True}}

    def get_attendance_days(self, obj):
        month_str = self.context.get("attendance_month")
        if month_str:
            try:
                year, month = [int(x) for x in month_str.split("-")]
                from datetime import date
                month_date = date(year, month, 1)
                rec = PlayerAttendance.objects.filter(player=obj, month=month_date).first()
                if rec:
                    return rec.days
            except Exception:
                pass
        return obj.attendance_days


class GroupSerializer(serializers.ModelSerializer):
    coach = CoachSerializer(read_only=True)
    coach_id = serializers.PrimaryKeyRelatedField(
        queryset=Coach.objects.all(), source="coach", write_only=True, required=False, allow_null=True
    )
    players = PlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "description", "coach", "coach_id", "players"]