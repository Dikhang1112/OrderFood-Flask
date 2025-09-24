from sqlalchemy import desc, asc
from typing import List, Optional
from OrderFood.models import db, User, Role


def get_all_user(limit: Optional[int] = None,
                 offset: int = 0,
                 newest_first: bool = True) -> List[User]:
    """
    Lấy toàn bộ người dùng (không bao gồm admin) qua session + query.
    - limit=None: trả tất cả
    - offset: phân trang
    - newest_first: sắp xếp theo id giảm dần (mới trước)
    """
    q = db.session.query(User).filter(User.role != Role.ADMIN)

    # Sắp xếp theo id
    q = q.order_by(desc(User.user_id) if newest_first else asc(User.user_id))

    if offset:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()
