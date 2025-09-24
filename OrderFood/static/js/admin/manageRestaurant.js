// static/js/admin/manageRestaurant.js
(function () {
  // ===== Helpers =====
  function findRow(el) {
    return el.closest(".rs-row") || el.closest("tr");
  }

  function setStatusBadge(row, statusText) {
    const cell = row.querySelector(".rs-col--status") || row.querySelector("td:nth-child(4)");
    if (!cell) return;
    const map = {
      APPROVED: ["rs-badge rs-badge--ok", "APPROVED"],
      PENDING:  ["rs-badge rs-badge--warn", "PENDING"],
      REJECTED: ["rs-badge rs-badge--err", "REJECTED"],
      REJECT:   ["rs-badge rs-badge--err", "REJECT"]
    };
    const [cls, label] = map[statusText] || ["rs-badge", statusText];
    cell.innerHTML = `<span class="${cls}">${label}</span>`;
  }

  function setLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.dataset.originalTitle = btn.dataset.originalTitle || btn.title || "";
    btn.title = isLoading ? "Đang xử lý..." : btn.dataset.originalTitle;
    btn.style.opacity = isLoading ? "0.6" : "1";
  }

  async function callPatch(url, payload) {
    const res = await fetch(url, {
      method: "PATCH",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: payload ? JSON.stringify(payload) : null
    });
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }
    return res.json().catch(() => ({}));
  }

  document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".rs-action");
  if (!btn) return;

  e.stopPropagation();
  e.preventDefault();

  const id = btn.getAttribute("data-id");
  if (!id) return;
  const row = btn.closest(".rs-row") || btn.closest("tr");

  try {
    if (btn.classList.contains("rs-action--reject")) {
      if (!confirm("Bạn có chắc muốn TỪ CHỐI nhà hàng này?")) return;
      const reason = prompt("Lí do từ chối:");
      if (reason == null || !reason.trim()) return;

      setLoading(btn, true);
      const data = await callPatch(`/admin/restaurants/${id}/reject`, { reason: reason.trim() });
      setStatusBadge(row, (data && data.status) || "REJECTED");
      window.Toast?.success?.("Đã từ chối nhà hàng");
      return;
    }

    if (btn.classList.contains("rs-action--approve")) {
      if (!confirm("Bạn có chắc muốn DUYỆT nhà hàng này?")) return;  // <--- thêm dòng này
      setLoading(btn, true);
      const data = await callPatch(`/admin/restaurants/${id}/approve`);
      setStatusBadge(row, (data && data.status) || "APPROVED");
      window.Toast?.success?.("Duyệt nhà hàng thành công");
      return;
    }
  } catch (err) {
    console.error(err);
    window.Toast?.error?.("Không thể thực hiện. Vui lòng thử lại.");
  } finally {
    setLoading(btn, false);
  }
}, true);
})();
