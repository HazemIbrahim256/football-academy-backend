from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Coach, Group, Player, PlayerEvaluation


class PermissionsTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True, is_superuser=True)

        self.coach_user1 = User.objects.create_user(username="coach1", password="coach123")
        self.coach1 = Coach.objects.create(user=self.coach_user1, bio="Coach 1")
        self.group1 = Group.objects.create(name="Group A", description="A", coach=self.coach1)

        self.coach_user2 = User.objects.create_user(username="coach2", password="coach123")
        self.coach2 = Coach.objects.create(user=self.coach_user2, bio="Coach 2")
        self.group2 = Group.objects.create(name="Group B", description="B", coach=self.coach2)

        self.p1 = Player.objects.create(group=self.group1, name="Alice", age=13, position="FW")
        self.p2 = Player.objects.create(group=self.group2, name="Bob", age=14, position="DF")

        self.client = APIClient()

    def test_admin_can_access_all_groups(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/groups/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_coach_sees_only_own_group(self):
        self.client.force_authenticate(user=self.coach_user1)
        res = self.client.get("/api/groups/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Group A")

    def test_coach_can_create_player_in_own_group(self):
        self.client.force_authenticate(user=self.coach_user1)
        payload = {"group": self.group1.id, "name": "Charlie", "age": 12, "position": "MF"}
        res = self.client.post("/api/players/", payload, format="json")
        self.assertEqual(res.status_code, 201)

    def test_coach_cannot_create_player_in_other_group(self):
        self.client.force_authenticate(user=self.coach_user1)
        payload = {"group": self.group2.id, "name": "Eve", "age": 12, "position": "MF"}
        res = self.client.post("/api/players/", payload, format="json")
        self.assertEqual(res.status_code, 403)

    def test_coach_can_create_evaluation_for_own_player(self):
        self.client.force_authenticate(user=self.coach_user1)
        payload = {
            "player": self.p1.id,
            "dribbling": 4,
            "passing": 4,
            "shooting": 4,
            "defense": 4,
            "speed": 4,
            "teamwork": 4,
            "notes": "Solid week",
        }
        res = self.client.post("/api/evaluations/", payload, format="json")
        self.assertEqual(res.status_code, 201)

    def test_coach_cannot_create_evaluation_for_other_group_player(self):
        self.client.force_authenticate(user=self.coach_user1)
        payload = {
            "player": self.p2.id,
            "dribbling": 4,
            "passing": 4,
            "shooting": 4,
            "defense": 4,
            "speed": 4,
            "teamwork": 4,
            "notes": "Test",
        }
        res = self.client.post("/api/evaluations/", payload, format="json")
        self.assertEqual(res.status_code, 403)