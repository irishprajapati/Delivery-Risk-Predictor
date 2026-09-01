from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.model import User, Customer, OTPCode
from app.schemas import RegisterRequest,VerifyOTPRequest
from app.utils.security import verify_password, create_access_token, get_password_hash, generate_otp
from app.utils.rate_limiter import is_blocked, record_failure, clear_failures
router = APIRouter()


#DB Dependency (correct pattern)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    customer = (
        db.query(Customer)
        .filter(Customer.phone == data.phone)
        .first()
    )

    if customer and customer.is_verified:
        raise HTTPException(
            status_code=400,
            detail="An account with this phone number already exists. Please log in."
        )

    hashed_pw = get_password_hash(data.password)

    if customer and not customer.is_verified:
        customer.password_hash = hashed_pw
        db.commit()
    else:
        customer = Customer(
            phone=data.phone,
            password_hash=hashed_pw,
            is_verified=False
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    otp_code = generate_otp()

    old_otp = (
        db.query(OTPCode)
        .filter(OTPCode.phone == data.phone)
        .first()
    )

    if old_otp:
        db.delete(old_otp)
        db.commit()

    otp_entry = OTPCode(
        phone=data.phone,
        otp=otp_code,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )

    db.add(otp_entry)
    db.commit()

    print(f"[DEV OTP] {data.phone} → {otp_code}")

    return {
        "message": "OTP sent successfully"
    }

#OTP Request
@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTPCode).filter(OTPCode.phone == data.phone).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP not found")
    if otp_record.created_at is None:
        db.delete(otp_record)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP invalid. Please request a new one.")
    expiry_time = otp_record.created_at + timedelta(minutes=5)
    if datetime.utcnow() > expiry_time:
        db.delete(otp_record)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired")
    if otp_record.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    customer = db.query(Customer).filter(Customer.phone == data.phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_verified = True
    db.delete(otp_record)
    db.commit()
    return {
        "message": "OTP verified successfully",
        "phone": customer.phone,
        "is_verified": customer.is_verified
    }

@router.post("/admin/login")
def admin_login(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not an admin")

    token = create_access_token({
        "sub": str(user.id),
        "role": "admin"
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
@router.post("/customer/login")
def customer_login(
    phone: str,
    password: str,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.phone == phone).first()

    if not customer:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not customer.is_verified:
        raise HTTPException(status_code=403, detail="Phone not verified")

    token = create_access_token({
        "sub": str(customer.id),
        "role": "customer"
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }



