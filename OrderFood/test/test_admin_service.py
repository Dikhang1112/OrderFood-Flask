import unittest
import pytest
from unittest.mock import patch, MagicMock
from flask import session, url_for
from OrderFood.admin_service import admin_bp, is_admin, approve_restaurant, reject_restaurant
from OrderFood.models import StatusRes

class MyTestCase(unittest.TestCase):
    # ----------------- Fixtures -----------------
    @pytest.fixture
    def client(app):
        app.register_blueprint(admin_bp)
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    # ----------------- Tests -----------------

    def test_is_admin():
        from enum import Enum

        class RoleEnum(Enum):
            ADMIN = "admin"
            USER = "user"

        assert is_admin("admin") is True
        assert is_admin("ADMIN") is True
        assert is_admin(RoleEnum.ADMIN) is True
        assert is_admin("user") is False

    def test_approve_restaurant_success(client):
        mock_res = MagicMock()
        mock_res.status = StatusRes.PENDING
        mock_res.status.value = "PENDING"
        mock_res.owner.user.email = "owner@example.com"

        with patch("OrderFood.admin_service.get_restaurant_by_id", return_value=mock_res):
            with patch("OrderFood.admin_service.db.session.commit") as mock_commit:
                with patch("OrderFood.admin_service.send_restaurant_status_email") as mock_email:
                    with client.session_transaction() as sess:
                        sess["role"] = "admin"
                        sess["user_id"] = 1

                    response = client.patch("/admin/restaurants/1/approve")
                    data = response.get_json()

                    assert response.status_code == 200
                    assert data["ok"] is True
                    assert data["status"] == mock_res.status.value
                    mock_commit.assert_called_once()
                    mock_email.assert_called_once_with("owner@example.com", mock_res.name, "APPROVED")

    def test_reject_restaurant_forbidden(client):
        response = client.patch("/admin/restaurants/1/reject")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "forbidden"

    def test_reject_restaurant_success(client):
        mock_res = MagicMock()
        mock_res.status = StatusRes.PENDING
        mock_res.owner.user.email = "owner@example.com"

        with patch("OrderFood.admin_service.get_restaurant_by_id", return_value=mock_res):
            with patch("OrderFood.admin_service.db.session.commit") as mock_commit:
                with patch("OrderFood.admin_service.send_restaurant_status_email") as mock_email:
                    with client.session_transaction() as sess:
                        sess["role"] = "admin"
                        sess["user_id"] = 1

                    response = client.patch("/admin/restaurants/1/reject", json={"reason": "Test reason"})
                    data = response.get_json()

                    assert response.status_code == 200
                    assert data["ok"] is True
                    assert data["id"] == 1
                    assert data["status"] == mock_res.status.value
                    mock_commit.assert_called_once()
                    mock_email.assert_called_once()

    def test_mark_completed(client):
        mock_order = MagicMock()
        mock_order.status = MagicMock()
        mock_order.status = "ACCEPTED"

        with patch("OrderFood.admin_service.Order.query.get_or_404", return_value=mock_order):
            with patch("OrderFood.admin_service.db.session.commit") as mock_commit:
                with patch("OrderFood.admin_service.push_customer_noti_on_completed") as mock_noti:
                    with client.session_transaction() as sess:
                        sess["role"] = "admin"
                        sess["user_id"] = 1

                    response = client.post("/admin/delivery/mark_completed/1")
                    assert response.status_code == 302  # redirect
                    mock_commit.assert_called_once()
                    mock_noti.assert_called_once_with(mock_order)


# add assertion here


if __name__ == '__main__':
    unittest.main()
