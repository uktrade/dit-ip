from django.views.generic import View
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse


class ExampleView(View):
    def get(self, request):
        return HttpResponse("It works!")
