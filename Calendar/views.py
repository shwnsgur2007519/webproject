import calendar
import datetime
import json
from django.shortcuts import render, redirect
from .models import Schedule, ScheduleType
from .forms import ScheduleForm, ScheduleTypeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import make_aware
from django.utils import timezone as tz
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from .ai import schedule_relocation, toJson, toSchedule
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import timedelta, timezone, datetime
from django.core.exceptions import ValidationError

KST = timezone(timedelta(hours=23))

def how_to_use(request):
    return render(request, 'calendar/how_to_use.html', {'has_ai_session': 'ai_result_json' in request.session})


def index(request):
    today = datetime.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)

    if request.user.is_authenticated:
        schedules = Schedule.objects.filter(
            owner=request.user
        ).filter(
            Q(deadline__year=year, deadline__month=month) |
            Q(start_time__year=year, start_time__month=month)
        )
    else:
        schedules = Schedule.objects.none()


    ai_result_json = request.session.get('ai_result_json', '')
    ai_results = []
    hidden_ids = []

    if ai_result_json:
        ai_results_str=json.loads(ai_result_json)
        ai_results = toSchedule(ai_results_str)
        hidden_ids = [s['id'] for s in ai_results_str]  # 숨길 원래 일정 id


    # 날짜별 일정 분류
    schedule_map = {}

    for schedule in schedules:
        # 마감일 기준 등록
        if schedule.deadline:
            date_key = schedule.deadline.day
            schedule_map.setdefault(date_key, []).append(("deadline", schedule))

        # 시작일 기준 등록
        if schedule.start_time and not schedule.id in hidden_ids:
            date_key = schedule.start_time.day
            schedule_map.setdefault(date_key, []).append(("start_time", schedule))
        
    for schedule in ai_results:
        if schedule.start_time and schedule.start_time.month == month:
            date_key = schedule.start_time.day
            schedule_map.setdefault(date_key, []).append(("ai_schedule", schedule))


    # 정렬: 마감 일정이 위에 뜨도록
    for day in schedule_map:
        schedule_map[day].sort(key=lambda pair: 0 if pair[0] == "deadline" else (1 if pair[0] == "start_time" else -1))


    # JSON용 schedule 정리 (모달용)
    schedule_json = {
    day: [
        {
            'id': s.id,
            'task_name': s.task_name,
            'subject': s.subject,
            'deadline': s.deadline.strftime('%Y-%m-%d %H:%M') if s.deadline else '',
            'is_fixed': s.is_fixed,
            'is_exam_task': s.is_exam_task,
            'owner_id': s.owner.id,
            'color': s.color,
            'is_done':s.is_done,
            'type' : type,
            'task_type' : str(s.task_type),
            'duration_minutes' : s.duration_minutes,
            'start_time': s.start_time.strftime('%Y-%m-%d %H:%M') if s.start_time else '',
        }
        for type, s in schedule_list
    ]
    for day, schedule_list in schedule_map.items()
    }


    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)



    context = {
        'year': year,
        'month': month,
        'calendar_data': month_days,
        'schedule_map': schedule_map,
        'schedule_json': json.dumps(schedule_json),
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'today_day': today.day if year == today.year and month == today.month else None,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'has_ai_session': 'ai_result_json' in request.session,
    }

    return render(request, 'calendar/schedule_list.html', context)

