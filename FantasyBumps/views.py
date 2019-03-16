from django.views.generic.base import TemplateView

from external import utils as ext
from external.constants import genders

from . import utils


class IndexView(TemplateView):
    template_name = 'fantasybumps/index.html'



class MarketView(TemplateView):
    template_name = 'fantasybumps/market.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        gender = context['gender']
        context['gender'] = {genders.MENS: 'Men', genders.WOMENS: 'Women'}[gender]
        context['start_order'] = ext.get_start_order(gender)
        
        user = self.request.user
        if user.is_authenticated:
            
            crew = utils.get_crew(user, gender)
            context['crew'] = crew
            context['crew_valid'] = utils.has_all_seats(crew)
            
            other_gender = ext.reverse_gender(gender)
            other_crew = utils.get_crew(user, other_gender)
            context['other_crew_valid'] = utils.has_all_seats(other_crew)
        
        return context

