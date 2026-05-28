from openai import OpenAI

from services.config import config

client = OpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_BASE_URL,
)

MODEL = config.OPENAI_MODEL
