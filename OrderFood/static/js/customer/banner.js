
(function () {
  function ready(fn){ document.readyState !== 'loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }

  ready(function () {
    const wrap  = document.getElementById('bannerCarousel');
    if (!wrap) return;

    // Nhận cấu hình từ data-attributes
    let files = [];
    try { files = JSON.parse(wrap.dataset.files || '[]'); } catch (_) { files = []; }
    const staticBase = (wrap.dataset.static || '/static/img/').replace(/\/?$/, '/');

    const inner = document.getElementById('bannerInner');
    const inds  = document.getElementById('bannerIndicators');
    if (!inner || !inds) return;

    // Không có file nào → ẩn
    if (!files.length) { wrap.style.display = 'none'; return; }

    // Dựng slide + indicators
    files.forEach((name, i) => {
      const src = staticBase + name;
      // indicator
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('data-bs-target', '#bannerCarousel');
      btn.setAttribute('data-bs-slide-to', String(i));
      btn.setAttribute('aria-label', 'Slide ' + (i + 1));
      if (i === 0) { btn.classList.add('active'); btn.setAttribute('aria-current', 'true'); }
      inds.appendChild(btn);

      // slide
      const item = document.createElement('div');
      item.className = 'carousel-item' + (i === 0 ? ' active' : '');
      const img = document.createElement('img');
      img.className = 'd-block w-100 banner-img';
      img.alt = 'Banner ' + (i + 1);
      img.src = src;

      // Nếu ảnh lỗi → gỡ slide + indicator
      img.onerror = () => {
        const indicator = inds.querySelector(`[data-bs-slide-to="${i}"]`);
        if (indicator) indicator.remove();
        const wasActive = item.classList.contains('active');
        item.remove();
        if (wasActive && inner.firstElementChild) inner.firstElementChild.classList.add('active');
        // Nếu hết slide → ẩn
        if (!inner.children.length) wrap.style.display = 'none';
      };

      item.appendChild(img);
      inner.appendChild(item);
    });

    // Khởi tạo carousel nếu có Bootstrap bundle
    if (window.bootstrap && typeof window.bootstrap.Carousel === 'function' && inner.children.length) {
      new bootstrap.Carousel(wrap, {
        interval: 1500,
        ride: 'carousel',
        pause: 'hover',
        touch: true,
        wrap: true
      });
    } else if (!window.bootstrap) {
      console.error('Bootstrap bundle chưa được nạp. Thêm bootstrap.bundle.min.js trước banner.js');
    }
  });
})();
