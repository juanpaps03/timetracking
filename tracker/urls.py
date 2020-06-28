from django.conf.urls import url

from . import views, views_api

urlpatterns = [
    url(regex=r'^$', view=views.Dashboard.as_view(), name='dashboard'),
    url(regex=r'^loghours/$', view=views.LogHours.as_view(), name='log_hours'),
    url(regex=r'^dayreview/$', view=views.DayReview.as_view(), name='day_review'),
    url(regex=r'^past_days/$', view=views.PastDays.as_view(), name='past_days'),
    url(regex=r'^past_days_edit/$', view=views.PastDaysEdit.as_view(), name='past_days_edit'),
    url(regex=r'^dht_report/$', view=views.DhtReport.as_view(), name='dht_report'),
    url(regex=r'^dht_tasks_report/$', view=views.DhtTasksReport.as_view(), name='dht_tasks_report'),
    url(regex=r'^dht_tasks_report_resumen/$', view=views.DhtTasksReportResumen.as_view(), name='dht_tasks_report_resumen'),
    url(regex=r'^api/add_hours/(?P<date>\d{4}-\d{2}-\d{2})/$', view=views_api.CreateLogHoursPastDay.as_view(), name='api_add_hours_past_day'),
    url(regex=r'^api/add_hours/$', view=views_api.CreateLogHours.as_view(), name='api_add_hours'),
    url(regex=r'^api/start_day/$', view=views_api.StartDay.as_view(), name='api_start_day'),
    url(regex=r'^api/end_day/$', view=views_api.EndDay.as_view(), name='api_end_day'),
    url(regex=r'^api/daily_report/$', view=views_api.DailyReport.as_view(), name='api_daily_report'),
    url(regex=r'^api/daily_report_from_past_day/$', view=views_api.DailyReportFromPastDay.as_view(), name='api_daily_report_from_past_day'),
    url(regex=r'^api/dhtgeneral_report/$', view=views_api.DhtReportApi.as_view(), name='api_dhtgeneral_report'),
    url(regex=r'^api/dht_tasks_report_api/$', view=views_api.DhtTasksReportApi.as_view(), name='api_dht_tasks_report'),
    url(regex=r'^api/dht_tasks_report_resumen_api/$', view=views_api.DhtTasksReportResumenApi.as_view(), name='api_dht_tasks_report_resumen')
]

