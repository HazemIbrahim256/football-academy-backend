from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Coach, Group, Player


class FilteringOrderingTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True, is_superuser=True)
        self.coach_user = User.objects.create_user(username="coach1", password="coach123")
        self.coach = Coach.objects.create(user=self.coach_user, bio="Coach")
        self.group = Group.objects.create(name="Group A", description="A", coach=self.coach)
        Player.objects.create(group=self.group, name="Alice", age=13, position="FW")
        Player.objects.create(group=self.group, name="Bob", age=14, position="DF")
        Player.objects.create(group=self.group, name="Charlie", age=12, position="MF")

        self.client = APIClient()
        self.client.force_authenticate(user=self.coach_user)

    def test_filter_by_position(self):
        res = self.client.get("/api/players/?position=DF")
        self.assertEqual(res.status_code, 200)
        names = [p["name"] for p in res.data]
        self.assertEqual(names, ["Bob"])  # only defender

    def test_order_by_age(self):
        res = self.client.get("/api/players/?ordering=age")
        self.assertEqual(res.status_code, 200)
        ages = [p["age"] for p in res.data]
        self.assertEqual(ages, sorted(ages))