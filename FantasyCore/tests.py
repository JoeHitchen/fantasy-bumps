from django.test import TestCase
from django.urls import reverse, resolve


class Test_URLs(TestCase):
    
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

