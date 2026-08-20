import requests


PROJECT_ID = 1

URL = (
    f"http://127.0.0.1:8000/"
    f"projects/{PROJECT_ID}/chat"
)


payload = {
    "question": (
        "What does this project use XGBoost for?"
    )
}


response = requests.post(
    URL,
    json=payload,
    timeout=120,
)


print("=" * 80)

print("Status:", response.status_code)

print("=" * 80)

print(response.json())

print("=" * 80)