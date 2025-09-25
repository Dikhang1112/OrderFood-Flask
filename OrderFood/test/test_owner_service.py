import unittest
import pytest
from unittest.mock import patch, MagicMock
from flask import session
from OrderFood.owner import owner_bp, is_owner
from OrderFood.models import StatusOrder, Role, StatusRefund
from datetime import datetime

class MyTestCase(unittest.TestCase):
    # ---------------- Fixture ----------------
    @pytest.fixture
    def client(app):
        app.register_blueprint(owner_bp)
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    # ---------------- Helpers ----------------
    def test_is_owner():
        assert is_owner("restaurant_owner") is True
        assert is_owner("RESTAURANT_OWNER") is True
        assert is_owner("customer") is False

    # ---------------- Routes ----------------
    def test_owner_home_redirect_login(client):
        response = client.get("/owner/")
        assert response.status_code == 302  # redirect to login

    def test_owner_home_success(client):
        mock_user = MagicMock()
        mock_restaurant = MagicMock()
        mock_user.restaurant_owner.restaurant = mock_restaurant
        with patch("OrderFood.owner.User.query.get", return_value=mock_user):
            with client.session_transaction() as sess:
                sess["role"] = "restaurant_owner"
                sess["user_id"] = 1
            response = client.get("/owner/")
            assert response.status_code == 200
            assert b"owner_home.html" in response.data or b"html" in response.data

    def test_get_menu_with_keyword(client):
        mock_user = MagicMock()
        mock_user.restaurant_owner.restaurant = MagicMock()
        with patch("OrderFood.owner.User.query.get", return_value=mock_user):
            with patch("OrderFood.owner.get_dishes_by_name", return_value=["dish1"]):
                with patch("OrderFood.owner.get_categories_by_owner_id", return_value=[]):
                    with client.session_transaction() as sess:
                        sess["user_id"] = 1
                    response = client.get("/owner/menu?keyword=dish")
                    assert response.status_code == 200
                    assert b"menu.html" in response.data

    def test_add_dish_success(client):
        mock_user = MagicMock()
        mock_user.restaurant_owner.restaurant.restaurant_id = 1
        with patch("OrderFood.owner.User.query.get", return_value=mock_user):
            with patch("OrderFood.owner.db.session.add") as mock_add:
                with patch("OrderFood.owner.db.session.commit") as mock_commit:
                    with client.session_transaction() as sess:
                        sess["user_id"] = 1
                    response = client.post("/owner/add_dish", data={
                        "name": "Pizza",
                        "price": "100",
                        "note": "Delicious",
                        "category": "",
                        "image_url": ""
                    })
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["success"] is True
                    mock_add.assert_called()
                    mock_commit.assert_called()

    def test_edit_dish_success(client):
        mock_dish = MagicMock()
        mock_dish.dish_id = 1
        mock_dish.category = MagicMock(name="Main")
        with patch("OrderFood.owner.Dish.query.get", return_value=mock_dish):
            with patch("OrderFood.owner.db.session.commit") as mock_commit:
                with client.session_transaction() as sess:
                    sess["user_id"] = 1
                response = client.post("/owner/menu/1", data={
                    "name": "Pizza Updated",
                    "note": "Note",
                    "price": "120",
                    "category": "Main",
                    "is_available": "1",
                    "image_url": ""
                })
                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                assert data["dish"]["name"] == "Pizza Updated"
                mock_commit.assert_called()

    def test_delete_dish_success(client):
        mock_dish = MagicMock()
        mock_dish.name = "Burger"
        with patch("OrderFood.owner.Dish.query.get", return_value=mock_dish):
            with patch("OrderFood.owner.db.session.delete") as mock_delete:
                with patch("OrderFood.owner.db.session.commit") as mock_commit:
                    with client.session_transaction() as sess:
                        sess["user_id"] = 1
                    response = client.delete("/owner/menu/1")
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["success"] is True
                    mock_delete.assert_called()
                    mock_commit.assert_called()

    def test_approve_order_success(client):
        mock_order = MagicMock()
        mock_order.order_id = 1
        mock_order.status = StatusOrder.PAID
        mock_order.customer.user.name = "John"
        mock_order.total_price = 200
        mock_order.cart.items = []
        with patch("OrderFood.owner.Order.query.get_or_404", return_value=mock_order):
            with patch("OrderFood.owner.db.session.commit") as mock_commit:
                with client.session_transaction() as sess:
                    sess["user_id"] = 1
                response = client.post("/owner/orders/1/approve")
                assert response.status_code == 200
                data = response.get_json()
                assert data["status"] == StatusOrder.ACCEPTED.value
                mock_commit.assert_called()

    def test_cancel_order_success(client):
        mock_order = MagicMock()
        mock_order.order_id = 1
        mock_order.status = StatusOrder.PAID
        mock_order.customer.user.name = "John"
        mock_order.payment = MagicMock(payment_id=10)
        with patch("OrderFood.owner.Order.query.get_or_404", return_value=mock_order):
            with patch("OrderFood.owner.db.session.add") as mock_add:
                with patch("OrderFood.owner.db.session.commit") as mock_commit:
                    with client.session_transaction() as sess:
                        sess["user_id"] = 1
                    response = client.post("/owner/orders/1/cancel", json={"reason": "Out of stock"})
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["status"] == StatusOrder.CANCELED.value
                    mock_add.assert_called()
                    mock_commit.assert_called()

    def test_manage_restaurant_success(client):
        mock_user = MagicMock()
        mock_user.restaurant_owner.restaurant = MagicMock()
        mock_user.restaurant_owner = MagicMock()
        with patch("OrderFood.owner.User.query.get", return_value=mock_user):
            with client.session_transaction() as sess:
                sess["role"] = "restaurant_owner"
                sess["user_id"] = 1
            response = client.get("/owner/restaurant")
            assert response.status_code == 200
            assert b"manage_res.html" in response.data

    def test_update_restaurant_success(client):
        mock_user = MagicMock()
        mock_user.restaurant_owner.restaurant = MagicMock()
        mock_user.restaurant_owner = MagicMock()
        with patch("OrderFood.owner.User.query.get", return_value=mock_user):
            with patch("OrderFood.owner.db.session.commit") as mock_commit:
                with client.session_transaction() as sess:
                    sess["role"] = "restaurant_owner"
                    sess["user_id"] = 1
                response = client.post("/owner/restaurant/update", json={
                    "name": "New Name",
                    "address": "New Address"
                })
                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                mock_commit.assert_called()


if __name__ == '__main__':
    unittest.main()
