from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.lab import Lab
from app.schemas.lab import LabCreateRequest, LabResponse, LabUpdateRequest


def get_lab_page_list(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    status: int | None = None,
) -> PageResponse:
    """分页 + 关键字（名称/位置）模糊查询实验室，可按状态过滤"""
    query = db.query(Lab)
    if keywords:
        query = query.filter(
            or_(Lab.name.ilike(f"%{keywords}%"), Lab.location.ilike(f"%{keywords}%"))
        )
    if status is not None:
        query = query.filter(Lab.status == status)
    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items],
        total=total,
    )


def get_lab_list(db: Session) -> list[LabResponse]:
    """不分页的实验室列表（学生端下拉、AI 工具调用用）"""
    items = db.query(Lab).order_by(Lab.id.desc()).all()
    return [LabResponse.model_validate(item) for item in items]


def get_lab(db: Session, lab_id: int) -> Lab:
    """按 ID 取实验室，取不到就抛业务异常"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return lab


def get_lab_detail(db: Session, lab_id: int) -> LabResponse:
    """按 ID 取实验室详情（响应模型）"""
    return LabResponse.model_validate(get_lab(db, lab_id))


def create_lab(db: Session, data: LabCreateRequest) -> LabResponse:
    exists = db.query(Lab).filter(Lab.name == data.name).first()
    if exists:
        raise BusinessException(message="实验室名称已存在")

    lab = Lab(**data.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, lab_id: int, data: LabUpdateRequest) -> LabResponse:
    lab = get_lab(db, lab_id)

    payload = data.model_dump(exclude_none=True)
    if "name" in payload:
        exists = (
            db.query(Lab).filter(Lab.name == payload["name"], Lab.id != lab_id).first()
        )
        if exists:
            raise BusinessException(message="实验室名称已存在")

    for field, value in payload.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, lab_id: int) -> None:
    lab = get_lab(db, lab_id)
    db.delete(lab)
    db.commit()