import datetime
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chatbot.models import ChatUser, UserChatSession

class SessionExpirationTests(APITestCase):
    def setUp(self):
        # Create a test user and session
        self.user = ChatUser.objects.create(name="Test User", email="test@example.com")
        self.session_id = "test-session-123"
        self.session = UserChatSession.objects.create(
            session_id=self.session_id,
            user=self.user,
            chat_details=[]
        )

    def test_active_session_retrieval(self):
        # Retrieve the session immediately; it should succeed and return HTTP 200 OK
        url = f"{reverse('chat')}?session_id={self.session_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_id'], self.session_id)

    def test_session_expiration_on_get(self):
        # Force updated_at to be older than 10 minutes (e.g., 11 minutes ago)
        eleven_minutes_ago = timezone.now() - datetime.timedelta(minutes=11)
        UserChatSession.objects.filter(session_id=self.session_id).update(updated_at=eleven_minutes_ago)

        url = f"{reverse('chat')}?session_id={self.session_id}"
        response = self.client.get(url)

        # It should return HTTP 404 NOT FOUND and delete the session from the DB
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(UserChatSession.objects.filter(session_id=self.session_id).exists())

    def test_session_expiration_on_post(self):
        # Force updated_at to be older than 10 minutes
        eleven_minutes_ago = timezone.now() - datetime.timedelta(minutes=11)
        UserChatSession.objects.filter(session_id=self.session_id).update(updated_at=eleven_minutes_ago)

        url = reverse('chat')
        data = {
            "session_id": self.session_id,
            "message": "Hello, is this AVL?"
        }
        response = self.client.post(url, data, format='json')

        # It should return HTTP 404 NOT FOUND and delete the session from the DB
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(UserChatSession.objects.filter(session_id=self.session_id).exists())

