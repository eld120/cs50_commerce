from django.test import Client, TestCase
from django.urls import reverse

from auctions.tests import factories


class TestUserLogin(TestCase):
    def test_login(self):
        factories.UserFactory()
        pass


class TestIndexView(TestCase):
    def test_index(self):
        client = Client()
        url = reverse("auctions:index")
        response = client.get(url)
        self.assertTemplateUsed(response, "auctions/index.html")
        self.assertEqual(response.status_code, 200)
