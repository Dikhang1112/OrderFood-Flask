async function addDish() {
    const addDishForm = document.getElementById('addDishForm');

    addDishForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(addDishForm);
        let imageFile = document.getElementById('dishImage').files[0];
        let imageUrl = null;

        if (imageFile) {
            const cloudData = new FormData();
            cloudData.append('file', imageFile);
            cloudData.append('upload_preset', 'ml_default'); // tên preset unsigned của bạn

            try {
                const cloudRes = await fetch('https://api.cloudinary.com/v1_1/dlwjqml4p/image/upload', {
                    method: 'POST',
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

        // Thêm link image vào formData
        formData.append('image_url', imageUrl);

        // Gửi dữ liệu tới server
        try {
            const res = await fetch('/owner/add_dish', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                alert('Thêm món thành công');
               const collapse = bootstrap.Collapse.getInstance(addDishContainer);
                if (collapse) {
                    collapse.hide();
                }

                // 2. Reset form
                addDishForm.reset();

                // 3. Hiển thị món mới vào table
                const dish = data.dish;
                if (dishesTableBody) {
                    const newRow = document.createElement('tr');
                    newRow.classList.add('dish-row');
                    newRow.dataset.id = dish.dish_id;
                    newRow.dataset.name = dish.name;
                    newRow.dataset.note = dish.note;
                    newRow.dataset.price = dish.price;
                    newRow.dataset.category = dish.category;
                    newRow.dataset.image = dish.image;
                    newRow.dataset.active = dish.active ? '1' : '0';

                    newRow.innerHTML = `
                        <td class="text-center">${dish.name}</td>
                        <td class="text-center text-truncate" style="max-width:150px;">${dish.note || "Chưa có mô tả"}</td>
                        <td class="text-center">${dish.price}đ</td>
                        <td class="text-center">${dish.category || '-'}</td>
                        <td class="text-center">
                            <input type="checkbox" class="form-check-input" ${dish.active ? 'checked' : ''}>
                        </td>
                        <td class="text-center">
                            <button type="submit" class="btn btn-danger btn-sm middle">Xóa</button>
                        </td>
                    `;
                    dishesTableBody.appendChild(newRow);

                    // thêm sự kiện click để edit
                    newRow.addEventListener('click', () => {
                        const id = newRow.dataset.id;
                        const name = newRow.dataset.name;
                        const note = newRow.dataset.note;
                        const price = newRow.dataset.price;
                        const category = newRow.dataset.category;
                        const image = newRow.dataset.image;
                        const active = newRow.dataset.active === '1';

                        document.getElementById('editDishId').value = id;
                        document.getElementById('editName').value = name;
                        document.getElementById('editNote').value = note;
                        document.getElementById('editPrice').value = price;
                        document.getElementById('editCategory').value = category;
                        document.getElementById('editImagePreview').src = image || '';
                        document.getElementById('editActive').checked = active;

                        const editForm = new bootstrap.Collapse(document.getElementById('editDishForm'), { show: true });
                    });
                }
            } else {
                alert(data.error || 'Thêm món thất bại');
            }
        } catch (err) {
            console.error(err);
            alert('Lỗi server');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    addDish();
});
