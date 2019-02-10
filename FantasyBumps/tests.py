from django.test import TestCase
from django.urls import reverse, resolve


class Test__Views(TestCase):
    
    def test__index(self):
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')

