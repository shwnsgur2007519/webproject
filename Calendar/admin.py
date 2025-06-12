from django.contrib import admin
from .models import Schedule, ScheduleType
# Register your models here.
# admin.site.register(Schedule)

class ScheduleAdmin(admin.ModelAdmin):
    search_fields = ['task_name', 'task_type', 'subject']
    
class ScheduleFormAdmin(admin.ModelAdmin):
    search_fields = ['name', 'owner']

admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(ScheduleType)