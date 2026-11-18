from datetime import datetime

import asyncio
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import (
    ReservationCreateRequest,
    ReservationResponse,
)

# 状态：0 待审核，1 已通过，2 已拒绝，3 已取消
STATUS_PENDING = 0
STATUS_APPROVED = 1
STATUS_REJECTED = 2
STATUS_CANCELLED = 3


def _to_response(item: Reservation) -> ReservationResponse:
    """补上预约人、实验室、设备名称和类型，方便前端直接展示"""
    res = ReservationResponse.model_validate(item)
    res.user_name = item.user.name if item.user else None
    res.lab_name = item.lab.name if item.lab else None
    res.equipment_name = item.equipment.name if item.equipment else None
    res.type = "设备" if item.equipment_id else "实验室"
    return res


def create_reservation(
    db: Session, current_user: User, data: ReservationCreateRequest
) -> ReservationResponse:
    """创建预约记录（实验室 + 可选设备）"""
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    if data.date < current_date:
        raise BusinessException(message="预约日期不能小于当前的日期")
    if data.end_time <= data.start_time:
        raise BusinessException(message="预约的结束时间必须晚于开始时间")
    if data.date == current_date and data.start_time < current_time:
        raise BusinessException(message="预约开始时间不能小于当前的时间")

    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")
    if lab.open_time and data.start_time < lab.open_time:
        raise BusinessException(message="预约时间不能早于实验室的开放时间")
    if lab.close_time and data.end_time > lab.close_time:
        raise BusinessException(message="预约时间不能晚于实验室的关闭时间")

    # equipment_id 不为空则表示这次是预约的实验室设备
    if data.equipment_id:
        equipment = (
            db.query(Equipment).filter(Equipment.id == data.equipment_id).first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")
        if equipment.lab_id != data.lab_id:
            raise BusinessException(message="该设备不属于这个实验室")

    # 实验室或设备在目标时段是否已被占用（待审核、已通过都算占用）
    query = db.query(Reservation).filter(
        Reservation.lab_id == data.lab_id,
        Reservation.date == data.date,
        Reservation.status.in_([STATUS_PENDING, STATUS_APPROVED]),
        Reservation.start_time < data.end_time,
        Reservation.end_time > data.start_time,
    )
    if data.equipment_id:
        query = query.filter(Reservation.equipment_id == data.equipment_id)
    else:
        query = query.filter(Reservation.equipment_id.is_(None))
    if query.first():
        raise BusinessException(message="该时段已被预约")

    reservation = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        remark=data.remark,
        status=STATUS_PENDING,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return _to_response(reservation)


def get_reservation_page_list(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    status: int | None = None,
) -> PageResponse:
    """预约记录列表：学生只能看自己的，管理员看全部"""
    query = db.query(Reservation)
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    total = query.count()
    items = (
        query.order_by(Reservation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(list=[_to_response(item) for item in items], total=total)


def cancel_reservation(db: Session, current_user: User, reservation_id: int) -> None:
    """学生取消预约（待审核、已通过都可以取消）"""
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.user_id != current_user.id:
        raise BusinessException(message="无权限", code=403)
    if item.status not in (STATUS_PENDING, STATUS_APPROVED):
        raise BusinessException(message="当前状态无法取消")
    item.status = STATUS_CANCELLED
    db.commit()


def audit_reservation(db: Session, reservation_id: int, status: int) -> None:
    """管理员审核预约：1-通过，2-拒绝"""
    if status not in (STATUS_APPROVED, STATUS_REJECTED):
        raise BusinessException(message="审核状态错误")
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != STATUS_PENDING:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    db.commit()


def expire_pending_reservations() -> None:
    """把「结束时间已过」的待审核预约改成已取消，释放时段"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        now_time = now.strftime("%H:%M")
        items = db.query(Reservation).filter(Reservation.status == STATUS_PENDING).all()
        changed = False
        for item in items:
            if item.date < today or (item.date == today and item.end_time <= now_time):
                item.status = STATUS_CANCELLED
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()


async def run_expire_scan(interval: int = 60) -> None:
    """后台任务：每 60 秒扫一次过期预约"""
    while True:
        try:
            expire_pending_reservations()
        except Exception as e:  # 扫描失败不影响服务
            print(f"过期预约扫描失败: {e}")
        await asyncio.sleep(interval)