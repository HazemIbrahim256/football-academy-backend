from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Coach, Group, Player, PlayerEvaluation


class PdfReportsTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True, is_superuser=True)
        self.coach_user = User.objects.create_user(username="coach1", password="coach123")
        self.coach = Coach.objects.create(user=self.coach_user, bio="Coach")
        self.group = Group.objects.create(name="Group A", description="A", coach=self.coach)
        self.player = Player.objects.create(group=self.group, name="Alice", age=13, position="FW")
        PlayerEvaluation.objects.create(
            player=self.player,
            coach=self.coach,
            dribbling=4,
            passing=4,
            shooting=5,
            defense=3,
            speed=4,
            teamwork=4,
            notes="Good",
        )
        self.client = APIClient()

    def test_group_pdf_download(self):
        self.client.force_authenticate(user=self.coach_user)
        res = self.client.get(f"/api/groups/{self.group.id}/report-pdf/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content[:4] == b"%PDF")

    def test_player_pdf_download(self):
        self.client.force_authenticate(user=self.coach_user)
        res = self.client.get(f"/api/players/{self.player.id}/report-pdf/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content[:4] == b"%PDF")