@login_required(login_url='common:login')
def schedule_week(request):
    date_str = request.GET.get('date')
    if date_str:
        try:
            reference_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            reference_date = datetime.now().date()
    else:
        reference_date = datetime.now().date()

    # 월요일 기준 주 시작일
    start_of_week = reference_date - timedelta(days=reference_date.weekday())
    days = [start_of_week + timedelta(days=i) for i in range(7)]

    # 수정 중 일정 띄우기
    ai_result_json = request.session.get('ai_result_json', '')
    ai_results = []
    hidden_ids = []

    if ai_result_json:
        ai_results_str=json.loads(ai_result_json)
        ai_results = toSchedule(ai_results_str)
        hidden_ids = [s['id'] for s in ai_results_str]  # 숨길 원래 일정 id


    schedules = Schedule.objects.filter(
        owner=request.user,
    )
    # 요일별로 스케줄 정리
    schedule_map = {}

    for schedule in schedules:
        # 마감일 기준 등록
        if schedule.deadline and days[0]<=schedule.deadline.date()<=days[-1]:
            date_key = schedule.deadline.date()
            schedule_map.setdefault(date_key, []).append(("deadline", schedule))

        # 시작일 기준 등록
        if schedule.start_time and not schedule.id in hidden_ids and days[0]<=schedule.start_time.date()<=days[-1]:
            date_key = schedule.start_time.date()
            schedule_map.setdefault(date_key, []).append(("start_time", schedule))
                
    for schedule in ai_results:
        if schedule.start_time and days[0]<=schedule.start_time.date()<=days[-1]:
            date_key = schedule.start_time.date()
            schedule_map.setdefault(date_key, []).append(("ai_schedule", schedule))

    # 정렬: 마감 먼저
    for day in schedule_map:
        schedule_map[day].sort(key=lambda pair: 0 if pair[0] == "deadline" else (1 if pair[0] == "start_time" else -1))
    
    schedule_json={}

    for date, pairs in schedule_map.items():
        date_str = date.strftime("%Y-%m-%d")
        
        schedule_json[date_str] = []

        for type_, s in pairs:
            schedule_json[date_str].append({
                'id': s.id,
                'task_name': s.task_name,
                'type': type_,
                'subject': s.subject,
                'deadline': s.deadline.strftime('%Y-%m-%d %H:%M') if s.deadline else '',
                'start_time': s.start_time.strftime('%Y-%m-%d %H:%M') if s.start_time else '',
                'is_fixed': s.is_fixed,
                'is_exam_task': s.is_exam_task,
                'owner_id': s.owner.id,
                'color': s.color,
                'is_done': s.is_done,
                'task_type': str(s.task_type),
                'duration_minutes': s.duration_minutes,
                'start_time': s.start_time.strftime('%Y-%m-%d %H:%M') if s.start_time else '',
            })

    
    context = {
        'days': days,
        'schedule_map': schedule_map,
        'schedule_json': json.dumps(schedule_json),
        'hours': range(0, 24),
        'user_id': request.user.id if request.user.is_authenticated else None,
        'prev_date': (start_of_week - timedelta(days=7)).strftime('%Y-%m-%d'),
        'next_date': (start_of_week + timedelta(days=7)).strftime('%Y-%m-%d'),
        'has_ai_session': 'ai_result_json' in request.session,
        'today': datetime.now().date(),
    }
    return render(request, 'calendar/schedule_week.html', context)


@login_required(login_url='common:login')
def schedule_create(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST, owner=request.user)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.owner = request.user
            try:
                schedule.full_clean()  # 모델 유효성 검사
                schedule.save()
                return redirect('calendar:index')
            except ValidationError as e:
                form.add_error(None, e)  # 폼 전체 에러로 추가

    else:
        form = ScheduleForm(owner=request.user)
    return render(request, 'calendar/schedule_form.html', {'form': form, 'is_edit': False})

@login_required(login_url='common:login')
def schedule_edit(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk, owner=request.user)
    next_url = request.GET.get('next') or request.POST.get('next')  # GET/POST 모두 대응

    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule, owner=request.user)
        if form.is_valid():
            form.save()

            # 보안 체크 포함
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('calendar:index')
    else:
        form = ScheduleForm(instance=schedule, owner=request.user)

    return render(request, 'calendar/schedule_form.html', {
        'form': form,
        'is_edit': True,
        'next': next_url,
        'id': pk,
    })

