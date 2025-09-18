(function () {
  const BASE = "/admin/restaurants"; // /admin blueprint prefix

  // Toast helper (fallback -> alert)
  function toast(msg, type = "info") {
    if (window.showToast) return window.showToast(msg, type);
    alert(msg);
  }

  // Đổi trạng thái badge trong bảng
  function updateRowStatus(row, statusText) {
    const cell = row.querySelector(".rs-col--status");
    if (!cell) return;
    let badge = cell.querySelector(".rs-badge");
    if (!badge) {
      badge = document.createElement("span");
      cell.innerHTML = "";
      cell.appendChild(badge);
    }
    badge.className = "rs-badge";
    const cls =
      statusText === "APPROVED" ? "rs-badge--ok"
      : statusText === "PENDING" ? "rs-badge--warn"
      : "rs-badge--err";
    badge.classList.add(cls);
    badge.textContent = statusText;
  }

  // Disable/enable button trong lúc gọi API
  function setBusy(btn, busy) {
    if (!btn) return;
    btn.disabled = !!busy;
    btn.style.opacity = busy ? ".6" : "";
  }

  async function doPatch(url, body, btn) {
    try {
      setBusy(btn, true);
      const res = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
        body: body ? JSON.stringify(body) : null,
        credentials: "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
      return data;
    } finally {
      setBusy(btn, false);
    }
  }

  // Event delegation cho 2 nút Action
  document.addEventListener("click", async (e) => {
    const approveBtn = e.target.closest(".rs-action--approve");
    const rejectBtn  = e.target.closest(".rs-action--reject");
    if (!approveBtn && !rejectBtn) return;

    const row = (approveBtn || rejectBtn).closest(".rs-row");
    const id  = row?.getAttribute("data-id");
    if (!id) return;

    try {
      if (approveBtn) {
        const url = `${BASE}/${id}/approve`;
        const data = await doPatch(url, null, approveBtn);
        updateRowStatus(row, data.status || "APPROVED");
        toast(`Đã duyệt nhà hàng #${id}`, "success");
      } else if (rejectBtn) {
        const reason = (prompt("Nhập lý do từ chối (tuỳ chọn):") || "").trim();
        const url = `${BASE}/${id}/reject`;
        const data = await doPatch(url, { reason }, rejectBtn);
        updateRowStatus(row, data.status || "REJECTED");
        toast(`Đã từ chối nhà hàng #${id}`, "warning");
      }
    } catch (err) {
      console.error(err);
      toast(`Lỗi: ${err.message || err}`, "error");
    }
  });
})();
