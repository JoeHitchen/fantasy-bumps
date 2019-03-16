from django.test import TestCase
from django.urls import reverse

from external import utils as ext


class Test__Index(TestCase):
    
    def test__index(self):
        """Renders the index page."""
        
        response = self.client.get(reverse('fantasybumps:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/index.html')



class Test__Market_Men(TestCase):
    
    def test__without_user(self):
        """Renders the market page for the men's competition."""
        
        response = self.client.get(reverse('fantasybumps:men'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Men')
        self.assertEqual(response.context['start_order'], ext.start_order_men)



class Test__Market_Women(TestCase):
    
    def test__without_user(self):
        """Renders the market page for the women's competition."""
        
        response = self.client.get(reverse('fantasybumps:women'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'fantasybumps/market.html')
        
        self.assertEqual(response.context['gender'], 'Women')
        self.assertEqual(response.context['start_order'], ext.start_order_women)

