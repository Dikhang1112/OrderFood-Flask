function addToCart(dish_id, restaurant_id){
     fetch('/api/cart', {
        method: "post",
        body: JSON.stringify({ "dish_id": dish_id, "restaurant_id": restaurant_id }),
        headers: {
            "Content-Type": "application/json"
        }})
   .then(res => res.json())
   .then(data => {
        if (data.total_items !== undefined) {
            // Cập nhật số lượng trên mini-cart
            updateCartCount(data.total_items);
            const mini_cart = document.getElementById("mini_cart");
            const cart_count = document.getElementById("cart-count");

            if (mini_cart && cart_count) {
                if (data.total_items > 0) {
                    mini_cart.classList.remove("d-none");
                    cart_count.classList.remove("d-none");
                } else {
                    mini_cart.classList.add("d-none");
                    cart_count.classList.add("d-none");
                }
            }
        } else {
            alert(data.error || "Có lỗi xảy ra");
        }
    })
    .catch(err => console.error("Error:", err))
}



function updateCartCount(count) {
    const badge = document.getElementById("cart-count");
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? "inline-block" : "none";
    }
}



window.addToCart = addToCart;