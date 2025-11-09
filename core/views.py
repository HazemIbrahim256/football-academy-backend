from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Coach, Group, Player, PlayerEvaluation
from .serializers import (
    CoachSerializer,
    CoachDetailSerializer,
    GroupSerializer,
    PlayerSerializer,
    PlayerEvaluationSerializer,
    SignupSerializer,
    UserSerializer,
)
from .permissions import IsAdmin, IsAdminOrCoachWriteOwnGroup, IsAdminOrCoachOfObject
from .pdf import build_group_report, build_player_report


class CoachViewSet(viewsets.ModelViewSet):
    queryset = Coach.objects.select_related("user").prefetch_related("groups").all()
    serializer_class = CoachDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=["post"], url_path="create-with-user", permission_classes=[IsAuthenticated, IsAdmin])
    def create_with_user(self, request):
        data = request.data
        required = ["username", "password"]
        for field in required:
            if field not in data:
                return Response({"detail": f"Missing field: {field}"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=data["username"]).exists():
            return Response({"detail": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create(
            username=data["username"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
        )
        user.set_password(data["password"])
        user.save()
        coach = Coach.objects.create(user=user, bio=data.get("bio", ""), phone=data.get("phone", ""))
        return Response(CoachSerializer(coach).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        coach = self.get_object()
        # Prevent deletion if coach is assigned to any group (PROTECT)
        if coach.groups.exists():
            return Response({"detail": "Coach has one or more assigned groups. Reassign or remove those groups first."}, status=status.HTTP_400_BAD_REQUEST)
        user = coach.user
        response = super().destroy(request, *args, **kwargs)
        # Also remove the associated user account
        try:
            user.delete()
        except Exception:
            pass
        return response


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCoachWriteOwnGroup]
    filterset_fields = ["name", "coach"]
    ordering_fields = ["name", "id"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Group.objects.select_related("coach__user").prefetch_related("players").all()
        coach = getattr(user, "coach_profile", None)
        if coach:
            return Group.objects.filter(coach=coach).select_related("coach__user").prefetch_related("players")
        return Group.objects.none()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        month = self.request.query_params.get("month")
        if month:
            ctx["attendance_month"] = month
        return ctx

    @action(detail=True, methods=["get"], url_path="report-pdf")
    def report_pdf(self, request, pk=None):
        group = self.get_object()
        # object-level permission
        self.check_object_permissions(request, group)
        pdf_bytes = build_group_report(group)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="group_{group.id}_report.pdf"'
        return response

    @action(detail=True, methods=["post"], url_path="reset-evaluations")
    def reset_evaluations(self, request, pk=None):
        """Reset all player evaluations in this group to null values.

        Admins can reset any group; coaches can reset only their own group.
        """
        group = self.get_object()
        # Ensure caller has object-level permission on this group
        self.check_object_permissions(request, group)

        qs = PlayerEvaluation.objects.filter(player__group=group)
        updated = qs.update(
            # Technical Skills
            ball_control=None,
            passing=None,
            dribbling=None,
            shooting=None,
            using_both_feet=None,
            # Physical Abilities
            speed=None,
            agility=None,
            endurance=None,
            strength=None,
            # Technical Understanding
            positioning=None,
            decision_making=None,
            game_awareness=None,
            teamwork=None,
            # Psychological and Social
            respect=None,
            sportsmanship=None,
            confidence=None,
            leadership=None,
            # Overall evaluation
            attendance_and_punctuality=None,
        )
        return Response({"detail": f"Reset evaluations for {updated} player(s).", "updated": updated}, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff:
            coach = None
            coach_id = self.request.data.get("coach_id")
            if coach_id:
                try:
                    coach = Coach.objects.get(id=coach_id)
                except Coach.DoesNotExist:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("Invalid coach_id")
            else:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("coach_id is required for group creation.")
            serializer.save(coach=coach)
            return
        # coach creating their own group (coaches may own multiple groups)
        coach = getattr(user, "coach_profile", None)
        if not coach:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only coaches or admins can create groups.")
        serializer.save(coach=coach)


class PlayerViewSet(viewsets.ModelViewSet):
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCoachWriteOwnGroup]
    filterset_fields = ["group", "age"]
    ordering_fields = ["name", "age", "id"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Player.objects.select_related("group__coach__user", "evaluation").all()
        coach = getattr(user, "coach_profile", None)
        if coach:
            return Player.objects.filter(group__coach=coach).select_related("group__coach__user", "evaluation")
        return Player.objects.none()

    def destroy(self, request, *args, **kwargs):
        """Override destroy to avoid queryset-based object lookup causing false 404s.

        We fetch the Player by primary key directly, then enforce object-level
        permissions explicitly. This prevents scenarios where a valid player
        becomes invisible to the request's filtered queryset, resulting in a 404
        even for authorized users (e.g., admins).
        """
        pk = kwargs.get(self.lookup_field or "pk")
        try:
            player = Player.objects.select_related("group__coach").get(pk=pk)
        except Player.DoesNotExist:
            return Response({"detail": "No Player matches the given query."}, status=status.HTTP_404_NOT_FOUND)

        # Enforce object-level permissions (admin or coach of the player's group)
        self.check_object_permissions(request, player)

        player.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        # Coaches can only create players within their group
        user = self.request.user
        if user.is_staff:
            serializer.save()
            return
        coach = getattr(user, "coach_profile", None)
        group = serializer.validated_data.get("group")
        if not coach or not group or group.coach_id != coach.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Coaches can only add players to their own group.")
        serializer.save()

    @action(detail=True, methods=["get"], url_path="report-pdf")
    def report_pdf(self, request, pk=None):
        player = self.get_object()
        self.check_object_permissions(request, player)
        pdf_bytes = build_player_report(player)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="player_{player.id}_report.pdf"'
        return response


class PlayerEvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = PlayerEvaluationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrCoachWriteOwnGroup]
    filterset_fields = ["player", "coach"]
    ordering_fields = ["updated_at", "id"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return PlayerEvaluation.objects.select_related("player__group__coach__user", "coach").all()
        coach = getattr(user, "coach_profile", None)
        if coach:
            return PlayerEvaluation.objects.filter(player__group__coach=coach).select_related("player__group__coach__user", "coach")
        return PlayerEvaluation.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff:
            serializer.save()
            return
        coach = getattr(user, "coach_profile", None)
        player = serializer.validated_data.get("player")
        if not coach or not player or player.group.coach_id != coach.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Coaches can only evaluate players in their assigned group.")
        serializer.save(coach=coach)

    def perform_update(self, serializer):
        # Maintain coach association for updates
        instance = serializer.instance
        user = self.request.user
        if user.is_staff:
            serializer.save()
            return
        coach = getattr(user, "coach_profile", None)
        if not coach or instance.player.group.coach_id != coach.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Coaches can only update evaluations within their group.")
        serializer.save(coach=coach)

    @action(detail=True, methods=["get", "put", "patch"], url_path="attendance")
    def attendance(self, request, pk=None):
        """Get or set monthly attendance for a player.

        Use query param 'month' in 'YYYY-MM' format and body {"days": <int>} for updates.
        """
        player = self.get_object()
        self.check_object_permissions(request, player)
        month_str = request.query_params.get("month")
        if not month_str:
            return Response({"detail": "month is required (YYYY-MM)"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            year, month = [int(x) for x in month_str.split("-")]
            from datetime import date
            month_date = date(year, month, 1)
        except Exception:
            return Response({"detail": "Invalid month format; expected YYYY-MM"}, status=status.HTTP_400_BAD_REQUEST)

        from .models import PlayerAttendance
        rec, _ = PlayerAttendance.objects.get_or_create(player=player, month=month_date)

        if request.method in ("PUT", "PATCH"):
            days = request.data.get("days")
            if days is None:
                return Response({"detail": "days is required"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                days = int(days)
            except Exception:
                return Response({"detail": "days must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            if days < 0 or days > 365:
                return Response({"detail": "days must be between 0 and 365"}, status=status.HTTP_400_BAD_REQUEST)
            rec.days = days
            rec.save()

        return Response({"player": player.id, "month": month_str, "days": rec.days}, status=status.HTTP_200_OK)


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create(
            username=data["username"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
        )
        user.set_password(data["password"])
        user.save()
        coach = Coach.objects.create(user=user, bio=data.get("bio", ""), phone=data.get("phone", ""))
        return Response(CoachSerializer(coach).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = request.user
        coach = getattr(user, "coach_profile", None)
        payload = {
            "user": UserSerializer(user).data,
            "coach": CoachSerializer(coach).data if coach else None,
            "is_staff": bool(user.is_staff),
        }
        return Response(payload, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        coach = getattr(user, "coach_profile", None)
        data = request.data

        # Update basic user fields
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        changed = False
        if first_name is not None:
            user.first_name = first_name
            changed = True
        if last_name is not None:
            user.last_name = last_name
            changed = True
        if email is not None:
            user.email = email
            changed = True
        if changed:
            user.save()

        # Update or create coach profile when coach-related fields are provided
        bio = data.get("bio")
        phone = data.get("phone")
        photo_file = request.FILES.get("photo")

        if coach is None and (bio is not None or phone is not None or photo_file is not None):
            coach = Coach.objects.create(user=user)

        if coach is not None:
            if bio is not None:
                coach.bio = bio
            if phone is not None:
                coach.phone = phone
            if photo_file:
                coach.photo = photo_file
            coach.save()

        return Response({
            "user": UserSerializer(user).data,
            "coach": CoachSerializer(coach).data if coach else None,
            "is_staff": bool(user.is_staff),
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            return Response({"detail": "old_password and new_password are required."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.check_password(old_password):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 6:
            return Response({"detail": "New password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

        payload = {
            "user": UserSerializer(user).data,
            "coach": CoachSerializer(coach).data if coach else None,
            "is_staff": bool(user.is_staff),
        }
        return Response(payload, status=status.HTTP_200_OK)