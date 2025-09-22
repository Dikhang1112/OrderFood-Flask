<<<<<<< HEAD
(function () {
  // Helper: Tìm <tr> chứa button
  function findRow(el) {
    return el.closest(".rs-row") || el.closest("tr");
  }

  // Helper: Cập nhật badge trạng thái trong hàng
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

  // Helper: Bật/tắt loading
  function setLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.dataset.originalTitle = btn.dataset.originalTitle || btn.title || "";
    btn.title = isLoading ? "Đang xử lý..." : btn.dataset.originalTitle;
    btn.style.opacity = isLoading ? "0.6" : "1";
  }

  // Gọi API PATCH (hỗ trợ gửi body JSON)
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

  // Lắng nghe click toàn trang (event delegation)
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".rs-action");
    if (!btn) return;

    const id = btn.getAttribute("data-id");
    if (!id) return;
    const row = findRow(btn);

    try {
      // REJECT: Confirm → Prompt lý do → PATCH
      if (btn.classList.contains("rs-action--reject")) {
        if (window.Toast && Toast.warningConfirm && Toast.warningPrompt) {
          // B1: Xác nhận
          Toast.warningConfirm("Bạn có chắc muốn từ chối nhà hàng này?", () => {
            // B2: Nhập lý do
            Toast.warningPrompt("Lí do", "Nhập lý do từ chối...", async (reason) => {
              try {
                setLoading(btn, true);
                const data = await callPatch(`/admin/restaurants/${id}/reject`, { reason });
                setStatusBadge(row, (data && data.status) || "REJECTED");
                Toast.success("Đã từ chối nhà hàng");
              } catch (err) {
                console.error(err);
                Toast.error("Không thể reject. Vui lòng thử lại.");
              } finally {
                setLoading(btn, false);
              }
            });
          });
        } else {
          // Fallback: confirm + prompt mặc định
          if (!confirm("Bạn có chắc muốn từ chối?")) return;
          const reason = prompt("Lí do từ chối:");
          if (reason == null || !reason.trim()) return;
          setLoading(btn, true);
          const data = await callPatch(`/admin/restaurants/${id}/reject`, { reason: reason.trim() });
          setStatusBadge(row, (data && data.status) || "REJECTED");
          if (window.Toast) Toast.success("Đã từ chối nhà hàng");
          setLoading(btn, false);
        }
        return;
      }

      // APPROVE (nếu đã có API)
      if (btn.classList.contains("rs-action--approve")) {
        setLoading(btn, true);
        const data = await callPatch(`/admin/restaurants/${id}/approve`);
        setStatusBadge(row, (data && data.status) || "APPROVED");
        if (window.Toast) Toast.success("Duyệt nhà hàng thành công");
        return;
      }
    } catch (err) {
      console.error(err);
      if (window.Toast) {
        Toast.error(err.message.includes("User cancelled") ? "Đã hủy thao tác" : "Không thể thực hiện. Vui lòng thử lại.");
      }
    } finally {
      setLoading(btn, false);
    }
  });
})();
=======
document.addEventListener("DOMContentLoaded", function () {
  // Approve
  document.querySelectorAll(".rs-action--approve").forEach(btn => {
    btn.addEventListener("click", function (ev) {
      ev.stopPropagation(); // không trigger click vào <tr>
      const id = this.dataset.id;
      fetch(`/admin/restaurants/${id}/approve`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" }
      })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          alert("Đã APPROVED nhà hàng #" + id);
          const row = this.closest("tr");
          if (row) {
            const badge = row.querySelector(".rs-badge");
            if (badge) {
              badge.textContent = "APPROVED";
              badge.className = "rs-badge rs-badge--ok";
            }
          }
        } else {
          alert("Lỗi: " + (data.error || "unknown"));
        }
      })
      .catch(err => console.error(err));
    });
  });

  // Reject
  document.querySelectorAll(".rs-action--reject").forEach(btn => {
    btn.addEventListener("click", function (ev) {
      ev.stopPropagation(); // không trigger click vào <tr>
      const id = this.dataset.id;
      fetch(`/admin/restaurants/${id}/reject`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" }
      })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          alert("Đã REJECTED nhà hàng #" + id);
          const row = this.closest("tr");
          if (row) {
            const badge = row.querySelector(".rs-badge");
            if (badge) {
              badge.textContent = "REJECTED";
              badge.className = "rs-badge rs-badge--err";
            }
          }
        } else {
          alert("Lỗi: " + (data.error || "unknown"));
        }
      })
      .catch(err => console.error(err));
    });
  });
});
>>>>>>> cffd1712d498615e18004bbbf9ec0f93949fdd08
