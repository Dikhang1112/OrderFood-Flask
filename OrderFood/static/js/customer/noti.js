// static/js/noti.js
(function () {
  const BTN   = document.getElementById('notiBellBtn');     // nút chuông
  const MENU  = document.getElementById('notiDropdown');    // menu dropdown
  const LIST  = document.getElementById('notiList');        // list container
  const BADGE = document.getElementById('notiBadge');       // số chưa đọc

  function setBadge(unread) {
    const n = Number(unread || 0);
    if (!BADGE) return;
    BADGE.textContent = n ? String(n) : '';
    BADGE.classList.toggle('d-none', n === 0);
  }

  function renderNotis(payload) {
    if (!payload || !Array.isArray(payload.items)) return;

    setBadge(payload.unread);

    LIST.innerHTML = payload.items.map(n => `
      <a href="#" class="noti-item ${n.is_read ? 'read' : 'unread'}"
         data-id="${n.id}" data-unread="${n.is_read ? '0' : '1'}"
         data-url="${n.target_url}">
        <div class="fw-semibold">${n.message}</div>
        <div class="noti-time">#${n.order_id} • ${n.create_at}</div>
      </a>
    `).join('') || `<div class="px-3 py-3 text-muted">Không có thông báo</div>`;
  }

  async function loadNotis() {
    try {
      const res = await fetch('/notifications/feed', { credentials: 'same-origin' });
      if (!res.ok) return;
      renderNotis(await res.json());
    } catch (err) {
      console.error('loadNotis failed', err);
    }
  }

  // Khi dropdown SẮP mở, gọi load
  BTN?.addEventListener('show.bs.dropdown', loadNotis);

  // Click 1 item: mark read (không xóa) rồi điều hướng
  LIST?.addEventListener('click', async (e) => {
    const a = e.target.closest('.noti-item');
    if (!a) return;
    e.preventDefault();

    const id = a.dataset.id;
    try {
      await fetch(`/notifications/mark-read/${id}`, { method: 'POST', credentials: 'same-origin' });
      if (a.dataset.unread === '1') {
        a.classList.remove('unread');
        a.classList.add('read');
        a.dataset.unread = '0';
        const cur = parseInt(BADGE?.textContent || '0', 10) || 0;
        setBadge(Math.max(0, cur - 1));
      }
    } catch (err) {
      console.error('mark-read failed', err);
    }

    const url = a.dataset.url;
    if (url) window.location.href = url;
  });

  // Đánh dấu tất cả đã đọc
  document.getElementById('markAllRead')?.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
      await fetch('/notifications/mark-all-read', { method: 'POST', credentials: 'same-origin' });
      LIST.querySelectorAll('.noti-item').forEach(a => {
        a.classList.remove('unread');
        a.classList.add('read');
        a.dataset.unread = '0';
      });
      setBadge(0);
    } catch (err) {
      console.error('mark-all-read failed', err);
    }
  });
})();
