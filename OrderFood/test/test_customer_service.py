import unittest
import pytest
from unittest.mock import patch, MagicMock
from flask import session, url_for
from OrderFood.customer import customer_bp, is_customer, is_restaurant_open
from datetime import time, datetime


class MyTestCase(unittest.TestCase):
    # ---------------- Fixture ----------------
    @pytest.fixture
    def client(app):
        app.register_blueprint(customer_bp)
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    # ---------------- Helpers ----------------
    def test_is_customer():
        assert is_customer("customer") is True
        assert is_customer("CUSTOMER") is True
        assert is_customer("admin") is False

    def test_is_restaurant_open(monkeypatch):
        class Rest:
            is_open = True
            open_hour = "09:00"
            close_hour = "21:00"

        rest = Rest()
        # patch datetime.now()
        now = datetime(2025, 1, 1, 10, 0, 0)
        monkeypatch.setattr("OrderFood.customer.datetime", MagicMock(now=MagicMock(return_value=now)))
        assert is_restaurant_open(rest) is True

        # test closed
        rest.is_open = False
        assert is_restaurant_open(rest) is False

    # ---------------- Routes ----------------
    def test_restaurant_detail(client):
        mock_res = MagicMock()
        mock_res.rating_point = 4.5
        with patch("OrderFood.customer.dao_cus.get_restaurant_by_id", return_value=mock_res):
            with patch("OrderFood.customer.dao_cus.get_restaurant_menu_and_categories", return_value=([], [])):
                with patch("OrderFood.customer.dao_cus.get_star_display", return_value=4):
                    response = client.get("/restaurant/1")
                    assert response.status_code == 200
                    assert b"restaurant_detail.html" in response.data or b"html" in response.data

    def test_cart_not_logged_in(client):
        response = client.get("/cart/1")
        assert response.status_code == 403
        data = response.get_json()
        assert "Bạn chưa đăng nhập" in data["error"]

    def test_customer_home(client):
        mock_restaurants = [MagicMock(rating_point=4.0)]
        with patch("OrderFood.customer.dao_cus.list_top_restaurants", return_value=mock_restaurants):
            with patch("OrderFood.customer.dao_cus.get_star_display", return_value=4):
                with client.session_transaction() as sess:
                    sess["role"] = "customer"
                response = client.get("/customer")
                assert response.status_code == 200
                assert b"customer_home.html" in response.data or b"html" in response.data

    def test_notifications_json_not_logged_in(client):
        response = client.get("/notifications/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["items"] == []
        assert data["unread_count"] == 0

    def test_order_rate_success(client):
        mock_order = MagicMock()
        with patch("OrderFood.customer.dao_cus.get_order_for_customer_or_admin", return_value=mock_order):
            with patch("OrderFood.customer.dao_cus.can_rate_order", return_value=True):
                with patch("OrderFood.customer.dao_cus.has_rated", return_value=False):
                    with patch("OrderFood.customer.dao_cus.add_order_rating") as mock_add_rating:
                        with patch("OrderFood.customer.dao_cus.update_restaurant_rating") as mock_update_rating:
                            with client.session_transaction() as sess:
                                sess["role"] = "customer"
                                sess["user_id"] = 1
                            response = client.post("/order/1/rate", data={"rating": 5, "comment": "Good"})
                            assert response.status_code == 302  # redirect
                            mock_add_rating.assert_called_once()
                            mock_update_rating.assert_called_once()

    def test_order_track(client):
        mock_order = MagicMock()
        mock_order.status = "COMPLETED"
        with patch("OrderFood.customer.dao_cus.get_order_for_customer_or_admin", return_value=mock_order):
            with patch("OrderFood.customer.dao_cus.compute_track_state", return_value=(1, "Done", True)):
                with client.session_transaction() as sess:
                    sess["role"] = "customer"
                    sess["user_id"] = 1
                response = client.get("/order/1/track")
                assert response.status_code == 200
                assert b"order_track.html" in response.data or b"html" in response.data


if __name__ == '__main__':
    unittest.main()
