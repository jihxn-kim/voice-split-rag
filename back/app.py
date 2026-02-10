#####################################################
#                                                   #
#                앱 상태 정의 및 관리                  #
#                                                   #
#####################################################

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from logs.logging_util import LoggerSingleton
from contextlib import asynccontextmanager
from config.clients import initialize_clients
from voice.router import router as voice_router
from auth.router import router as auth_router
from config.exception import register_exception_handlers
from database import Base, engine
from sqlalchemy import text
from dotenv import load_dotenv
import os
import logging

load_dotenv()

# 로거 설정
logger = LoggerSingleton.get_logger(logger_name="app", level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 데이터베이스 테이블 생성
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE voice_records "
                    "ADD COLUMN IF NOT EXISTS segments_merged_data JSON"
                )
            )
        logger.info("Database columns ensured successfully")
    except Exception as e:
        logger.warning(f"Failed to ensure database columns: {str(e)}")
    logger.info("Database tables created successfully")
    
    logger.info(
        r"""                                                                          
 ##  ##    ####    ######    ####     #####             #####   ######    ####    #####    ######  
 ##  ##   ##  ##     ##     ##  ##   ##                ##         ##     ##  ##   ##  ##     ##    
 ##  ##   ##  ##     ##     ##       ####               ####      ##     ##  ##   ##  ##     ##    
 ##  ##   ##  ##     ##     ##       ##                    ##     ##     ######   #####      ##    
  ####    ##  ##     ##     ##  ##   ##                    ##     ##     ##  ##   ## ##      ##    
   ##      ####    ######    ####     #####            #####      ##     ##  ##   ##  ##     ##    
"""
    )

    # Todo: 데이터베이스 초기화 로직 추가 필요
    # await to_thread(create_database_if_not_exists)
    # await init_db()
    # logger.info(
    #     f"\n{'=' * 80}\n"
    #     f"| {' ' * 29} 🛢️ DATABASE INITIATED 🛢️ {' ' * 29} |\n"
    #     f"{'=' * 80}\n"
    # )

    # 앱 상테에 클라이언트 컨테이너를 저장할 객체 초기화
    global client_container
    client_container = initialize_clients()
    app.state.client_container = client_container

    yield
    # 종료시 클린업 작업은 여기서
    # Todo: 데이터베이스 연결 해제 로직 추가 필요
    # Todo: 기타 리소스 정리 로직 추가 필요
    logger.info(
        r"""                                                                        
 ##  ##    ####    ######    ####     #####             #####   ##  ##   #####   
 ##  ##   ##  ##     ##     ##  ##   ##                ##       ### ##   ##  ##  
 ##  ##   ##  ##     ##     ##       ####              ####     ######   ##  ##  
 ##  ##   ##  ##     ##     ##       ##                ##       ## ###   ##  ##  
  ####    ##  ##     ##     ##  ##   ##                ##       ##  ##   ##  ##  
   ##      ####    ######    ####     #####             #####   ##  ##   #####   
                           🛑 ENGINE SHUTDOWN 🛑
    """
    )

# FastAPI 앱 인스턴스 생성
app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)

vsr_url = os.getenv("VSR_URL", "http://localhost:3000")

# CORS 설정 - 프론트엔드 URL 허용
allowed_origins = [
    "http://localhost:3000",  # Next.js 로컬
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite 로컬 (개발용)
    "http://127.0.0.1:5173",
]

# 환경 변수로 설정된 프론트엔드 URL 추가
if vsr_url:
    allowed_origins.extend([
        vsr_url,
        f"https://{vsr_url}" if not vsr_url.startswith("http") else vsr_url,
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus FastAPI 미들웨어 설정
Instrumentator().instrument(app).expose(app)

# 라우터 등록
from voice.history_router import router as history_router
from client.router import router as client_router
from appointment.router import router as appointment_router

routers = [auth_router, voice_router, history_router, client_router, appointment_router]

for router in routers:
    app.include_router(router)

# 라우터에 client_container 전달은 app.state를 통해 처리합니다.