@require_POST
@login_required(login_url='common:login')
def schedule_duplicate(request, pk):
    original = get_object_or_404(Schedule, pk=pk, owner=request.user)

    # 복제 생성
    Schedule.objects.create(
        owner=original.owner,
        task_name=original.task_name,
        duration_minutes=original.duration_minutes,
        difficulty=original.difficulty,
        importance=original.importance,
        task_type=original.task_type,
        subject=original.subject,
        is_exam_task=original.is_exam_task,
        exam=original.exam,
        deadline=original.deadline,
        start_time=original.start_time,
        end_time=original.end_time,
        is_fixed=original.is_fixed,
        color=original.color,
        is_done=original.is_done,
    )

    # messages.success(request, "일정이 복제되었습니다.")
    return redirect(request.META.get('HTTP_REFERER', 'calendar:schedule_list'))

@login_required(login_url='common:login')
def schedule_list(request):
    schedules = Schedule.objects.filter(owner=request.user).order_by('deadline')
    return render(request, 'calendar/schedule_list_page.html', {'schedules': schedules})

def schedule_type_create(request):
    if request.method == 'POST':
        form = ScheduleTypeForm(request.POST)
        if form.is_valid():
            schedule_type = form.save(commit=False)
            schedule_type.owner = request.user  # 소유자 지정
            schedule_type.save()
            return redirect('calendar:schedule_type_list')  # 저장 후 이동
    else:
        form = ScheduleTypeForm()
    
    return render(request, 'calendar/schedule_type_create.html', {'form': form})

@login_required(login_url='common:login')
def schedule_type_list(request):
    types = ScheduleType.objects.filter(owner=request.user)
    return render(request, 'calendar/schedule_type_list.html', {'types': types,'has_ai_session': 'ai_result_json' in request.session})

@login_required(login_url='common:login')
def schedule_type_edit(request, pk):
    schedule_type = get_object_or_404(ScheduleType, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ScheduleTypeForm(request.POST, instance=schedule_type)
        if form.is_valid():
            form.save()
            return redirect('calendar:schedule_type_list')
    else:
        form = ScheduleTypeForm(instance=schedule_type)
    return render(request, 'calendar/schedule_type_form.html', {'form': form, 'is_edit': True,'has_ai_session': 'ai_result_json' in request.session})

@login_required(login_url='common:login')
def schedule_type_delete(request, pk):
    schedule_type = get_object_or_404(ScheduleType, pk=pk, owner=request.user)
    if request.method == 'POST':
        schedule_type.delete()
        return redirect('calendar:schedule_type_list')
    return render(request, 'calendar/schedule_type_confirm_delete.html', {'type': schedule_type, 'has_ai_session': 'ai_result_json' in request.session})

@csrf_exempt
@login_required
def schedule_mark_done(request, pk):
    if request.method == 'POST':
        try:
            schedule = Schedule.objects.get(pk=pk, owner=request.user)
            schedule.is_done = True
            schedule.save()
            return JsonResponse({'success': True})
        except Schedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

@csrf_exempt
@login_required
def schedule_unmark_done(request, pk):
    if request.method == 'POST':
        try:
            schedule = Schedule.objects.get(pk=pk, owner=request.user)
            schedule.is_done = False
            schedule.save()
            return JsonResponse({'success': True})
        except Schedule.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)

@login_required(login_url='common:login')
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk, owner=request.user)
    if request.method == 'POST':
        schedule.delete()
        return redirect('calendar:schedule_list')
    return render(request, 'calendar/schedule_confirm_delete.html', {'type': schedule})

def now_kst_naive():
    return datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)

