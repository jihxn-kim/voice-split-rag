#####################################################
#                                                   #
#                의존성 주입 함수 정의                 #
#                                                   #
#####################################################

from fastapi import Request
from openai import AsyncOpenAI
from langsmith import Client as LangSmithClient
from google.cloud.speech_v1p1beta1 import SpeechClient
from google.cloud.speech_v2 import SpeechClient as SpeechV2Client
from google.cloud.storage import Client as StorageClient

##### 클라이언트 의존성 주입 함수 정의 #####
# app.py lifespan 에서 초기화된 클라이언트를 반환
# Depends를 위한 헬퍼 함수

# openai
def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.client_container.openai_client

# langsmith
def get_langsmith_client(request: Request) -> LangSmithClient:
    return request.app.state.client_container.langsmith_client

# google speech
def get_google_speech_client(request: Request) -> SpeechClient:
    return request.app.state.client_container.google_speech_client

def get_google_speech_v2_client(request: Request) -> SpeechV2Client:
    return request.app.state.client_container.google_speech_v2_client

def get_speech_v2_recognizer(request: Request) -> str | None:
    return request.app.state.client_container.speech_v2_recognizer

# gcs
def get_gcs_client(request: Request) -> StorageClient:
    return request.app.state.client_container.gcs_client

def get_gcs_bucket_name(request: Request) -> str | None:
    return request.app.state.client_container.gcs_bucket_name