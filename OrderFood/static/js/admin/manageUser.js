// static/js/admin/manageUser.js
(function () {
  // ===== Helpers =====
  function findRow(el) {
    return el.closest(".rs-row") || el.closest("tr");
  }

  function setLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.dataset.originalTitle = btn.dataset.originalTitle || btn.title || "";
    btn.title = isLoading ? "Đang xử lý..." : btn.dataset.originalTitle;
    btn.style.opacity = isLoading ? "0.6" : "1";
  }

  async function callDelete(url) {
    const res = await fetch(url, {
      method: "DELETE",
      headers: { "Accept": "application/json" },
    });
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }
    return res.json().catch(() => ({}));
  }

  // ===== Event listener =====
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".rs-action--reject");
    if (!btn) return;

    e.stopPropagation();
    e.preventDefault();

    const row = findRow(btn);
    if (!row) return;

    const userId = btn.dataset.id;
    if (!userId) return;

    const role = btn.dataset.role?.trim().toUpperCase();

    if (!confirm(`Bạn có chắc muốn XÓA người dùng này?`)) return;

    setLoading(btn, true);

    try {
      let url = "";
      if (role === "CUSTOMER") {
        url = `/admin/${userId}/delete_customer`; // endpoint xóa customer
      } else if (role === "RESTAURANT_OWNER") {
        url = `/admin/${userId}/delete_owner`; // endpoint xóa owner
      } else {
        alert("Không thể xóa user này.");
        return;
      }

      await callDelete(url);

      // Xóa row khỏi table
      row.remove();
      window.Toast?.success?.("Xóa người dùng thành công!");
    } catch (err) {
      console.error(err);
      window.Toast?.error?.("Không thể xóa người dùng. Vui lòng thử lại.");
    } finally {
      setLoading(btn, false);
    }
  }, true);

  // ===== Tab switching =====
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
      const targetId = btn.dataset.target;
      document.getElementById(targetId).classList.add("active");
    });
  });

})();
