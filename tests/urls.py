from django.conf.urls import url
from django.contrib import admin

from . import views


urlpatterns = [
    url(r'^example$', views.ExampleView.as_view(), name='example'),
    url(r'^admin/', admin.site.urls),
]
