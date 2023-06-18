from typing import Optional, Callable, TypeVar, TYPE_CHECKING

from django.test import TestCase
from django.urls import reverse
from django.contrib import auth, messages

from . import forms

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse


Obj = TypeVar('Obj')


def exists(obj: Optional[Obj]) -> Obj:
    assert obj
    return obj


class MessagesTestMixin():
    
    MsgTuple = tuple[str, str]
    levels_matrix = {10: 'debug', 20: 'info', 25: 'success', 30: 'warning', 40: 'error'}
    
    subTest: Callable  # type: ignore
    assertEqual: Callable  # type: ignore
    
    @classmethod
    def message_tuple(cls, msg: messages.storage.base.Message) -> MsgTuple:
        """Converts a message object into a tuple for easy comparison."""
        return (cls.levels_matrix[msg.level], msg.message)
    
    
    def assertMessages(self, response: 'TestHttpResponse', expected: list[MsgTuple]) -> None:
        
        sent = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(sent), len(expected))
        
        for i, msg in enumerate(expected):
            with self.subTest(index = i):
                self.assertEqual(self.message_tuple(sent[i]), msg)


class Test__URLs(TestCase):
    
    def test__accounts_inbuilt(self) -> None:
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



class Test__Account_Signup(TestCase, MessagesTestMixin):
    
    default_character_set_error = (
        'Enter a valid username.'
        + ' This value may contain only letters, numbers, and @/./+/-/_ characters.'
    )
    
    def test__form__without_email(self) -> None:
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
    
    
    def test__form__with_email(self) -> None:
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
    
    
    def test__form__character_set__space(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATest User'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__character_set__at(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATestUser@'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__character_set__dot(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATestUser.'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__character_set__plus(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATestUser+'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__character_set__minus(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATestUser-'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__character_set__underscore(self) -> None:
        """Usernames can only contain letters and numbers."""
        
        username = 'ATestUser_'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertNotIn(self.default_character_set_error, str(form.errors['username']))
        self.assertIn(
            'Usernames can only contain letters and numbers.',
            str(form.errors['username']),
        )
    
    
    def test__form__case_insensitive_duplication(self) -> None:
        """Prevents creation of new users that differ from an existing user by only letter case."""
        
        auth.models.User.objects.create(username = 'atEStuSeR')
        
        username = 'ATestUser'
        form = forms.UserCreationWithEmailForm({
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('This team name is already taken.', str(form.errors['username']))
    
    
    def test__form__blacklisted_username_standard_error(self) -> None:
        """Blacklisted usernames are rejected."""
        
        form = forms.UserCreationWithEmailForm({
            'username': 'AbCBlacklistTestDEf',
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('This team name is not permitted.', str(form.errors['username']))
    
    
    def test__form__blacklisted_username_custom_error(self) -> None:
        """Custom error messages can be specified for blacklisted usernames."""
        
        form = forms.UserCreationWithEmailForm({
            'username': 'AbCHiTChENDEf',
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        })
        self.assertFalse(form.is_valid())
        self.assertIn(
            'The admin requests that you do not feature them in your team name.',
            str(form.errors['username']),
        )
        
    
    def test__view__success(self) -> None:
        """Redirects to the login page and sends a success message."""
        
        username = 'ATestUser'
        post_data = {
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        }
        response = self.client.post(reverse('signup'), post_data)
        self.assertRedirects(response, reverse('index'))
        
        user = auth.get_user(self.client)
        assert isinstance(user, auth.models.User)  # This format needed for MyPy purposes
        self.assertEqual(user.username, username)
        self.assertTrue(user.is_authenticated)
        
        self.assertMessages(response, [
            ('success', 'Welcome ATestUser - Your account has been created.'),
        ])
    
    
    def test__view__whitespace(self) -> None:
        """Checks whitespace is correctly stripped and handled - See #63."""
        
        username = '  ATestUser  '
        post_data = {
            'username': username,
            'password1': 'AComplexPassword',
            'password2': 'AComplexPassword',
        }
        response = self.client.post(reverse('signup'), post_data)
        self.assertRedirects(response, reverse('index'))
        
        user = auth.get_user(self.client)
        assert isinstance(user, auth.models.User)  # This format needed for MyPy purposes
        self.assertEqual(user.username, username.strip())
        self.assertTrue(user.is_authenticated)
        
        self.assertMessages(response, [
            ('success', 'Welcome ATestUser - Your account has been created.'),
        ])



class Test__Account_Update(TestCase, MessagesTestMixin):
    
    user: auth.models.User
    
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = auth.models.User.objects.create_user('user', '', 'password')
    
    
    def test__no_login(self) -> None:
        """Redirects to the login page."""
        
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, reverse('login'))
    
    
    def test__ignore_username(self) -> None:
        """Ignores attempts to update usernames."""
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'username': 'AlternativeUser'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'user')
    
    
    def test__view__add_email(self) -> None:
        """Adds an e-mail address to the User."""
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test@example.com'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')
        
        self.assertMessages(response, [('success', 'Profile updated')])
    
    
    def test__view__change_email(self) -> None:
        """Changes the User's e-mail."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test@example.com'})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')
        
        self.assertMessages(response, [('success', 'Profile updated')])
    
    
    def test__view__remove_email(self) -> None:
        """Removes the User's e-mail."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': ''})
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, '')
        
        self.assertMessages(response, [('success', 'Profile updated')])
    
    
    def test__view__reject_invalid_email(self) -> None:
        """Rejects invalid e-mail addresses."""
        
        self.user.email = 'example@test.com'
        self.user.save()
        
        self.client.login(username = 'user', password = 'password')
        
        response = self.client.post(reverse('profile'), {'email': 'test'})
        self.assertEqual(response.status_code, 200)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'example@test.com')
        
        self.assertMessages(response, [])

