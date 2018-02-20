from django.conf.urls import url

from . import views

urlpatterns = [
    url(regex=r'^(?P<username>[\w.@+-]+)/$', view=views.Dashboard.as_view(), name='dashboard'),
]
