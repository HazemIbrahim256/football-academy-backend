from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core.models import Coach, Group, Player, PlayerEvaluation


class Command(BaseCommand):
    help = "Seed sample data: admin, coach, group, players, evaluations"

    def handle(self, *args, **options):
        admin_username = "admin"
        admin_password = "admin123"
        coach_username = "coach1"
        coach_password = "coach123"

        # Admin user
        admin, created = User.objects.get_or_create(username=admin_username, defaults={
            "first_name": "Admin",
            "last_name": "User",
            "email": "admin@example.com",
            "is_staff": True,
            "is_superuser": True,
        })
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user '{admin_username}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Admin user '{admin_username}' already exists"))

        # Coach user and profile
        coach_user, created = User.objects.get_or_create(username=coach_username, defaults={
            "first_name": "Alex",
            "last_name": "Coach",
            "email": "coach1@example.com",
        })
        if created:
            coach_user.set_password(coach_password)
            coach_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created coach user '{coach_username}'"))
        else:
            self.stdout.write(self.style.WARNING(f"Coach user '{coach_username}' already exists"))

        coach, _ = Coach.objects.get_or_create(user=coach_user, defaults={
            "bio": "UEFA B Licensed coach with a focus on youth development.",
        })

        # Group
        group, _ = Group.objects.get_or_create(
            name="U14 - Falcons",
            defaults={
                "description": "Under-14 development squad",
                "coach": coach,
            },
        )
        # Ensure one-to-one assignment
        if group.coach_id != coach.id:
            group.coach = coach
            group.save()

        # Players
        players_data = [
            {"name": "John Doe", "age": 14, "phone": "555-0101"},
            {"name": "Liam Smith", "age": 13, "phone": "555-0102"},
            {"name": "Noah Brown", "age": 14, "phone": "555-0103"},
            {"name": "Mason Clark", "age": 12, "phone": "555-0104"},
        ]
        players = []
        for pdata in players_data:
            p, _ = Player.objects.get_or_create(name=pdata["name"], group=group, defaults=pdata)
            players.append(p)

        # Evaluations
        ratings = [
            {
                # Technical Skills
                "ball_control": 4,
                "passing": 4,
                "dribbling": 4,
                "shooting": 5,
                "using_both_feet": 4,
                # Physical Abilities
                "speed": 4,
                "agility": 4,
                "endurance": 3,
                "strength": 3,
                # Technical Understanding
                "positioning": 3,
                "decision_making": 4,
                "game_awareness": 4,
                "teamwork": 4,
                # Psychological and Social
                "respect": 4,
                "sportsmanship": 5,
                "confidence": 4,
                "leadership": 3,
                # Overall
                "attendance_and_punctuality": 4,
            },
            {
                "ball_control": 3,
                "passing": 5,
                "dribbling": 3,
                "shooting": 3,
                "using_both_feet": 3,
                "speed": 3,
                "agility": 3,
                "endurance": 4,
                "strength": 3,
                "positioning": 3,
                "decision_making": 3,
                "game_awareness": 4,
                "teamwork": 5,
                "respect": 4,
                "sportsmanship": 4,
                "confidence": 3,
                "leadership": 3,
                "attendance_and_punctuality": 5,
            },
            {
                "ball_control": 2,
                "passing": 3,
                "dribbling": 2,
                "shooting": 3,
                "using_both_feet": 2,
                "speed": 3,
                "agility": 3,
                "endurance": 3,
                "strength": 4,
                "positioning": 4,
                "decision_making": 3,
                "game_awareness": 3,
                "teamwork": 4,
                "respect": 4,
                "sportsmanship": 3,
                "confidence": 3,
                "leadership": 3,
                "attendance_and_punctuality": 3,
            },
            {
                "ball_control": 3,
                "passing": 3,
                "dribbling": 3,
                "shooting": 2,
                "using_both_feet": 3,
                "speed": 3,
                "agility": 3,
                "endurance": 3,
                "strength": 3,
                "positioning": 3,
                "decision_making": 3,
                "game_awareness": 3,
                "teamwork": 3,
                "respect": 3,
                "sportsmanship": 3,
                "confidence": 3,
                "leadership": 2,
                "attendance_and_punctuality": 4,
            },
        ]
        for p, r in zip(players, ratings):
            PlayerEvaluation.objects.get_or_create(player=p, defaults={**r, "coach": coach, "notes": "Weekly evaluation."})

        self.stdout.write(self.style.SUCCESS("Seeding complete."))