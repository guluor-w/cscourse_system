# import openai
# from config import OPENAI_API_KEY

# client = openai.OpenAI(api_key=OPENAI_API_KEY)

# def call_gpt(messages, model="gpt-3.5-turbo"):
#     response = client.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0.7
#     )
#     return response.choices[0].message.content

# analyzer/client.py

import os
import requests

# 从 config.py 中获取 API 密钥
from config import MOONSHOT_API_KEY

def analyze_with_moonshot(prompt: str) -> str:
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MOONSHOT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "moonshot-v1-32k",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError(f"Moonshot API 错误: {response.status_code} - {response.text}")
