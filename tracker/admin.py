from django.contrib import admin

from tracker.models import Building, Workday, Loghour, Task

admin.site.register(Building)
admin.site.register(Workday)
admin.site.register(Loghour)
admin.site.register(Task)
