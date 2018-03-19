from django.contrib import admin

from tracker.models import Building, Workday, LogHour, Task

admin.site.register(Building)
admin.site.register(Workday)
admin.site.register(LogHour)
admin.site.register(Task)