@login_required(login_url='common:login')
def schedule_replace(request):
    data = Schedule.objects.filter(
        owner=request.user,
        is_done=False,
        is_fixed=False,
    ).filter(
        Q(deadline__gt=now_kst_naive()) |
        Q(deadline__isnull=True)
    ).order_by('deadline')
    
    default_start = (now_kst_naive()).strftime("%Y-%m-%dT%H:%M")
    default_end = (now_kst_naive() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    return render(request, 'calendar/schedule_replace.html', 
                  {'schedules': data, 
                   'default_start': default_start, 
                   'default_end': default_end, 
                   'has_ai_session': 'ai_result_json' in request.session})

@require_POST
def ai_run(request):
    selected_ids = request.POST.getlist('selected_ids')
    schedules = Schedule.objects.filter(pk__in=selected_ids)
    data_json = toJson(schedules)

    # --- (수정됨) 가용 시간을 POST 데이터에서 가져오기 ---
    available_start_time = request.POST.get('available_start_time')
    available_end_time = request.POST.get('available_end_time')

    # --- (수정됨) 가져온 가용 시간을 세션에 저장 ---
    if available_start_time:
        request.session['user_available_start_time'] = available_start_time
    if available_end_time:
        request.session['user_available_end_time'] = available_end_time
    
    # 재배치 전체 기간 처리 (기존 로직)
    schedule_start_str = request.POST.get('schedule_start')
    schedule_end_str = request.POST.get('schedule_end')
    
    try:
        schedule_start = datetime.strptime(schedule_start_str, "%Y-%m-%dT%H:%M")
        schedule_end = datetime.strptime(schedule_end_str, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        schedule_start = now_kst_naive()
        schedule_end = now_kst_naive() + timedelta(days=7)

    # --- (수정됨) AI 재배치 함수에 가용 시간 정보 전달 ---
    available_times = {'start': available_start_time, 'end': available_end_time}
    update_json = schedule_relocation(data_json, schedule_start, schedule_end, available_times)
    
    # AI 처리 결과에 따른 분기 (기존 로직과 동일)
    if isinstance(update_json, str):
        messages.warning(request, update_json)
        return redirect('calendar:schedule_replace')

    request.session['ai_result_json'] = json.dumps(update_json)
    return redirect('calendar:index')

@require_POST
@login_required(login_url='common:login')
def ai_confirm(request):
    import json
    from django.utils.timezone import make_aware

    ai_result_raw = request.session.pop('ai_result_json', None)

    if not ai_result_raw:
        return redirect(request.META.get('HTTP_REFERER', 'calendar:index'))

    try:
        ai_result_list = json.loads(ai_result_raw)

        # ID별로 start_time만 추출
        id_to_start = {
            item['id']: (
                make_aware(datetime.strptime(item['start_time'], '%Y-%m-%d %H:%M:%S'))
                if item.get('start_time')
                else None
            )
            for item in ai_result_list
        }


        # 기존 인스턴스를 DB에서 다시 조회
        schedules = Schedule.objects.filter(id__in=id_to_start.keys())

        for s in schedules:
            s.start_time = id_to_start[s.id]

        with transaction.atomic():
            Schedule.objects.bulk_update(schedules, ['start_time'])

    except Exception as e:
        messages.error(request, f"AI 확정 중 오류 발생: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'calendar:index'))

@require_POST
@login_required
def ai_cancel(request):
    request.session.pop('ai_result_json', None)
    return redirect(request.META.get('HTTP_REFERER', 'calendar:index'))


def test(request):
    import json
    from datetime import datetime
    from .ai import schedule_relocation  # 상대경로 import
    import os

    # 1. JSON 파일 불러오기
    json_file = os.path.join(os.path.dirname(__file__), "testjson.json")
    with open(json_file, 'r', encoding='utf-8') as f:
        task_list = json.load(f)

    # 2. 일정 시작/종료 시간 정의
    schedule_start = datetime.strptime("2025-06-08 17:07:00", "%Y-%m-%d %H:%M:%S")
    schedule_end   = datetime.strptime("2025-06-15 17:07:00", "%Y-%m-%d %H:%M:%S")

    # 3. 함수 실행
    result = schedule_relocation(task_list, schedule_start, schedule_end)

    # 4. 결과 출력
    print("\n\n재배치 결과:")
    if isinstance(result, str):
        print(result)
    else:
        for task in result:
            print(f"- {task.get('task_name', '이름 없음')}: 시작 → {task['start_time']}")
    
    return redirect('calendar:index')