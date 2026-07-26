from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Classroom, QuizAttempt


class QuizHistoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='secret123')
        self.classroom = Classroom.objects.create(
            title='Test Class',
            description='A classroom for quiz testing.',
            owner=self.user,
            class_type='public',
        )

    def test_user_can_view_their_quiz_history(self):
        attempt = QuizAttempt.objects.create(
            classroom=self.classroom,
            student=self.user,
            score=2,
            total_questions=4,
            answers={'1': {'selected': 'A', 'correct': 'A', 'is_correct': True}},
        )

        self.client.login(username='student', password='secret123')
        response = self.client.get(reverse('my_results'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Results')
        self.assertContains(response, self.classroom.title)
        self.assertContains(response, str(attempt.score))
        self.assertContains(response, reverse('quiz_result', args=[attempt.attempt_id]))
