from django.contrib import admin

from .models import Coach, Group, Player, PlayerEvaluation, PlayerAttendance


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "bio")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "coach")
    search_fields = ("name",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "group", "phone", "age", "attendance_days")
    list_filter = ("group",)
    search_fields = ("name",)


@admin.register(PlayerEvaluation)
class PlayerEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "player",
        "coach",
        "average_rating",
        "attendance_and_punctuality",
        "updated_at",
    )
    list_filter = ("coach",)
    search_fields = ("player__name", "coach__user__username")


@admin.register(PlayerAttendance)
class PlayerAttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "player", "month", "days", "updated_at")
    list_filter = ("month", "player__group")
    search_fields = ("player__name",)