from django import forms
from .models import Schedule, ScheduleType
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

COLOR_CHOICES = [
    ('#FF0000', '색상 1'),
    ("#FFBF00", '색상 2'),
    ("#EEFF00", '색상 3'),
    ("#00FF33", '색상 4'),
    ("#00D2FC", '색상 5'),
    ("#0059FF", '색상 6'),
    ("#1900FF", '색상 7'),
    ("#6A00FF", '색상 8'),
    ("#EA00FF", '색상 9'),
]


class ScheduleForm(forms.ModelForm):
    color=forms.ChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.Select(attrs={'class':'form-select'})
    )
    class Meta:
        model = Schedule
        fields = [
            'task_name','duration_minutes','difficulty','importance','task_type','subject',
            'is_exam_task','exam','deadline','start_time','end_time','is_fixed','color',
        ]
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'task_name':         '일정 이름',
            'duration_minutes':  '소요 시간(분)',
            'difficulty':        '난이도',
            'importance':        '중요도',
            'task_type':         '일정 분류',
            'subject':           '과목',
            'is_exam_task':      '시험 일정 여부',
            'exam':              '관련 시험',
            'deadline':          '마감 기한',
            'start_time':        '시작 시간',
            'end_time':          '종료 시간',
            'is_fixed':          '고정 여부',
            'color':             '색상',
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)

        # owner 기준으로 task_type 필터링
        if owner is not None:
            self.fields['task_type'].queryset = ScheduleType.objects.filter(owner=owner)

        # exam 필드: 자기 자신 제외 + 해당 사용자 + 시험 일정만
        if owner is not None:
            queryset = Schedule.objects.filter(owner=owner, is_exam_task=True)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields['exam'].queryset = queryset
        else:
            # owner 없으면 비워 두기
            self.fields['exam'].queryset = Schedule.objects.none()

class ScheduleTypeForm(forms.ModelForm):
    class Meta:
        model=ScheduleType
        fields = ['name']

User = get_user_model()

class NicknameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nickname']

from django.forms import modelformset_factory
from .models import ShareSetting

ShareSettingFormSet = modelformset_factory(
    ShareSetting,
    fields=('to_user', 'schedule_type'),
    extra=1,
    can_delete=True
)
