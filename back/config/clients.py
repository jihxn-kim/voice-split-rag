#####################################################
#                                                   #
#               클라이언트 의존성 정의                 #
#                                                   #
#####################################################

from langsmith import Client as LangSmithClient
from openai import AsyncOpenAI
import assemblyai as aai
import os
from dotenv import load_dotenv

load_dotenv()

# 모든 클라이언트 인스턴스를 담을 컨테이너 클래스
class ClientContainer:
    def __init__(self):
        self.openai_client = None
        self.langsmith_client = None
        self.assemblyai_api_key = None

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

    return container
