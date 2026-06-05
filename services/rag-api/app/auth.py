import os
from fastapi import Header, HTTPException, status


def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> None:
    expected = (os.environ.get("ADMIN_API_KEY") or "").strip()
    got = (x_admin_key or "").strip()
    if not expected or got != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key",
        )


def require_student(x_student_key: str | None = Header(None, alias="X-Student-Key")) -> None:
    expected = (os.environ.get("STUDENT_API_KEY") or "").strip()
    got = (x_student_key or "").strip()
    if not expected or got != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Student-Key",
        )
