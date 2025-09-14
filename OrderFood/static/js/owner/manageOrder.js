(function () {

  function findRow(el) {
    return el.closest("li.list-group-item") || el.closest("tr");
  }

  function setLoading(btn, isLoading) {
    if (!btn) return;
    btn.disabled = isLoading;
    btn.dataset.originalTitle = btn.dataset.originalTitle || btn.title || "";
    btn.title = isLoading ? "Đang xử lý..." : btn.dataset.originalTitle;
    btn.style.opacity = isLoading ? "0.6" : "1";
  }

  // Duyệt đơn
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".approve-order-btn");
    if (!btn) return;

    const orderId = btn.dataset.orderId;
    if (!orderId) return;

    const row = findRow(btn);
    try {
      setLoading(btn, true);
      const res = await fetch(`/owner/orders/${orderId}/approve`, {
        method: "POST",
        headers: { "Accept": "application/json" }
      });
      const data = await res.json();
      if (!res.ok || data.status !== "ACCEPTED") throw new Error(data.error || "Không thể duyệt đơn");

      row.style.transition = "opacity 0.3s";
      row.style.opacity = 0;
      setTimeout(() => row.remove(), 350);

      const approvedTab = document.querySelector("#approved ul.list-group");
      if (approvedTab) {
        const li = document.createElement("li");
        li.className = "list-group-item";
        let itemsHTML = "";
        if (data.items) itemsHTML = data.items.map(i => `- ${i.name} x ${i.quantity}`).join("<br>");
        li.innerHTML = `
          <div>Đơn #${data.order_id} - ${data.customer_name} - ${data.total_price} VNĐ</div>
          <div style="margin-top: 5px;">
            <strong>Sản phẩm:</strong><br>${itemsHTML}
          </div>
          <span class="order-status-badge"><span class="badge bg-info">Đã duyệt</span></span>
        `;
        approvedTab.appendChild(li);
      }

      if (window.Toast) Toast.success("Đã duyệt đơn!");
    } catch (err) {
      console.error(err);
      if (window.Toast) Toast.error(err.message);
    } finally {
      setLoading(btn, false);
    }
  });

  // Hủy đơn
  // Hủy đơn
document.addEventListener("submit", async (e) => {
  const form = e.target.closest("form");
  if (!form || !form.classList.contains("cancel-order-form")) return;
  e.preventDefault();

  const orderId = form.dataset.orderId;
  const reason = form.querySelector("textarea[name='reason']").value.trim();
  const btn = form.querySelector("button[type=submit]");
  const row = form.closest("li.list-group-item");

  try {
    setLoading(btn, true);

    const res = await fetch(`/owner/orders/${orderId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ reason })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Không thể hủy đơn");

    // Ẩn row tab Pending
    row.style.transition = "opacity 0.3s";
    row.style.opacity = 0;
    setTimeout(() => row.remove(), 350);

    // Append vào tab Cancelled
    const cancelledTab = document.querySelector("#cancelled ul.list-group");
    if (cancelledTab) {
      const li = document.createElement("li");
      li.className = "list-group-item";
      li.innerHTML = `
        Đơn #${data.order_id} - ${data.customer_name} - <span class="text-danger">Đã hủy</span>
        <br><small><strong>Lý do:</strong> ${data.reason}</small>
      `;
      cancelledTab.appendChild(li);
    }

    if (window.Toast) Toast.success("Đã hủy đơn!");
  } catch (err) {
    console.error(err);
    if (window.Toast) Toast.error(err.message);
  } finally {
    setLoading(btn, false);
  }
});
})();