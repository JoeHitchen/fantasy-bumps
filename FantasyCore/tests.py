import json

from django.test import TestCase
from django.urls import reverse
from django.contrib import messages
from django.contrib import auth

from . import forms
from .views import healthcheck_notice


class Test__URLs(TestCase):
    
    def test__accounts_inbuilt(self):
        """
        Checks that the in-build account URLs are included in the URL config.
        """
        
        # Define standard configuration
        url_configs = [
            ('login', 'login/'),
            ('password_reset', 'password_reset/'),
            ('password_reset_done', 'password_reset/done/'),
            ('password_reset_confirm', 'reset/uidb64/token/', 'uidb64', 'token'),
            ('password_reset_complete', 'reset/done/'),
            ('password_change', 'password_change/'),
            ('password_change_done', 'password_change/done/'),
        ]
        
        # Test iteratively
        for url_name, url_subpath, *url_args in url_configs:
            with self.subTest(name = url_name):
                
                self.assertEqual(
                    reverse(url_name, args = url_args),
                    '/accounts/' + url_subpath,
                )



class Test__Healthcheck(TestCase):
    
    def test__default(self):
        """Returns a JSON containing the site name and a notice."""
        
        response = self.client.get(reverse('healthcheck'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'name': 'FantasyBumps', 'notice': healthcheck_notice},
        )
    
    
    def test__with_data(self):
        """Includes GET data in the reponse."""
        
        response = self.client.get(reverse('healthcheck'), {'data': '49c8ec32'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'name': 'FantasyBumps', 'notice': healthcheck_notice, 'data': '49c8ec32'},
        )
    
    
    def test__no_overwrite(self):
        """Does not allow GET data to overwrite name or notice."""
        
        response = self.client.get(reverse('healthcheck'), {'name': 'hidden', 'notice': 'hidden'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'name': 'FantasyBumps', 'notice': healthcheck_notice},
        )



class Test__Account_Signup(TestCase):
    
    def test__form__without_email(self):
        """Creates a user that does not have an e-mail address."""
        
        username = 'ATestUser'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertTrue(form.is_valid())
        form.save()
        
        user = auth.models.User.objects.get(username = username)
        self.assertFalse(user.email)
    
    
    def test__form__with_email(self):
        """Creates a user that does has an e-mail address."""
        
        username = 'ATestUser'
        email = 'test@example.org'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'email': email,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertTrue(form.is_valid())
        form.save()
        
        user = auth.models.User.objects.get(username = username)
        self.assertEqual(user.email, email)
        
    
    def test__view__success(self):
        """Redirects to the login page and sends a success message."""
        
        username = 'ATestUser'
        post_data = {
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        }
        response = self.client.post(reverse('signup'), post_data)
        self.assertRedirects(response, reverse('fantasybumps:index'))
        
        user = auth.get_user(self.client)
        self.assertEqual(user.username, username)
        self.assertTrue(user.is_authenticated)
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 1)
        for msg in response_messages:
            self.assertEqual(msg.level, messages.SUCCESS)
            self.assertEqual(
                msg.message,
                'Welcome ATestUser - Your account has been created.',
            )



class Test__Account_Update(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.user = auth.models.User.objects.create_user('user', '', 'password')
    
    
    def test__no_login(self):
        """Redirects to the login page."""
        
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, reverse('login'))
    
    
    def test__ignore_username(self):
        """Ignores attempts to update usernames."""
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'username': 'AlternativeUser'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'user')
    
    
    def test__view__add_email(self):
        """Adds an e-mail address to the User."""
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test@example.com'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 1)
        for msg in response_messages:
            self.assertEqual(msg.level, messages.SUCCESS)
            self.assertEqual(
                msg.message,
                'Profile updated',
            )
    
    
    def test__view__change_email(self):
        """Changes the User's e-mail."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test@example.com'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 1)
        for msg in response_messages:
            self.assertEqual(msg.level, messages.SUCCESS)
            self.assertEqual(
                msg.message,
                'Profile updated',
            )
    
    
    def test__view__remove_email(self):
        """Removes the User's e-mail."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': ''})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, '')
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 1)
        for msg in response_messages:
            self.assertEqual(msg.level, messages.SUCCESS)
            self.assertEqual(
                msg.message,
                'Profile updated',
            )
    
    
    def test__view__reject_invalid_email(self):
        """Rejects invalid e-mail addresses."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test'})
        self.assertEqual(response.status_code, 200)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'example@test.com')
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 0)

