# OrderFood/dao/restaurant_dao.py
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from OrderFood import db
from OrderFood.models import Restaurant


def get_all_restaurants(limit: Optional[int] = None,
                        offset: int = 0,
                        newest_first: bool = True) -> List[Restaurant]:
    """
    Lấy toàn bộ nhà hàng qua session + query.
    - limit=None: trả tất cả
    - offset: phân trang
    - newest_first: sắp xếp theo id giảm dần (mới trước)
    """
    q = db.session.query(Restaurant)
    q = q.order_by(Restaurant.restaurant_id.desc() if newest_first
                   else Restaurant.restaurant_id.desc())
    if offset:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()


def count_restaurants() -> int:
    """Đếm tổng số nhà hàng (phục vụ phân trang)."""
    return db.session.query(func.count(Restaurant.restaurant_id)).scalar() or 0


def search_restaurants(keyword: Optional[str],
                       limit: int = 50,
                       offset: int = 0) -> List[Restaurant]:
    """
    Tìm nhà hàng theo tên (LIKE, không phân biệt hoa thường).
    """
    q = db.session.query(Restaurant)
    if keyword:
        kw = f"%{keyword.strip().lower()}%"
        q = q.filter(func.lower(Restaurant.name).like(kw))
    q = q.order_by(Restaurant.restaurant_id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


def get_restaurant_by_id(restaurant_id: int) -> Optional[Restaurant]:
    """Lấy 1 nhà hàng theo id (có thể kèm eager load sau này)."""
    return (db.session.query(Restaurant)
            # .options(joinedload(Restaurant.owner))  # nếu muốn load luôn owner
            .filter(Restaurant.restaurant_id == restaurant_id)
            .first())


def list_with_pagination(page: int = 1, page_size: int = 20) -> Tuple[List[Restaurant], int]:
    """
    Trả về (items, total) để render phân trang dễ dàng.
    """
    total = count_restaurants()
    offset = max(0, (page - 1) * page_size)
    items = get_all_restaurants(limit=page_size, offset=offset, newest_first=True)
    return items, total
