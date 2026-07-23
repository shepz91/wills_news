
from unittest.mock import patch
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from articles.models import Article, Publisher


class NewsApplicationAPITests(APITestCase):

    def setUp(self):
        self.reader_group, _ = Group.objects.get_or_create(name='Reader')
        self.journalist_group, _ = Group.objects.get_or_create(name='Journalist')
        self.editor_group, _ = Group.objects.get_or_create(name='Editor')

        self.publisher_alpha = Publisher.objects.create(name="Alpha Network")
        self.publisher_beta = Publisher.objects.create(name="Beta Network")

        self.reader = User.objects.create_user(username='reader_user', password='password123', email='reader@news.com')
        self.reader.groups.add(self.reader_group)
        self.reader_token = Token.objects.create(user=self.reader)

        self.journalist = User.objects.create_user(username='journalist_user', password='password123', email='journalist@news.com')
        self.journalist.groups.add(self.journalist_group)
        self.journalist_token = Token.objects.create(user=self.journalist)
        self.publisher_alpha.journalists.add(self.journalist)

        self.editor = User.objects.create_user(username='editor_user', password='password123', email='editor@news.com')
        self.editor.groups.add(self.editor_group)
        self.editor_token = Token.objects.create(user=self.editor)
        self.publisher_alpha.editors.add(self.editor)

        self.approved_alpha_article = Article.objects.create(
            title="Alpha Approved News",
            content="Content for Alpha network",
            publisher=self.publisher_alpha,
            approved=True
        )

        self.approved_beta_article = Article.objects.create(
            title="Beta Approved News",
            content="Content for Beta network",
            publisher=self.publisher_beta,
            approved=True
        )

        self.unapproved_alpha_article = Article.objects.create(
            title="Alpha Pending Draft",
            content="Pending editor verification review",
            publisher=self.publisher_alpha,
            approved=False
        )

        self.list_url = reverse('api-articles-list')
        self.subscribed_url = reverse('api-articles-subscribed')
        self.login_url = reverse('api_login')

    def get_detail_url(self, article_id):
        return reverse('api-articles-detail', kwargs={'pk': article_id})

    def test_token_authentication_success(self):
        """tests token authenticaTION for the system and if it is succesful"""
        response = self.client.post(self.login_url, {'username': 'reader_user', 'password': 'password123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_token_authentication_failed(self):
        """tests token authenticaTION for the system and if it is failed"""
        response = self.client.post(self.login_url, {'username': 'reader_user', 'password': 'wrong_password'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_public_feed_access(self):
        """
       Test:
        - Anyone can read.
        - Only Journalists, Editors, and Admins can write.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        subscribed_response = self.client.get(self.subscribed_url)
        self.assertEqual(subscribed_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reader_retrieves_only_subscribed_tenant_content(self):
        """
        TESTe:
        - Tenant articles: Restricted to publisher network staff only.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.reader_token.key)
        self.publisher_alpha.journalists.add(self.reader)

        response = self.client.get(self.subscribed_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_journalist_can_create_article_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.journalist_token.key)
        payload = {
            'title': 'Breaking News Entry',
            'content': 'Draft reporting text elements.',
            'publisher_id': self.publisher_alpha.id
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['approved'])

    def test_reader_cannot_create_article_failed(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.reader_token.key)
        payload = {
            'title': 'Illegal Submission',
            'content': 'Attempting to inject a post bypass.'
        }
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_modify_and_approve_articles(self):
        """Editors can edit and update articles inside their assigned network."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.editor_token.key)

        self.publisher_alpha.editors.add(self.editor)
        self.editor.publisher_editors.add(self.publisher_alpha)

        article = Article.objects.get(id=self.unapproved_alpha_article.id)
        detail_url = self.get_detail_url(article.id)

        payload = {
            'title': 'Updated Title by Editor',
            'content': 'New revised copy configuration data.'
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cross_tenant_editor_modification_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.editor_token.key)
        detail_url = self.get_detail_url(self.approved_beta_article.id)
        payload = {'title': 'Malicious Injection'}
        response = self.client.put(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete_article(self):
        """Editors retain delete permissions for tenant data."""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.editor_token.key)

        self.publisher_alpha.editors.add(self.editor)
        self.editor.publisher_editors.add(self.publisher_alpha)

        article = Article.objects.get(id=self.unapproved_alpha_article.id)
        detail_url = self.get_detail_url(article.id)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch('requests.post')
    def test_approval_signal_triggers_webhook_and_emails(self, mock_post):
        mock_post.return_value.status_code = 201
        article = self.unapproved_alpha_article
        article.approved = True
        article.save()

        called_urls = [call_arg[0][0] for call_arg in mock_post.call_args_list]
        self.assertTrue(any('/api/approved/' in url for url in called_urls))
