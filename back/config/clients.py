#####################################################
#                                                   #
#               클라이언트 의존성 정의                 #
#                                                   #
#####################################################

from langsmith import Client as LangSmithClient
from openai import AsyncOpenAI
import assemblyai as aai
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# 모든 클라이언트 인스턴스를 담을 컨테이너 클래스
class ClientContainer:
    def __init__(self):
        self.openai_client = None
        self.langsmith_client = None
        self.assemblyai_api_key = None
        self.speechmatics_api_key = None
        self.speechmatics_api_url = None
        self.deepgram_api_key = None
        self.vito_client_id = None
        self.vito_client_secret = None
        self.mistral_api_key = None
        self.s3_client = None

# 클라이언트들을 초기화하는 함수
def initialize_clients() -> ClientContainer:
    container = ClientContainer()
    
    # OpenAI 클라이언트
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        container.openai_client = AsyncOpenAI(api_key=openai_key)
    
    # LangSmith 클라이언트
    container.langsmith_client = LangSmithClient()
    
    # AssemblyAI API 키 설정
    assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
    if assemblyai_key:
        aai.settings.api_key = assemblyai_key
        container.assemblyai_api_key = assemblyai_key

    # Speechmatics API 키 설정
    speechmatics_key = os.getenv("SPEECHMATICS_API_KEY")
    if speechmatics_key:
        container.speechmatics_api_key = speechmatics_key
        container.speechmatics_api_url = os.getenv(
            "SPEECHMATICS_API_URL",
            "https://asr.api.speechmatics.com/v2",
        )

    # Deepgram API 키 설정
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    if deepgram_key:
        container.deepgram_api_key = deepgram_key

    # VITO (RTZR) API 설정
    vito_client_id = os.getenv("VITO_CLIENT_ID")
    vito_client_secret = os.getenv("VITO_CLIENT_SECRET")
    if vito_client_id and vito_client_secret:
        container.vito_client_id = vito_client_id
        container.vito_client_secret = vito_client_secret
    
    # Mistral API 키 설정
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        container.mistral_api_key = mistral_key

    # AWS S3 클라이언트
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    if aws_access_key and aws_secret_key:
        container.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

    return container
