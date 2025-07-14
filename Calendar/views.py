import calendar
import json
from django.shortcuts import render, redirect
from .models import Schedule, ScheduleType, ShareSetting, VisibleShare
from .forms import ScheduleForm, ScheduleTypeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import make_naive
from datetime import timedelta, datetime
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, OuterRef, Exists
from .schedule_relocation import schedule_relocation, toJson, toSchedule
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import timezone as tz
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()
KST = tz(timedelta(hours=9))

def get_now():
    return make_naive(datetime.now(KST))

def how_to_use(request):
    return render(request, 'calendar/how_to_use.html', {'has_ai_session': 'ai_result_json' in request.session})

def allowed_schedules(schedules, user):
    if user.is_authenticated:
        # ① 본인 일정
        myschedules = schedules.filter(
            owner=user
        )

        # 공유 일정 – 나에게 공유해준 사람들 중 내가 보도록 선택한 유저
        shared_from_users = VisibleShare.objects.filter(user=user).values_list('target', flat=True)

        # 공유된 일정 ID 추출 (기본 분류 포함 처리)
        shared_ids = schedules.filter(
            owner__in=shared_from_users
        )
        
        typed_ids = shared_ids.annotate(
            is_allowed=Exists(
                ShareSetting.objects.filter(
                    from_user=OuterRef('owner'),
                    to_user=user
                ).filter(
                    schedule_type=OuterRef('task_type')
                )
            )
        ).filter(is_allowed=True).values_list('id', flat=True)
        
        default_ids = shared_ids.annotate(
            is_allowed=Exists(
                ShareSetting.objects.filter(
                    from_user=OuterRef('owner'),
                    to_user=user
                ).filter(
                    schedule_type__isnull=True
                )
            )
        ).filter(Q(is_allowed=True) & Q(task_type__isnull = True)).values_list('id', flat=True)
        
        allowed_shared_ids=typed_ids.union(default_ids)

        # 실제 일정은 annotate 없이 다시 가져오기
        shared_schedules = schedules.filter(id__in=allowed_shared_ids)

        # 공유 일정 합치기
        schedules = myschedules.union(shared_schedules)

    else:
        schedules = schedules.none()
    
    return schedules

