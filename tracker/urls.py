from django.conf.urls import url

from . import views, views_api

urlpatterns = [
    url(regex=r'^$', view=views.Dashboard.as_view(), name='dashboard'),
    url(regex=r'^loghours/$', view=views.LogHours.as_view(), name='log_hours'),
    url(regex=r'^api/start_work_day/$', view=views_api.StartWorkday.as_view(), name='api_start_workday'),
    url(regex=r'^api/add_hours/$', view=views_api.LogsHoursCrate.as_view(), name='api_add_hours'),
]
