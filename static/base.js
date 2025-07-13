["showDone", "showDeadline", "showStart"].forEach(id => {
  const checkbox = document.getElementById(id);

  checkbox.addEventListener("change", () => {
    localStorage.setItem(id, checkbox.checked);  // ✅ 상태 저장
    reload();
  });
});

function restoreCheckboxStates() {
  ["showDone", "showDeadline", "showStart"].forEach(id => {
    const saved = localStorage.getItem(id);
    if (saved !== null) {
      document.getElementById(id).checked = (saved === "true");
    } else {
      // 초기값 true로 설정 (한 번도 저장된 적 없는 경우)
      document.getElementById(id).checked = true;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  restoreCheckboxStates();        // ✅ 체크박스 복원
  reload();
});



// CSRF 토큰 추출 함수
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

