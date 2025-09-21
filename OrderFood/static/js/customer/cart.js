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
        badge.classList.remove("d-none"); // đảm bảo badge luôn hiển thị
    }

    if (mini_cart) {
        mini_cart.classList.remove("d-none"); // đảm bảo mini-cart luôn hiển thị
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
