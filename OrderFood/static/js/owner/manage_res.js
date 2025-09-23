// static/js/restaurant.js
document.addEventListener("DOMContentLoaded", () => {
    const saveBtn = document.getElementById("save-btn");
    const toggleBtn = document.getElementById("toggle-open");

    toggleBtn.addEventListener("change", () => {
        const statusLabel = document.getElementById("status-label");
        statusLabel.textContent = toggleBtn.checked ? "Mở cửa" : "Đóng cửa";
    });

    saveBtn.addEventListener("click", () => {
        const data = {
            name: document.getElementById("name").value,
            address: document.getElementById("address").value,
            open_hour: document.getElementById("open-hour").value,
            close_hour: document.getElementById("close-hour").value,
            is_open: document.getElementById("toggle-open").checked,
            tax: document.getElementById("tax").value
        };

        fetch("/owner/restaurant/update", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        })
        .then(res => res.json())
        .then(res => {
            if(res.success){
                alert("Cập nhật thành công!");
            } else {
                alert("Lỗi: " + res.error);
            }
        })
        .catch(err => alert("Lỗi server: " + err));
    });
});
