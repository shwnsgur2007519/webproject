document.addEventListener('keydown', function (event) {
  const path = window.location.pathname;

  // 주간 보기: /calendar/week/
  if (path.includes('/week/')) {
    if (event.key === 'ArrowLeft') {
      window.location.href = '?date=' + window.prev_date;
    } else if (event.key === 'ArrowRight') {
      window.location.href = '?date=' + window.next_date;
    }

  // 월간 보기: /calendar/ 또는 /calendar/index/
  } else if (path === '/calendar/' || path.includes('/calendar/index')) {
    if (event.key === 'ArrowLeft') {
      window.location.href = '?year=' + window.prev_year + '&month=' + window.prev_month;
    } else if (event.key === 'ArrowRight') {
      window.location.href = '?year=' + window.next_year + '&month=' + window.next_month;
    }
  }
});