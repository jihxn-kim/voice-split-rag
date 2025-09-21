#####################################################
#                                                   #
#               클라이언트 의존성 정의                 #
#                                                   #
#####################################################

from langsmith import Client as LangSmithClient
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# 모든 클라이언트 인스턴스를 담을 컨테이너 클래스
class ClientContainer:
    def __init__(self):
        self.openai_client = None
        self.langsmith_client = None

# 클라이언트들을 초기화하는 함수
def initialize_clients() -> ClientContainer:
    container = ClientContainer()
    container.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    container.langsmith_client = LangSmithClient()

    return container
