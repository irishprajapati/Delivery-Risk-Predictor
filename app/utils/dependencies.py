from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.model import User, Customer
from app.database import SessionLocal
from app.utils.security import decode_access_token

# OAuth2 scheme (extracts token from Authorization header)
security = HTTPBearer()


#  DB Dependency (clean session handling)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        # Extract token from Bearer
        token = credentials.credentials

        payload = decode_access_token(token)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user_id = payload.get("sub")
        role = payload.get("role")

        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload invalid"
            )

        if role == "admin":
            user = db.query(User).filter(User.id == int(user_id)).first()

            if not user:
                raise HTTPException(status_code=401, detail="Admin not found")

            if not user.is_active:
                raise HTTPException(status_code=403, detail="Admin disabled")

        elif role == "customer":
            user = db.query(Customer).filter(Customer.id == int(user_id)).first()

            if not user:
                raise HTTPException(status_code=401, detail="Customer not found")

            if not user.is_verified:
                raise HTTPException(status_code=403, detail="Customer not verified")

        elif role == "rider":
            from app.model import Rider
            rider = db.query(Rider).filter(Rider.id == int(user_id)).first()

            if not rider:
                raise HTTPException(status_code=401, detail="Rider not found")

            if not rider.is_active:
                raise HTTPException(status_code=403, detail="Rider account is inactive")

            user = rider

        else:
            raise HTTPException(status_code=401, detail="Invalid role")

        return {
            "id": user.id,
            "role": role,
            "user": user
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
#Admin only dependency
def get_current_admin(current=Depends(get_current_user)):
    if current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current["user"]
#user only dependency
def get_current_customer(current=Depends(get_current_user)):
    if current["role"] != "customer":
        raise HTTPException(status_code=403, detail="Customers only")
    return current["user"]

#rider only dependency
def get_current_rider(current=Depends(get_current_user)):
    if current["role"] != "rider":
        raise HTTPException(status_code=403, detail="Riders only")
    return current["user"]