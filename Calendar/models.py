from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

class ScheduleType(models.Model):
    name=models.CharField(max_length=50,blank=True)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name}"


class Schedule(models.Model):
    owner=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task_name=models.CharField(max_length=50, blank=True)
    duration_minutes=models.IntegerField(null=True, blank=True)
    difficulty=models.IntegerField(null=True, blank=True)
    importance=models.IntegerField(null=True, blank=True)
    task_type = models.ForeignKey('ScheduleType', null=True, blank=True, on_delete=models.SET_NULL)
    subject=models.CharField(max_length=50, blank=True)
    is_exam_task=models.BooleanField(default=False)
    deadline=models.DateTimeField(null=True ,blank=True)
    start_time=models.DateTimeField(null=True ,blank=True)
    end_time=models.DateTimeField(null=True ,blank=True)
    is_fixed=models.BooleanField(default=False)
    exam=models.ForeignKey('self',default=None, on_delete=models.SET_DEFAULT, null=True ,blank=True)
    color = models.CharField(max_length=7, blank=True, default='#6c8df5')
    is_done = models.BooleanField(default=False)
    
    
    def clean(self):
        super().clean()
        # 조건: 시험 일정이면 deadline은 필수
        errors={}
        if self.task_name == '':
            errors['task_name'] = '일정 이름을 입력하세요'
        elif self.is_exam_task and self.exam:
            errors['exam']='시험 일정이면 입력할 수 없습니다.'
        if self.is_fixed and self.start_time is None:
            errors['start_time']='고정 일정이면 반드시 입력해야 합니다'
        # if self.is_fixed and self.end_time is None:
        #     errors['end_time']='고정 일정이면 반드시 입력해야 합니다'
        if self.difficulty and not 1<=self.difficulty<=5:
            errors['difficulty'] = '1에서 5 사이여야 합니다.'
        if self. importance and not 1<=self.importance<=5:
            errors['difficulty'] = '1에서 5 사이여야 합니다.'
        
        if errors:
            raise ValidationError(errors)
    
    def __str__(self):
        return f"{self.task_name}[{self.owner}]"

class ShareSetting(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='shared_from_me', on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='shared_to_me', on_delete=models.CASCADE
    )
    schedule_type = models.ForeignKey(
        ScheduleType, on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        unique_together = ('from_user', 'to_user', 'schedule_type')

    def __str__(self):
        return f"{self.from_user} → {self.to_user} : {self.schedule_type or '(기본 분류)'}"

class VisibleShare(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visible_shares')  # 보는 사람
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visible_by')  # 보여지는 사람

    class Meta:
        unique_together = ('user', 'target')