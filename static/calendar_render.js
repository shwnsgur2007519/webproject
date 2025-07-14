function insert_text(item, div){  
  if(item.type === "start_time")
  {
    if(item.is_done === true){
      const del=document.createElement('del');
      div.appendChild(del);
      if(item.task_type !== "None")
        del.textContent=`✓ [${item.task_type}] ${item.task_name}`;
      else
        del.textContent=`✓ ${item.task_name}`;
    }
    else{
      if(item.task_type !== "None")
        div.textContent = `✓ [${item.task_type}] ${item.task_name}`;
      else
        div.textContent = `✓ ${item.task_name}`;
    }
  }
  else if(item.type === "ai_schedule"){
    div.textContent = `[AI 제안] ${item.task_name}`;
  }
  else if(item.type === "deadline"){
    if(item.task_type !== "None"){
      div.textContent = `[${item.task_type}] ${item.task_name}`;
    }
    else{
      div.textContent = `${item.task_name}`;
    }
  }
}

function insert_text_detail(item){  
  if(item.task_type === "None")
    return item.task_name;
  else return `[${item.task_type}] ${item.task_name}`
}

function getFilterSettings() {
  return {
    showDone: document.getElementById("showDone").checked,
    showDeadline: document.getElementById("showDeadline").checked,
    showStart: document.getElementById("showStart").checked,
  };
}

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

//상세 보기
function openTaskDetail(el) {
  document.getElementById("taskDetailModalLabel").textContent = insert_text_detail(el.dataset);
  document.getElementById("detailDeadline").textContent = el.dataset.deadline || '없음';
  document.getElementById("detailstarttime").textContent = el.dataset.start_time || '없음';
  document.getElementById("detailFixed").textContent = el.dataset.fixed === "true" ? "예" : "아니오";
  document.getElementById("detailExam").textContent = el.dataset.exam === "true" ? "예" : "아니오";
  if(el.dataset.is_shared === "true"){
    document.getElementById("detailOwner").parentElement.classList.remove("d-none");
    document.getElementById("detailOwner").textContent = el.dataset.owner_username;
  }
  else{
    document.getElementById("detailOwner").parentElement.classList.add("d-none");
  }

  if(el.dataset.duration_minutes !== undefined && el.dataset.duration_minutes !== 'null') {
    document.getElementById("detailTime").textContent = el.dataset.duration_minutes;
  }
  else {
    document.getElementById("detailTime").textContent = "없음";
  }
  
  const id = el.dataset.id;
  const editLink = document.getElementById("editTaskLink");
  editLink.href = `/calendar/schedule/${id}/edit/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
  const isDone = el.dataset.is_done === "true";

  const doneBtn = document.getElementById("markDoneBtn");
  const undoneBtn = document.getElementById("unmarkDoneBtn");
  const Editbtn = document.getElementById("editbuttons");

  if (!window.hasAISession && el.dataset.is_shared === "false") {
    Editbtn.classList.remove("d-none");
    if (isDone) {
      doneBtn.classList.add("d-none");
      undoneBtn.classList.remove("d-none");
    } else {
      doneBtn.classList.remove("d-none");
      undoneBtn.classList.add("d-none");
    }
    console.log(isDone);
  }
  else{
    Editbtn.classList.add("d-none");
  }

  const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
  modal.show();
}

// 완료 버튼 처리
document.getElementById('markDoneBtn').addEventListener('click', async function () {
  const id = document.getElementById('editTaskLink').href.split('/schedule/')[1].split('/')[0];
  try {
    const response = await fetch(`/calendar/schedule/${id}/mark_done/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });

    if (response.ok) {
      // 일정 데이터 갱신
      const modal = bootstrap.Modal.getInstance(
        document.getElementById('taskDetailModal')
      );
      modal.hide();
      location.reload();
      // ✅ 일정 새로 렌더링
    } else {
      alert('완료 처리 실패');
    }
  } catch (e) {
    alert('오류 발생: ' + e);
  }
  reload();
  location.reload();
});

// 미완료 버튼 처리
document.getElementById("unmarkDoneBtn").addEventListener("click", async function () {
  const id = document.getElementById("editTaskLink").href.split("/schedule/")[1].split("/")[0];

  try {
    const response = await fetch(`/calendar/schedule/${id}/unmark_done/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        "Content-Type": "application/json"
      },
      body: JSON.stringify({})
    });

    if (response.ok) {
      const modal = bootstrap.Modal.getInstance(document.getElementById("taskDetailModal"));
      modal.hide();
      location.reload();  // 또는 renderWeekSchedule();
    } else {
      alert("미완료 처리 실패");
    }
  } catch (e) {
    alert("오류 발생: " + e);
  }
});