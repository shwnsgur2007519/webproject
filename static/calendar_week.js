// 일정 모두 제거
function clearWeekSchedule() {
  for (const day in scheduleData) {
    scheduleData[day].forEach(item => {
      const dt = item.type === "start_time" || item.type === "ai_schedule" ? item.start_time : item.deadline;
      const dateObj = new Date(dt);
      const hour = dateObj.getHours().toString().padStart(2, '0');
      const cellId = `cell-${day}-${hour}`;
      const cell = document.getElementById(cellId);
      if (cell) cell.innerHTML = "";
    });
  }
}

// 일정 렌더링
function renderWeekSchedule() {
  const settings = getFilterSettings();

  for (const day in scheduleData) {
    scheduleData[day].forEach(item => {
      if (!shouldShow(item, settings)) return;
      const dt = item.type === "start_time" || item.type === "ai_schedule" ? item.start_time : item.deadline;
      const dateObj = new Date(dt);
      const hour = dateObj.getHours().toString().padStart(2, '0');
      const cellId = `cell-${day}-${hour}`;
      const cell = document.getElementById(cellId);
      if (!cell) return;

      const div = document.createElement("div");
      div.className = "text-white rounded px-1 py-1 small text-truncate w-100 my-1";
      div.style.backgroundColor = item.type === "start_time" || item.type === "ai_schedule" ? (item.is_done === true ? "#4677be" :"#0d6efd") : (item.is_shared ? "#555555ff" : item.color);
      
      insert_text(item, div);

      div.setAttribute("role", "button");
      div.setAttribute("onclick", "openTaskDetail(this)");
      
      Object.keys(item).forEach(key =>{
        div.dataset[key]=item[key];
      })
      
      cell.appendChild(div);
    });
  }
}


function reload(){
    clearWeekSchedule();
    renderWeekSchedule();
}

// ✅ 초기화 및 이벤트 연결
document.addEventListener("DOMContentLoaded", () => {
  renderWeekSchedule();

  ["showDone", "showDeadline", "showStart"].forEach(id => {
    document.getElementById(id).addEventListener("change", () => {
        reload();
    });
  });
});
