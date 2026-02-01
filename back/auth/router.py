"""
인증 관련 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.user import UserCreate, UserLogin, UserResponse, Token
from auth.security import verify_password, get_password_hash, create_access_token
from auth.dependencies import get_current_active_user
from logs.logging_util import LoggerSingleton
import logging

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="auth", level=logging.INFO)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    회원가입
    
    Args:
        user_data: 사용자 등록 정보
        db: 데이터베이스 세션
    
    Returns:
        UserResponse: 생성된 사용자 정보
    """
    logger.info(f"Registration attempt: email={user_data.email}, username={user_data.username}")
    
    # 이메일 중복 체크
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Registration failed: Email already exists - {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 사용자명 중복 체크
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        logger.warning(f"Registration failed: Username already exists - {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # 비밀번호 해싱
    hashed_password = get_password_hash(user_data.password)
    
    # 사용자 생성
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User registered successfully: id={new_user.id}, username={new_user.username}")
    
    return new_user


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    로그인
    
    Args:
        user_credentials: 로그인 자격증명
        db: 데이터베이스 세션
    
    Returns:
        Token: JWT 액세스 토큰
    """
    logger.info(f"Login attempt: username={user_credentials.username}")
    
    # 사용자 조회
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        logger.warning(f"Login failed: Invalid credentials - username={user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Login failed: Inactive user - username={user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # JWT 토큰 생성 (sub는 문자열이어야 함)
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"Login successful: user_id={user.id}, username={user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    현재 로그인한 사용자 정보 조회
    
    Args:
        current_user: 현재 사용자 (JWT 토큰에서 추출)
    
    Returns:
        UserResponse: 사용자 정보
    """
    logger.info(f"User info requested: user_id={current_user.id}")
    return current_user