def index(request):
    today = get_now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)

    schedules=allowed_schedules(
        Schedule.objects.filter(
            Q(deadline__year=year, deadline__month=month) |
            Q(start_time__year=year, start_time__month=month)
        ), request.user
    )

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
            if schedule.deadline and schedule.deadline.month == month:
                date_key = schedule.deadline.day
                schedule_map.setdefault(date_key, []).append(("deadline", schedule))

        # 시작일 기준 등록
        if schedule.start_time and not schedule.id in hidden_ids:
            if schedule.start_time and schedule.start_time.month == month:
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
            'year' : year,
            'month' : month,
            'owner_username': s.owner.username,
            'is_shared': s.owner != request.user,
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
            reference_date = get_now().date()
    else:
        reference_date = get_now().date()

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


    schedules = allowed_schedules(
        Schedule.objects, request.user
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
                'owner_username': s.owner.username,
                'is_shared': s.owner != request.user,
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
        'today': get_now().date(),
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
        datetime_str = request.GET.get('date')
        initial_data = {}
        if datetime_str:
            parsed_datetime = parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d-%H-%M")
            if parsed_datetime:
                initial_data['deadline'] = parsed_datetime
        form = ScheduleForm(initial=initial_data, owner=request.user)
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

@login_required(login_url='common:login')
def schedule_replace(request):
    data = Schedule.objects.filter(
        owner=request.user,
        is_done=False,
        is_fixed=False,
    ).filter(
        Q(deadline__gt=timezone.now()) |
        Q(deadline__isnull=True)
    ).order_by('deadline')
    
    default_start = get_now().strftime("%Y-%m-%dT%H:%M")
    default_end = (get_now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
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
        schedule_start = get_now()
        schedule_end = get_now() + timedelta(days=7)

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

    ai_result_raw = request.session.pop('ai_result_json', None)

    if not ai_result_raw:
        return redirect(request.META.get('HTTP_REFERER', 'calendar:index'))

    try:
        ai_result_list = json.loads(ai_result_raw)

        # ID별로 start_time만 추출
        id_to_start = {
            item['id']: (
                datetime.strptime(item['start_time'], '%Y-%m-%d %H:%M:%S')
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

@login_required
def share_settings(request):
    user = request.user
    schedule_types = ScheduleType.objects.filter(owner=user)
    all_users = User.objects.exclude(pk=user.pk)

    # POST 요청 처리
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_all":
            # 기존 공유 설정 전체 삭제 후 재생성
            ShareSetting.objects.filter(from_user=user).delete()

            for other_user in all_users:
                for st in schedule_types:
                    key = f"share_{other_user.id}_{st.id}"
                    if key in request.POST:
                        ShareSetting.objects.create(
                            from_user=user,
                            to_user=other_user,
                            schedule_type=st
                        )
                null_key = f"share_{other_user.id}_null"
                if null_key in request.POST:
                    ShareSetting.objects.create(
                        from_user=user,
                        to_user=other_user,
                        schedule_type=None
                    )
            messages.success(request, "공유 설정이 저장되었습니다.")
            return redirect('calendar:share_settings')
        elif action == "add_share":
            username = request.POST.get("new_user")
            st_id = request.POST.get("new_schedule_type")

            if not username:
                messages.error(request, "사용자 ID를 입력하세요.")
                return redirect('calendar:share_settings')
            if username == user.username:
                messages.error(request, "자기 자신에게는 공유할 수 없습니다.")
                return redirect('calendar:share_settings')
            
            try:
                target_user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, f"'{username}' 사용자 ID는 존재하지 않습니다.")
                return redirect('calendar:share_settings')

            if st_id == "__all__":
                for st in list(schedule_types) + [None]:
                    ShareSetting.objects.get_or_create(
                        from_user=user,
                        to_user=target_user,
                        schedule_type=st
                    )
                messages.success(request, f"{target_user.username} 사용자에게 모든 분류가 공유되었습니다.")
            elif st_id == "__default__":
                ShareSetting.objects.get_or_create(
                    from_user=user,
                    to_user=target_user,
                    schedule_type=None
                )
                messages.success(request, f"{target_user.username} 사용자에게 기본 분류가 공유되었습니다.")
            else:
                try:
                    st = ScheduleType.objects.get(pk=st_id, owner=user)
                    ShareSetting.objects.get_or_create(
                        from_user=user,
                        to_user=target_user,
                        schedule_type=st
                    )
                    messages.success(request, f"{target_user.username} 사용자에게 '{st.name}' 분류가 공유되었습니다.")
                except ScheduleType.DoesNotExist:
                    messages.error(request, "해당 일정 분류가 존재하지 않습니다.")

            return redirect('calendar:share_settings')
        elif action == "update_visible":
            selected_ids = request.POST.getlist("visible_users")

            # 기존 설정 삭제
            VisibleShare.objects.filter(user=user).delete()

            # 새로 설정된 대상 추가
            for uid in selected_ids:
                try:
                    target = User.objects.get(id=uid)
                    if ShareSetting.objects.filter(from_user=target, to_user=user).exists():  # 공유 받은 사용자만
                        VisibleShare.objects.create(user=user, target=target)
                except User.DoesNotExist:
                    continue

            messages.success(request, "표시할 일정이 업데이트되었습니다.")
            return redirect('calendar:share_settings')



    # GET 요청 또는 POST 후 재표시
    shared_settings = ShareSetting.objects.filter(from_user=user)
    shared_users = shared_settings.values_list("to_user", flat=True).distinct()
    shared_user_objs = User.objects.filter(id__in=shared_users)
    available_users = all_users.exclude(id__in=shared_users)

    # shared_map[user][schedule_type] = True/False
    shared_map = {}
    for u in shared_user_objs:
        shared_map[u] = {
            st: ShareSetting.objects.filter(from_user=user, to_user=u, schedule_type=st).exists()
            for st in schedule_types
        }
        shared_map[u][None]=ShareSetting.objects.filter(from_user=user, to_user=u, schedule_type=None).exists()

    incoming_shared_users = User.objects.filter(
        id__in=ShareSetting.objects.filter(to_user=user).values_list('from_user', flat=True).distinct()
    )
    visible_ids = set(VisibleShare.objects.filter(user=user).values_list('target_id', flat=True))
    
    context = {
        'schedule_types': schedule_types,
        'shared_users': shared_user_objs,
        'available_users': available_users,
        'shared_map': shared_map,
        'incoming_shared_users': incoming_shared_users,
        'visible_ids': visible_ids,
    }
    
    return render(request, 'calendar/share_settings.html', context)