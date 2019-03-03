from django.views.generic import View
try:
    from django.core.urlresolvers import reverse_lazy
except ImportError:
    from django.urls import reverse_lazy
from django.http import HttpResponse


class ExampleView(View):
    def get(self, request):
        return HttpResponse("It works!")
