from django.utils.timezone import make_aware
from django.utils import timezone
from datetime import datetime, timedelta, time
from .models import Schedule, ScheduleType
from django.contrib.auth.models import User
import os
import sys
import numpy as np
import random


def toSchedule(relocated_list):
    """
    schedule_relocation()이 반환한 dict 리스트를 받아,
    각 dict를 Schedule 인스턴스로 복원하여 리스트로 반환.
    """
    restored = []
    for data in relocated_list:
        # 1) ForeignKey 복원
        owner = User.objects.get(pk=data['owner_id'])
        task_type = None
        if data.get('task_type_id') is not None:
            task_type = ScheduleType.objects.get(pk=data['task_type_id'])
        exam = None
        if data.get('exam_id') is not None:
            exam = Schedule.objects.get(pk=data['exam_id'])

        # 2) DateTimeField 복원
        for dt_key in ('deadline', 'start_time', 'end_time'):
            dt_val = data.get(dt_key)
            if dt_val:
                data[dt_key] = datetime.strptime(dt_val, '%Y-%m-%d %H:%M:%S')
            else:
                data[dt_key] = None

        # 3) 나머지 필드 값을 꺼내서 Schedule 인스턴스 생성
        instance = Schedule(
            owner            = owner,
            task_name        = data.get('task_name'),
            duration_minutes = data.get('duration_minutes'),
            difficulty       = data.get('difficulty'),
            importance       = data.get('importance'),
            task_type        = task_type,
            subject          = data.get('subject'),
            is_exam_task     = data.get('is_exam_task', False),
            deadline         = data.get('deadline'),
            start_time       = data.get('start_time'),
            end_time         = data.get('end_time'),
            is_fixed         = data.get('is_fixed', False),
            exam             = exam,
            color            = data.get('color', '#6c8df5'),
            is_done          = data.get('is_done', False),
        )
        restored.append(instance)

    return restored


