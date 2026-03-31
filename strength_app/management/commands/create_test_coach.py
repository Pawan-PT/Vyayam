"""
Creates a test coach account linked to TEST001 and TEST002.
Usage: python manage.py create_test_coach
Login: /coach/login/ → username: testcoach  password: testpass123
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from strength_app.models import TherapistProfile, CoachPatientLink, PatientProfile


class Command(BaseCommand):
    help = 'Creates test coach (testcoach/testpass123) linked to TEST001 and TEST002'

    def handle(self, *args, **options):
        # Create Django User
        user, created = User.objects.get_or_create(
            username='testcoach',
            defaults={'email': 'coach@test.com', 'first_name': 'Test', 'last_name': 'Coach'},
        )
        user.set_password('testpass123')
        user.save()

        # Create TherapistProfile
        therapist, _ = TherapistProfile.objects.get_or_create(
            user=user,
            defaults={
                'therapist_id': 'COACH001',
                'name': 'Dr. Test Coach',
                'license_number': 'PT-2024-001',
                'specialization': 'Sports Physiotherapy',
                'email': 'coach@test.com',
                'phone': '9999900099',
            },
        )

        # Link test patients
        linked = []
        for pid in ['TEST001', 'TEST002']:
            patient = PatientProfile.objects.filter(patient_id=pid).first()
            if patient:
                CoachPatientLink.objects.get_or_create(
                    coach=therapist,
                    patient=patient,
                    defaults={'is_active': True},
                )
                linked.append(pid)
            else:
                self.stdout.write(self.style.WARNING(
                    f'  Patient {pid} not found — run create_test_patient first'
                ))

        verb = 'created' if created else 'already exists'
        self.stdout.write(self.style.SUCCESS(
            f'Coach {verb}: testcoach / testpass123 → {therapist.name} ({therapist.therapist_id})'
        ))
        if linked:
            self.stdout.write(self.style.SUCCESS(
                f'Linked athletes: {", ".join(linked)}'
            ))
        self.stdout.write('Login at /coach/login/')
