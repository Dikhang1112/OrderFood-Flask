// Sao chọn 1..n sẽ sáng 1..n
(function () {
  const wrap = document.querySelector('.rating-stars:not(.rating-readonly)');
  if (!wrap) return;
  const stars = Array.from(wrap.querySelectorAll('.star'));
  const input = document.getElementById('rating-input');

  function paint(n) {
    stars.forEach((s, i) => s.classList.toggle('on', i < n));
  }

  stars.forEach(btn => {
    btn.addEventListener('click', () => {
      const n = +btn.dataset.val;
      paint(n);
      input.value = n;
    });
    btn.addEventListener('mouseenter', () => paint(+btn.dataset.val));
    btn.addEventListener('mouseleave', () => paint(+input.value || 0));
  });
})();
