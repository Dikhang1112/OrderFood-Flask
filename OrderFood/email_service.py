# OrderFood/mail_service.py
from flask import current_app
from flask_mail import Message

from OrderFood import mail


def send_mail(subject: str, recipients: list[str], body: str = "", html: str = "") -> bool:
    """
    Gửi email đơn giản. Trả về True nếu gửi OK, False nếu lỗi.
    """
    try:
        if not recipients:
            return False
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body if html == "" else None,
            html=html if html else None,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER")
        )
        mail.send(msg)
        return True
    except Exception as ex:
        # Có thể log vào file/logging tùy bạn
        current_app.logger.exception("send_mail failed")
        return False


# Ví dụ các hàm nghiệp vụ cụ thể
def send_restaurant_status_email(to_email: str, restaurant_name: str, status: str, reason: str | None = None):
    subject = f"[OrderFood] Cập nhật trạng thái nhà hàng: {restaurant_name}"
    reason_html = f"<p><b>Lý do:</b> {reason}</p>" if reason else ""
    html = f"""
    <div style="font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif">
      <h2>Thông báo trạng thái nhà hàng</h2>
      <p>Nhà hàng <b>{restaurant_name}</b> đã được cập nhật trạng thái: <b>{status}</b>.</p>
      <p>{reason_html}</p>
      <p>Trân trọng,<br>Đội ngũ OrderFood</p>
    </div>
    """
    return send_mail(subject, [to_email], html=html)
