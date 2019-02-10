from django.test import TestCase
from django.urls import reverse, resolve


class Test__Views(TestCase):
    
    def test__index(self):
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')
    
    
    def test__men(self):
        
        response = self.client.get(reverse('fantasybumps:men'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Men')
    
    
    def test__women(self):
        
        response = self.client.get(reverse('fantasybumps:women'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Women')

