#####################################################
#                                                   #
#                의존성 주입 함수 정의                 #
#                                                   #
#####################################################

from fastapi import Request
from openai import AsyncOpenAI
from langsmith import Client as LangSmithClient

##### 클라이언트 의존성 주입 함수 정의 #####
# app.py lifespan 에서 초기화된 클라이언트를 반환
# Depends를 위한 헬퍼 함수

# openai
def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.client_container.openai_client

# langsmith
def get_langsmith_client(request: Request) -> LangSmithClient:
    return request.app.state.client_container.langsmith_client