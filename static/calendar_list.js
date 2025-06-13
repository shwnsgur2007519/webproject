
// ✅ 현재 체크박스 상태를 객체로 추출
function getFilterSettings() {
  return {
    showDone: document.getElementById("showDone").checked,
    showDeadline: document.getElementById("showDeadline").checked,
    showStart: document.getElementById("showStart").checked,
  };
}

// ✅ 설정 기반 필터 함수
function shouldShow(item, settings) {
  const isDone = item.is_done;
  const type = item.type;

  if (type === "deadline") {
    return settings.showDeadline && (!isDone || (isDone && settings.showDone));
  }

  if (type === "start_time") {
    return settings.showStart && (!isDone || (isDone && settings.showDone));
  }

  if (type === "ai_schedule") {
    return true;
  }
  return false;
}

// ✅ 모달 렌더링
function openScheduleModal(el) {
  const day = el.getAttribute('data-day');
  const listEl = document.getElementById('scheduleModalList');
  listEl.innerHTML = '';

  const settings = getFilterSettings();

  if (window.scheduleData && scheduleData[day]) {
    scheduleData[day]
      .filter(item => shouldShow(item, settings))
      .forEach(item => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.role = 'button';
        li.style.backgroundColor = item.type === "start_time" || item.type === "ai_schedule" ? (item.is_done === true ? "#4677be" :"#0d6efd") : item.color;
        li.style.webkitTextFillColor = 'white';
        
        insert_text(item, li);
        
        // 데이터 추가
        li.dataset.task = item.task_name;
        li.dataset.subject = item.subject;
        li.dataset.deadline = item.deadline;
        li.dataset.fixed = item.is_fixed;
        li.dataset.exam = item.is_exam_task;
        li.dataset.id = item.id;
        li.dataset.owner = item.owner_id;
        li.dataset.done = item.is_done;
        li.dataset.task_type = item.task_type;
        li.dataset.duration_minutes= item.duration_minutes;
        li.dataset.start_time= item.start_time;
        
        li.onclick = () => openTaskDetail(li);
        listEl.appendChild(li);
      });
  }

  const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
  modal.show();
}

