(function () {
  // helper: tìm <tr> chứa button
  function findRow(el) {
    return el.closest(".rs-row") || el.closest("tr");
  }

  // helper: cập nhật badge trạng thái trong hàng
  function setStatusBadge(row, statusText) {
    const cell = row.querySelector(".rs-col--status") || row.querySelector("td:nth-child(4)");
    if (!cell) return;

    const map = {
      APPROVED: ["rs-badge rs-badge--ok", "APPROVED"],
      PENDING:  ["rs-badge rs-badge--warn", "PENDING"],
      REJECTED: ["rs-badge rs-badge--err", "REJECTED"]
    };
    const [cls, label] = map[statusText] || ["rs-badge", statusText];

    cell.innerHTML = `<span class="${cls}">${label}</span>`;
  }

  // helper: bật/tắt loading cho button
  function setLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.dataset.originalTitle = btn.dataset.originalTitle || btn.title || "";
    btn.title = isLoading ? "Đang xử lý..." : btn.dataset.originalTitle;
    btn.style.opacity = isLoading ? "0.6" : "1";
  }

  async function callPatch(url) {
    const res = await fetch(url, {
      method: "PATCH",
      headers: {
        "Accept": "application/json"
        // Nếu bạn dùng CSRF, thêm header X-CSRFToken ở đây
      }
    });
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }
    return res.json().catch(() => ({}));
  }

  // Click handler cho toàn trang
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".rs-action");
    if (!btn) return;

    const id = btn.getAttribute("data-id");
    if (!id) return;

    // Tìm dòng để cập nhật UI
    const row = findRow(btn);

   // REJECT
if (btn.classList.contains("rs-action--reject")) {
  // Thay confirm() bằng Toast.warning có nút xác nhận
  if (window.Toast && Toast.warningConfirm) {
    Toast.warningConfirm("Bạn có chắc muốn từ chối nhà hàng này?", async () => {
      try {
        setLoading(btn, true);
        const data = await callPatch(`/admin/restaurants/${id}/reject`);
        setStatusBadge(row, (data && data.status) || "REJECTED");
        Toast.success("Đã từ chối nhà hàng");
      } catch (err) {
        console.error(err);
        Toast.error("Không thể reject. Vui lòng thử lại.");
      } finally {
        setLoading(btn, false);
      }
    });
  } else {
    // fallback: confirm() như cũ
    const confirmReject = confirm("Từ chối nhà hàng này?");
    if (!confirmReject) return;
    try {
      setLoading(btn, true);
      const data = await callPatch(`/admin/restaurants/${id}/reject`);
      setStatusBadge(row, (data && data.status) || "REJECTED");
      if (window.Toast) Toast.success("Đã từ chối nhà hàng");
    } catch (err) {
      console.error(err);
      if (window.Toast) Toast.error("Không thể reject. Vui lòng thử lại.");
    } finally {
      setLoading(btn, false);
    }
  }
  return;
}
  });
})();
