import requests


PROJECT_ID = 1

URL = (
    f"http://127.0.0.1:8000"
    f"/projects/{PROJECT_ID}/chat"
)


question = (
    "Explain what XGBoost does in this project "
    "and also tell me what the latest recommended "
    "XGBoost approach is according to current web sources."
)


response = requests.post(
    URL,
    json={
        "question": question,
    },
    timeout=120,
)


print("=" * 80)
print("STATUS:", response.status_code)
print("=" * 80)

print(response.json())