def toJson(instances):
    """
    Schedule 인스턴스 리스트를 JSON 직렬화 가능한 dict 리스트로 변환.
    datetime은 문자열로, None/기본값 포함 처리.
    """
    result = []
    for inst in instances:
        def dt_str(dt: datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None

        data = {
            'id':               inst.pk,
            'owner_id':         inst.owner_id,
            'task_name':        inst.task_name or '',
            'duration_minutes': inst.duration_minutes,
            'difficulty':       inst.difficulty,
            'importance':       inst.importance,
            'task_type_id':     inst.task_type_id,
            'subject':          inst.subject or '',
            'is_exam_task':     bool(inst.is_exam_task),
            'deadline':         dt_str(inst.deadline),
            'start_time':       dt_str(inst.start_time),
            'end_time':         dt_str(inst.end_time),
            'is_fixed':         bool(inst.is_fixed),
            'exam_id':          inst.exam_id,
            'color':            inst.color or '#6c8df5',
            'is_done':          bool(inst.is_done),
        }
        result.append(data)
    return result

import copy
def schedule_relocation(task_list_dup, schedule_start, schedule_end, available_times):

    # 1) 기본 설정
    state_dim   = 3
    action_dim  = len(task_list_dup)
    feature_dim = state_dim + action_dim
    task_list=copy.deepcopy(task_list_dup)
    
    for task in task_list:
        if not task.get("duration_minutes"):
            task["duration_minutes"] = 60

    try:
        start_time_str = available_times.get('start', '07:00')
        end_time_str = available_times.get('end', '22:00')
        start_t = datetime.strptime(start_time_str, '%H:%M').time()
        end_t = datetime.strptime(end_time_str, '%H:%M').time()
        if start_t > end_t:
            end_t
    except (ValueError, TypeError):
        # 형식에 맞지 않는 값이 들어올 경우를 대비한 최종 안전장치
        start_t = time(7, 0)
        end_t = time(22, 0)
    is_overnight = start_t > end_t

    if len(task_list) == 0:
        return "하나 이상의 일정을 선택해주세요."

    def get_feature(state, action, state_dim, action_dim):
        one_hot = np.zeros(action_dim, dtype=np.float32)
        one_hot[action] = 1.0
        return np.concatenate([state.astype(np.float32), one_hot])

    # 2) 학습된 가중치 불러오기
    weight_file = os.path.join(os.path.dirname(__file__), "trained_weights.npy")
    if os.path.exists(weight_file):
        w_loaded = np.load(weight_file)
        old_dim  = w_loaded.shape[0]
        if old_dim != feature_dim:
            w = np.zeros(feature_dim, dtype=np.float32)
            w[:min(old_dim, feature_dim)] = w_loaded[:min(old_dim, feature_dim)]
        else:
            w = w_loaded.astype(np.float32)
    else:
        raise FileNotFoundError(f"가중치 파일이 없습니다: {weight_file}")

    # 3) 스케줄 기간 정보 계산
    window_days    = (schedule_end.date() - schedule_start.date()).days + 1
    if is_overnight:
        # (자정까지의 시간) + (자정부터 종료시간까지의 시간)
        minutes_to_midnight = (24 * 60) - (start_t.hour * 60 + start_t.minute)
        minutes_from_midnight = end_t.hour * 60 + end_t.minute
        available_per_day = minutes_to_midnight + minutes_from_midnight
    else:
        # 일반 근무 시간 계산
        available_per_day = (end_t.hour - start_t.hour) * 60 + (end_t.minute - start_t.minute)

    available_minutes    = available_per_day * window_days
    # 4) 마감일 태스크 수집
    deadline_tasks = []
    for idx, t in enumerate(task_list):
        dl = t.get("deadline")
        if dl:
            dl_dt = datetime.strptime(dl, "%Y-%m-%d %H:%M:%S")
            due_offset = int((dl_dt - schedule_start).total_seconds() // 60)
            deadline_tasks.append((idx, t["duration_minutes"], due_offset))
    deadline_tasks.sort(key=lambda x: x[2])
    deadline_indices    = [idx for idx, _, _ in deadline_tasks]
    no_deadline_indices = [i for i, t in enumerate(task_list) if not t.get("deadline")]

    # 5) 추가 휴식 계산
    task_minutes = sum(t["duration_minutes"] for t in task_list)
    reserved_for_deadlines = len(deadline_indices) * 25
    remaining_time = available_minutes - task_minutes - reserved_for_deadlines
    if no_deadline_indices:
        max_additional_break = max(30, remaining_time // len(no_deadline_indices))
    else:
        max_additional_break = 10

    # 6) datetime 기반 앞배치 함수 정의
    def check_deadline_feasible_prefix(tasks, curr_dt):
        for idx, dur, due_offset in tasks:
            # 업무 시간 보정
            current_time = curr_dt.time()
            is_outside_hours = False
            if is_overnight:
                if start_t <= current_time or current_time < end_t:
                    is_outside_hours = False
                else:
                    is_outside_hours = True

            if is_outside_hours:
                if is_overnight:
                    if start_t <= current_time or current_time < end_t:
                        pass
                    elif current_time < start_t:
                        curr_dt = curr_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                    else:
                        curr_dt = (curr_dt + timedelta(days=1)).replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                else:
                    if start_t <= current_time <= end_t:
                        pass
                    elif current_time < start_t:
                        curr_dt = curr_dt.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                    else:
                        curr_dt = (curr_dt + timedelta(days=1)).replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)

            end_dt = curr_dt + timedelta(minutes=dur)
            due_dt = schedule_start + timedelta(minutes=due_offset)
            if end_dt > due_dt:
                return False

            curr_dt = end_dt + timedelta(minutes=10)  # 휴식 10분
        return True

    # 초기 검사: 모든 마감일 작업이 schedule_start부터 가능한지 확인
    if not check_deadline_feasible_prefix(deadline_tasks, schedule_start):
        print("❌ 모든 마감일 작업을 주어진 기간 내에 배치할 수 없습니다. 프로그램을 종료합니다.")
        return "일정을 배치할 수 없습니다."

    # 7) 예외 정의
    class NoValidTaskError(Exception):
        pass

    # 8) 환경 클래스 정의
    class SimpleScheduleEnv:
        def __init__(self, task_list, max_additional_break):
            self.task_list      = task_list
            self.total_actions  = len(task_list)
            self.schedule_start = schedule_start
            self.window_days    = window_days
            self.max_additional_break = max_additional_break
            self.deadline_indices     = deadline_indices

            self.due_date_offsets = []
            for t in task_list:
                dl = t.get("deadline")
                if dl:
                    dt = datetime.strptime(dl, "%Y-%m-%d %H:%M:%S")
                    self.due_date_offsets.append(int((dt - schedule_start).total_seconds() // 60))
                else:
                    self.due_date_offsets.append(None)

        def reset(self):
            self.idx           = 0
            self.schedule      = [-1] * self.total_actions
            self.scheduled_set = set()
            self.start_times   = []
            self.current_dt    = self.schedule_start
            self._enforce_business_hours(None)
            self.done          = False
            return self._get_state()

        def _enforce_business_hours(self, action):
            
            if action is not None:
                dur_ = self.task_list[action]["duration_minutes"]
                T=self.current_dt+timedelta(minutes=dur_)
            else:
                T=self.current_dt
            
            current_time = T.time()

            is_outside_hours = False

            if is_overnight:
                if end_t < current_time < start_t:
                    is_outside_hours = True
            else:
                if not (start_t <= current_time <= end_t):
                    is_outside_hours = True


            if is_outside_hours:
                if is_overnight:
                    if start_t <= current_time or current_time < end_t:
                        pass
                    elif current_time < start_t:
                        self.current_dt = T.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                    else:
                        self.current_dt = (T+ timedelta(days=1)).replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                else:
                    if start_t <= current_time <= end_t:
                        pass
                    elif current_time < start_t:
                        self.current_dt = T.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
                    else:
                        self.current_dt = (T + timedelta(days=1)).replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)



        def _get_state(self):
            rem      = self.total_actions - len(self.scheduled_set)
            tod_frac = (self.current_dt.hour * 60 + self.current_dt.minute) / 1440
            return np.array([self.idx / self.total_actions, rem / self.total_actions, tod_frac], dtype=np.float32)

        def step(self, action):
            if self.done:
                return self._get_state(), 0, True, {}

            self._enforce_business_hours(action)

            dur = self.task_list[action]["duration_minutes"]
            self.current_dt += timedelta(minutes=dur)
            work_end = self.current_dt

            # 휴식 시간: 마감일 작업이면 10,20,30분 랜덤, 아니면 최대 휴식 범위 내 10분 단위 랜덤
            if action in self.deadline_indices:
                break_min = random.choice([10, 20, 30])
            else:
                max_b = (self.max_additional_break // 10) * 10
                opts = list(range(30, max_b + 1, 10)) if max_b >= 30 else [30]
                break_min = random.choice(opts)
            self.current_dt += timedelta(minutes=break_min)

            due_off = self.due_date_offsets[action]
            if due_off is not None:
                due_dt = self.schedule_start + timedelta(minutes=due_off)
                start_dt = work_end - timedelta(minutes=dur)
                end_dt = work_end
                if start_dt > due_dt or end_dt > due_dt:
                    raise RuntimeError(f"작업[{action}] 마감일 초과")

            self.schedule[self.idx] = action
            self.scheduled_set.add(action)
            start_min = int((work_end - timedelta(minutes=dur) - self.schedule_start).total_seconds() // 60)
            self.start_times.append(start_min)

            self._enforce_business_hours(None)
            
            self.idx += 1
            if self.idx >= self.total_actions:
                self.done = True

            return self._get_state(), 0, self.done, {}

    # 9) 스케줄링 여러번 재시도
    max_trials = 100
    for trial in range(1, max_trials + 1):
        try:
            env = SimpleScheduleEnv(task_list, max_additional_break)
            state = env.reset()
            schedule, start_times = [], []

            while not env.done:
                valid = []
                rem_d = [a for a in deadline_indices if a not in env.scheduled_set]
                curr_min = int((env.current_dt - schedule_start).total_seconds() // 60)

                if rem_d:
                    for a in rem_d:
                        dur = task_list[a]["duration_minutes"]
                        off = env.due_date_offsets[a]
                        if off is not None and curr_min + dur > off:
                            continue
                        # 남은 마감 작업 중에서 현재 시간이후 마감인 작업만 검사
                        future_deadline_tasks = [
                            (i, task_list[i]["duration_minutes"], env.due_date_offsets[i])
                            for i in rem_d if i != a and curr_min + dur + 10 <= env.due_date_offsets[i]
                        ]
                        if not check_deadline_feasible_prefix(future_deadline_tasks, schedule_start + timedelta(minutes=curr_min + dur + 10)):
                            continue
                        valid.append(a)
                else:
                    valid = [a for a in no_deadline_indices if a not in env.scheduled_set]

                if not valid:
                    raise NoValidTaskError()
                
                q_vals = [-np.inf] * action_dim
                for a in valid:
                    phi = get_feature(state, a, state_dim, action_dim)
                    q_vals[a] = np.dot(w, phi)
                    
                    dl_str = task_list[a].get("deadline")
                    if dl_str:
                        dl_date = datetime.strptime(dl_str, "%Y-%m-%d %H:%M:%S").date()
                        if dl_date == env.current_dt.date():
                            q_vals[a] += 1000

                action = int(np.argmax(q_vals))

                state, _, done, _ = env.step(action)
                schedule.append(action)
                start_times.append(env.start_times[-1])

                if env.current_dt > schedule_end:
                    raise NoValidTaskError()

            print(f"✅ 시도 {trial} 성공적으로 스케줄링 완료!")
            break

        except NoValidTaskError:
            print(f"❌ 시도 {trial} 실패: 유효한 작업이 없습니다. 재시도합니다…")
        except RuntimeError as e:
            print(f"❌ 시도 {trial} 실패: {e}. 재시도합니다…")

    else:
        print(f"❌ {max_trials}번 모두 실패했습니다. 배치 불가")
        return "일정을 배치할 수 없습니다."

    # 10) 결과 출력 및 마감일 위반 검사
    violations = []
    for idx, sm in zip(schedule, start_times):
        t = task_list[idx]
        dl = t.get("deadline")
        st = schedule_start + timedelta(minutes=sm)
        en = st + timedelta(minutes=t["duration_minutes"])
        if dl:
            due_dt = datetime.strptime(dl, "%Y-%m-%d %H:%M:%S")
            if st > due_dt or en > due_dt:
                violations.append((t['subject'], t.get('task_type', 'N/A'), st, en, due_dt))

    for idx, sm in zip(schedule, start_times):
        t = task_list[idx]
        st = schedule_start + timedelta(minutes=sm)
        if st.time() < start_t:
            st = st.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
        en = st + timedelta(minutes=t["duration_minutes"])
        print(f"{st:%Y-%m-%d %H:%M} - {en:%H:%M}: {t['subject']} (타입: {t.get('task_type', 'N/A')})")

    if violations:
        print("\n=== 마감일 위반 작업 ===")
        for subj, typ, s, e, d in violations:
            print(f"{subj} (타입: {typ}) — 시작: {s:%Y-%m-%d %H:%M}, 종료: {e:%Y-%m-%d %H:%M}, 마감: {d:%Y-%m-%d %H:%M}")
    else:
        print("\n모든 작업이 마감일을 준수했습니다.")

    # 11) 결과 반환: 시작 시간 포함
    result = []
    for idx, sm in zip(schedule, start_times):
        t = task_list_dup[idx].copy()
        t["start_time"] = (schedule_start + timedelta(minutes=sm)).strftime("%Y-%m-%d %H:%M:%S")
        result.append(t)


    return result