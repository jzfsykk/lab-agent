"""创建或重置管理员账号。

用法（在 backend 目录下执行）：

    .venv\\Scripts\\python.exe -m scripts.create_admin
    .venv\\Scripts\\python.exe -m scripts.create_admin --username admin --password 自定义密码

已存在同名账号时只重置密码与角色，不会重复插入。
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import User
from app.utils.password import hash_password

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
DEFAULT_NAME = "系统管理员"


def main() -> None:
    parser = argparse.ArgumentParser(description="创建或重置管理员账号")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="账号")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="密码")
    parser.add_argument("--name", default=DEFAULT_NAME, help="显示名称")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username))
        if user is None:
            db.add(
                User(
                    username=args.username,
                    password=hash_password(args.password),
                    name=args.name,
                    role="admin",
                    status=1,
                )
            )
            action = "已创建"
        else:
            user.password = hash_password(args.password)
            user.role = "admin"
            user.status = 1
            action = "已重置"

        db.commit()

    print(f"{action}管理员账号：{args.username} / {args.password}")


if __name__ == "__main__":
    main()
