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
        Object.keys(item).forEach(key =>{
          li.dataset[key]=item[key];
        })
        
        li.onclick = () => openTaskDetail(li);
        listEl.appendChild(li);
      });
  }

  const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
  modal.show();
}



// ✅ DOM에 있는 일정 요소 숨김/표시
function updateVisibility() {
  const settings = getFilterSettings();

  document.querySelectorAll("[data-type='deadline']").forEach(el => {
    const isDone = el.dataset.is_done === "true";
    const should = settings.showDeadline && (!isDone || (isDone && settings.showDone));
    el.style.display = should ? "" : "none";
  });

  document.querySelectorAll("[data-type='start_time']").forEach(el => {
    const isDone = el.dataset.is_done === "true";
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
      div.dataset.day = day;
      Object.keys(item).forEach(key =>{
        div.dataset[key]=item[key];
      })
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
