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


                // 4. Hiển thị category mới
                if (dish.category) {
                    const exists = Array.from(categorySelect.options)
                                        .some(opt => opt.value === dish.category);
                    if (!exists) {
                        const newOpt = document.createElement('option');
                        newOpt.value = dish.category;
                        newOpt.textContent = dish.category;
                        // Thêm trước option "Thêm mới" (giữ option "new" ở cuối)
                        const newOption = categorySelect.querySelector('option[value="new"]');
                        categorySelect.insertBefore(newOpt, newOption);
                    }
                }

                //5. Ẩn input thêm cate

                newCategoryInput.classList.add('d-none');
                newCategoryInput.required = false;
                newCategoryInput.value = "";
                categorySelect.value = dish.category || "";

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




let currentRowId = null;

document.querySelectorAll('.dish-row').forEach(row => {
    row.addEventListener('click', () => {
        const id = row.dataset.id;
        const name = row.dataset.name;
        const note = row.dataset.note;
        const price = row.dataset.price;
        const category = row.dataset.category;
        const image = row.dataset.image;
        const active = row.dataset.active === '1';

        const editFormEl = document.getElementById('editDishForm');
        const collapse = bootstrap.Collapse.getOrCreateInstance(editFormEl);

        if (currentRowId === id && editFormEl.classList.contains('show')) {
            // Click lại cùng row -> ẩn form
            collapse.hide();
            currentRowId = null;
            return;
        }

        // Cập nhật dữ liệu vào form
        document.getElementById('editDishId').value = id;
        document.getElementById('editName').value = name;
        document.getElementById('editNote').value = note;
        document.getElementById('editPrice').value = price;
        document.getElementById('editCategory').value = category;
        document.getElementById('editImagePreview').src = image || '';
        document.getElementById('editActive').checked = active;

        // Hiển thị form
        collapse.show();
        currentRowId = id;
    });
});




    const categorySelect = document.getElementById('categorySelect');
const newCategoryInput = document.getElementById('newCategoryInput');

categorySelect.addEventListener('change', () => {
    if(categorySelect.value === "new"){
        newCategoryInput.classList.remove('d-none');
        newCategoryInput.required = true;
    } else {
        newCategoryInput.classList.add('d-none');
        newCategoryInput.required = false;
    }
});




const editDishForm = document.querySelector('#editDishForm form');

editDishForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(editDishForm);
    const dishId = document.getElementById('editDishId').value;

    // ✅ gửi is_available rõ ràng 1/0
    const isAvailable = document.getElementById("editActive").checked;
    formData.set("is_available", isAvailable ? "1" : "0");

    // xử lý upload cloudinary nếu có ảnh mới
    let imageFile = document.getElementById('editImage').files[0];
    if (imageFile) {
        const cloudData = new FormData();
        cloudData.append('file', imageFile);
        cloudData.append('upload_preset', 'ml_default');

        try {
            const cloudRes = await fetch('https://api.cloudinary.com/v1_1/dlwjqml4p/image/upload', {
                method: 'POST',
                body: cloudData
            });
            const cloudJson = await cloudRes.json();
            formData.append('image_url', cloudJson.secure_url);
        } catch (err) {
            console.error("Lỗi upload Cloudinary:", err);
            alert("Không thể upload ảnh");
            return;
        }
    }

    try {
        const res = await fetch(`/owner/menu/${dishId}`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (data.success) {
            alert("Cập nhật thành công");

            const dish = data.dish;
            const row = document.querySelector(`.dish-row[data-id="${dish.dish_id}"]`);
            if (row) {
                row.dataset.name = dish.name;
                row.dataset.note = dish.note;
                row.dataset.price = dish.price;
                row.dataset.category = dish.category;
                row.dataset.image = dish.image;
                row.dataset.active = dish.is_available ? '1' : '0';

                row.innerHTML = `
                    <td class="text-center">${dish.name}</td>
                    <td class="text-center text-truncate" style="max-width:150px;">${dish.note || "Chưa có mô tả"}</td>
                    <td class="text-center">${dish.price}đ</td>
                    <td class="text-center">${dish.category || '-'}</td>
                    <td class="text-center">
                        <button type="submit" class="btn btn-danger btn-sm middle">Xóa</button>
                    </td>
                `;
            }

            const collapse = bootstrap.Collapse.getInstance(document.getElementById('editDishForm'));
            collapse.hide();

        } else {
            alert(data.error || "Cập nhật thất bại");
        }
    } catch (err) {
        console.error(err);
        alert("Lỗi server");
    }
});


// xoa

document.querySelectorAll('.dish-row .btn-danger').forEach(button => {
    button.addEventListener('click', async function (e) {
        e.stopPropagation(); // ⛔ Không cho bubble lên <tr>

        if (!confirm("Bạn có chắc chắn muốn xoá món ăn này?")) return;

        const row = this.closest('.dish-row');
        const dishId = row.dataset.id;

        try {
            const res = await fetch(`/owner/menu/${dishId}`, {
                method: "DELETE"
            });

            const data = await res.json();
            if (data.success) {
                alert(data.message || "Xoá thành công");
                row.remove();

                // Ẩn form chỉnh sửa nếu đang hiển thị
                const editFormEl = document.getElementById("editDishForm");
                const collapse = bootstrap.Collapse.getInstance(editFormEl);
                if (collapse) collapse.hide();

                // Nếu không còn món ăn nào thì hiển thị message
                if (document.querySelectorAll(".dish-row").length === 0) {
                    document.getElementById("noDishesMsg").style.display = "block";
                }
            } else {
                alert(data.error || "Xoá thất bại");
            }
        } catch (err) {
            console.error("Lỗi xoá món ăn:", err);
            alert("Lỗi server khi xoá món ăn");
        }
    });
});
