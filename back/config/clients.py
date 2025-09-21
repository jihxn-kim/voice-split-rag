#####################################################
#                                                   #
#               클라이언트 의존성 정의                 #
#                                                   #
#####################################################

from langsmith import Client as LangSmithClient
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

load_dotenv()

# 모든 클라이언트 인스턴스를 담을 컨테이너 클래스
class ClientContainer:
    def __init__(self):
        self.openai_client = None
        self.langsmith_client = None
        self.google_speech_client = None
        self.gcs_client = None
        self.gcs_bucket_name = None

# 클라이언트들을 초기화하는 함수
def initialize_clients() -> ClientContainer:
    container = ClientContainer()
    container.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    container.langsmith_client = LangSmithClient()
    # Google Application Default Credentials 사용 (환경변수 GOOGLE_APPLICATION_CREDENTIALS 필요)
    container.google_speech_client = speech.SpeechClient()
    container.gcs_client = storage.Client()
    # 기본 버킷 이름을 환경변수에서 읽어 보관 (dotenv 지원)
    container.gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")

    return container
