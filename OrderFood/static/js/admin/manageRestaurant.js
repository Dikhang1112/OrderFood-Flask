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
