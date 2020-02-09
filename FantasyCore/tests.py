import json

from django.test import TestCase
from django.urls import reverse
from django.contrib import messages

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
    
    def test__success(self):
        """Redirects to the login page and sends a success message."""
        
        post_data = {
            'username': 'test',
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        }
        response = self.client.post(reverse('signup'), post_data)
        self.assertRedirects(response, reverse('login'))
        
        response_messages = messages.get_messages(response.wsgi_request)
        self.assertEqual(len(response_messages), 1)
        for msg in response_messages:
            self.assertEqual(msg.level, messages.SUCCESS)
            self.assertEqual(
                msg.message,
                'Account successfully created. Sign in to begin playing.',
            )