// ✅ 상세 보기
function openTaskDetail(el) {
  document.getElementById("taskDetailModalLabel").textContent = insert_text_detail(el.dataset);
  // document.getElementById("detailSubject").textContent = el.dataset.subject || '없음';
  document.getElementById("detailDeadline").textContent = el.dataset.deadline || '없음';
  document.getElementById("detailstartiime").textContent = el.dataset.start_time || '없음';
  document.getElementById("detailFixed").textContent = el.dataset.fixed === "true" ? "예" : "아니오";
  document.getElementById("detailExam").textContent = el.dataset.exam === "true" ? "예" : "아니오";
  if(el.dataset.duration_minutes !== undefined && el.dataset.duration_minutes !== 'null') {
    document.getElementById("detailTime").textContent = el.dataset.duration_minutes;
  }
  else {
    document.getElementById("detailTime").textContent = "없음";
  }
  
  const id = el.dataset.id;
  const editLink = document.getElementById("editTaskLink");
  editLink.href = `/calendar/schedule/${id}/edit/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
  editLink.classList.remove("d-none");
  const isDone = el.dataset.done === "true";

  const doneBtn = document.getElementById("markDoneBtn");
  const undoneBtn = document.getElementById("unmarkDoneBtn");
  const Editbtn = document.getElementById("editbuttons");

  if (!window.hasAISession) {
    Editbtn.classList.remove("d-none");
    if (isDone) {
      doneBtn.classList.add("d-none");
      undoneBtn.classList.remove("d-none");
    } else {
      doneBtn.classList.remove("d-none");
      undoneBtn.classList.add("d-none");
    }
  }
  else{
    Editbtn.classList.add("d-none");
  }


  const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
  modal.show();
}

// ✅ DOM에 있는 일정 요소 숨김/표시
function updateVisibility() {
  const settings = getFilterSettings();

  document.querySelectorAll("[data-type='deadline']").forEach(el => {
    const isDone = el.dataset.done === "true";
    const should = settings.showDeadline && (!isDone || (isDone && settings.showDone));
    el.style.display = should ? "" : "none";
  });

  document.querySelectorAll("[data-type='start_time']").forEach(el => {
    const isDone = el.dataset.done === "true";
    const should = settings.showStart && (!isDone || (isDone && settings.showDone));
    el.style.display = should ? "" : "none";
  });

  document.querySelectorAll("[data-type='ai_schedule']").forEach(el => {
    el.style.display = "";
  });
}

function updateMoreLinks() {
  document.querySelectorAll('.schedule-more').forEach(div => {
    const day = div.dataset.day;
    const all = scheduleData[day] || [];
    const visible = all.filter(shouldShow);
    


    // 3개 이하면 숨김
    if (visible.length <= 3) {
      div.style.display = 'none';
    } else {
      div.style.display = '';
      const moreCount = visible.length - 3;
      div.querySelector('a').textContent = `+${moreCount}개 더보기`;
    }
  });
}


function updateFilterState() {
  window.showDone = document.getElementById("showDone").checked;
  window.showDeadline = document.getElementById("showDeadline").checked;
  window.showStart = document.getElementById("showStart").checked;
}

// 스케줄 렌더링
function renderSchedules() {
  const settings = getFilterSettings();

  for (const day in scheduleData) {
    const cell = document.getElementById("cell-" + day);
    if (!cell) continue;

    cell.innerHTML = ""; // 셀 초기화

    const visibleItems = scheduleData[day].filter(item => shouldShow(item, settings));

    // 4개 이하: 모두, 5개 이상: 앞의 3개만
    const previewItems = visibleItems.length <= 4
      ? visibleItems
      : visibleItems.slice(0, 3);

    // 일정 출력
    previewItems.forEach(item => {
      const div = document.createElement("div");
      div.className = "text-white rounded px-0 py-0 small text-truncate w-100";
      div.style.backgroundColor = 
        (item.type === "start_time" || item.type === "ai_schedule")
          ? (item.is_done ? "#4677be" : "#0d6efd")
          : item.color;
      // data-* 속성 추가
      div.dataset.type = item.type;
      div.dataset.done = item.is_done;
      div.dataset.day = day;
      div.dataset.id = item.id;
      div.dataset.task = item.task_name;
      div.dataset.subject = item.subject;
      div.dataset.deadline = item.deadline;
      div.dataset.fixed = item.is_fixed;
      div.dataset.exam = item.is_exam_task;
      div.dataset.owner = item.owner_id;
      div.dataset.task_type = item.task_type;
      div.dataset.duration_minutes= item.duration_minutes;
      div.dataset.start_time= item.start_time;
      div.setAttribute("role", "button");
      div.setAttribute("onclick", "openTaskDetail(this)");
      insert_text(item, div);
      cell.appendChild(div);
    });

    // 5개 이상일 때만 +N개 더보기 추가
    if (visibleItems.length >= 5) {
      const moreDiv = document.createElement("div");
      moreDiv.className = "text-muted small text-end w-100 schedule-more";
      moreDiv.dataset.day = day;

      const a = document.createElement("a");
      a.href = "#";
      a.className = "text-decoration-none";
      a.textContent = `+${visibleItems.length - 3}개 더보기`;
      a.setAttribute("data-day", day);
      a.setAttribute("onclick", "openScheduleModal(this)");

      moreDiv.appendChild(a);
      cell.appendChild(moreDiv);
    }
  }
}


function reload(){
  updateVisibility(); // DOM 숨김
  renderSchedules();  // 전체 다시 그리기
}

["showDone", "showDeadline", "showStart"].forEach(id => {
  document.getElementById(id).addEventListener("change", () => {
    reload();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  reload();
});
