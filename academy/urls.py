from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.views import CoachViewSet, GroupViewSet, PlayerViewSet, PlayerEvaluationViewSet, SignupView, MeView, ChangePasswordView

router = routers.DefaultRouter()
router.register(r"coaches", CoachViewSet, basename="coach")
router.register(r"groups", GroupViewSet, basename="group")
router.register(r"players", PlayerViewSet, basename="player")
router.register(r"evaluations", PlayerEvaluationViewSet, basename="evaluation")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/auth/signup/", SignupView.as_view(), name="signup"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)