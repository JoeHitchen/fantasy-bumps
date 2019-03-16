from django.views.generic.base import TemplateView

from external import utils as ext
from external.constants import genders


class IndexView(TemplateView):
    template_name = 'fantasybumps/index.html'



class MarketView(TemplateView):
    template_name = 'fantasybumps/market.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        gender = context['gender']
        context['gender'] = {genders.MENS: 'Men', genders.WOMENS: 'Women'}[gender]
        context['start_order'] = ext.get_start_order(gender)
        
        return context

