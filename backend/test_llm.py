from app.llm.client import generate_answer


answer = generate_answer(
    system_prompt=(
        "You are an expert AI and machine learning engineering copilot. "
        "Explain technical concepts clearly and accurately."
    ),
    user_prompt=(
        "Explain what XGBoost is, how it works, "
        "and when an ML engineer should use it."
    ),
)


print("=" * 80)
print(answer)
print("=" * 80)