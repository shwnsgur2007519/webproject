import json
from datetime import datetime
from .schedule_relocation import schedule_relocation  # 상대경로 import

# 1. JSON 파일 불러오기
with open('./testjson.json', 'r', encoding='utf-8') as f:
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

