async function registerRestaurant() {
    const form = document.getElementById("resRegisterForm");

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const formData = new FormData(form);

        // Upload ảnh lên Cloudinary (nếu có)
        let imageFile = document.getElementById("image").files[0];
        let imageUrl = null;
        if (imageFile) {
            const cloudData = new FormData();
            cloudData.append("file", imageFile);
            cloudData.append("upload_preset", "ml_default");

            try {
                const cloudRes = await fetch("https://api.cloudinary.com/v1_1/dlwjqml4p/image/upload", {
                    method: "POST",
                    body: cloudData
                });
                const cloudJson = await cloudRes.json();
                imageUrl = cloudJson.secure_url;
            } catch (err) {
                console.error("Lỗi upload Cloudinary:", err);
                alert("Không thể upload ảnh");
                return;
            }
        }

        formData.append("image_url", imageUrl);

        try {
            const res = await fetch("/owner/res_register", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            console.log("Response:", data); // để debug

            if (data.success) {
                alert("🎉 Đăng ký nhà hàng thành công! Đơn đang chờ duyệt.");
                window.location.href = "/owner";
            } else {
                alert(data.error || "Đăng ký thất bại");
            }
        } catch (err) {
            console.error("Lỗi server:", err);
            alert("Có lỗi khi gửi dữ liệu");
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    registerRestaurant();
});
