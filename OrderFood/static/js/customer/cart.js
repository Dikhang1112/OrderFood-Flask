// =========================================
// Cart.js - xử lý popup thêm món vào giỏ
// =========================================

// Mở modal món ăn
function openDishModal(dish_id, name, image, price, note, restaurant_id) {
    // Điền dữ liệu vào modal
    document.getElementById("dishModalTitle").textContent = name;
    document.getElementById("dishModalImage").src = image || 'https://via.placeholder.com/120x120?text=No+Image';
    document.getElementById("dishModalPrice").textContent = price;
    document.getElementById("dishModalNote").textContent = note || '';
    document.getElementById("dishModalQty").value = 1;
    document.getElementById("dishModalUserNote").value = '';

    // Thêm sự kiện cho nút "Thêm vào giỏ"
    const addBtn = document.getElementById("dishModalAddBtn");
    addBtn.onclick = function() {
        const qty = parseInt(document.getElementById("dishModalQty").value) || 1;
        const userNote = document.getElementById("dishModalUserNote").value || '';
        addToCart(dish_id, restaurant_id, qty, userNote);

        // Đóng modal
        const modalEl = document.getElementById("dishModal");
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();
    }

    // Hiển thị modal
    const modalEl = document.getElementById("dishModal");
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

// Thêm món vào giỏ hàng qua API
function addToCart(dish_id, restaurant_id, quantity = 1, note = "") {
    fetch('/api/cart', {
        method: "POST",
        body: JSON.stringify({
            "dish_id": dish_id,
            "restaurant_id": restaurant_id,
            "quantity": quantity,
            "note": note
        }),
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.total_items !== undefined) {
            // Cập nhật mini-cart ngay lập tức
            updateCartCount(data.total_items);
        } else {
            alert(data.error || "Có lỗi xảy ra");
        }
    })
    .catch(err => console.error("Error:", err));
}

// Cập nhật mini-cart
function updateCartCount(count) {
    const badge = document.getElementById("cart-count");
    const mini_cart = document.getElementById("mini_cart");

    if (badge) {
        badge.textContent = count;
        if (count <= 0) {
            badge.classList.add("d-none");
        } else {
            badge.classList.remove("d-none");
        }
    }

    if (mini_cart) {
        if (count <= 0) {
            mini_cart.classList.add("disabled");
        } else {
            mini_cart.classList.remove("disabled");
        }
    }
}


// Gắn sự kiện cho các nút "+" trên danh sách món
document.querySelectorAll('.add-dish-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        openDishModal(
            parseInt(this.dataset.id),
            this.dataset.name,
            this.dataset.image || 'https://via.placeholder.com/120x120?text=No+Image',
            parseFloat(this.dataset.price),
            this.dataset.note,
            parseInt(this.dataset.res)
        );
    });
});

// Cho phép gọi từ HTML
window.addToCart = addToCart;
window.openDishModal = openDishModal;
window.updateCartCount = updateCartCount;

document.addEventListener('DOMContentLoaded', () => {
    const table = document.querySelector('.ct-table');
    if (!table) return;

    // Inline edit quantity / note
    table.addEventListener('blur', (e) => {
        if (e.target.classList.contains('cart-qty-input') || e.target.classList.contains('cart-note-input')) {
            const row = e.target.closest('tr');
            const itemId = e.target.dataset.id;
            const quantity = parseInt(row.querySelector('.cart-qty-input').value) || 1;
            const note = row.querySelector('.cart-note-input').value || '';
            updateCartItem(itemId, quantity, note, row);
        }
    }, true);

    // Click xóa
    table.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-cart-item')) {
            const row = e.target.closest('tr');
            deleteCartItem(e.target.dataset.id, row);
        }
    });
});

function updateCartItem(itemId, quantity, note, row) {
    fetch(`/api/cart/${itemId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity, note })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            row.querySelector('.cart-subtotal').textContent = data.subtotal.toLocaleString('vi-VN') + ' đ';
            document.getElementById('cart-total').textContent = data.total.toLocaleString('vi-VN') + ' đ';
        } else alert(data.error || "Có lỗi khi cập nhật sản phẩm");
    }).catch(err => console.error(err));
}

function deleteCartItem(itemId, row) {
    if (!confirm("Bạn có chắc muốn xóa sản phẩm này khỏi giỏ hàng?")) return;

    fetch(`/api/cart/${itemId}`, { method: "DELETE" })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            row.remove();
            updateCartCount(data.total_items);

            // Update tổng giá
            let total = 0;
            document.querySelectorAll('.cart-subtotal').forEach(cell => {
                total += parseFloat(cell.textContent.replace(/[^0-9.-]+/g,""));
            });
            document.getElementById('cart-total').textContent = total.toLocaleString('vi-VN') + ' đ';
            console.log(data.redirect_url);

            // Redirect nếu giỏ hàng trống
            if (data.redirect_url) {
            console.log("ss");
                window.location.href = data.redirect_url;
            }
        } else {
            alert(data.error || "Có lỗi khi xóa sản phẩm");
        }
    })
    .catch(err => console.error(err));
}
