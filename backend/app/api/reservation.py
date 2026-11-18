from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.reservation import AuditReservationRequest, ReservationCreateRequest
from app.services import reservation_service

router = APIRouter(prefix="/reservation", tags=["预约相关接口"])


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交预约（登录用户）"""
    res = reservation_service.create_reservation(db, current_user, data)
    return Response.success(message="预约已提交，请等待审核", data=res)


@router.get("/list")
def get_reservation_list(
    page: int = 1,
    page_size: int = 10,
    status: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """预约记录列表（学生只看自己，管理员看全部）"""
    res = reservation_service.get_reservation_page_list(
        db, current_user, page, page_size, status
    )
    return Response.success(data=res)


@router.get("/my", include_in_schema=False)
def get_my_reservation_list(
    page: int = 1,
    page_size: int = 10,
    status: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """兼容别名：等价于 /list（学生视角）"""
    res = reservation_service.get_reservation_page_list(
        db, current_user, page, page_size, status
    )
    return Response.success(data=res)


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消预约（本人）"""
    reservation_service.cancel_reservation(db, current_user, reservation_id)
    return Response.success(message="取消成功")


@router.put("/{reservation_id}/audit")
def audit_reservation(
    reservation_id: int,
    data: AuditReservationRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审核预约（仅管理员）"""
    reservation_service.audit_reservation(db, reservation_id, data.status)
    return Response.success(message="审核成功")