import json
import ollama

MODEL = "llama3.2"

SPIRIT_ANIMALS = [
    "owl", "fox", "dolphin", "lion", "wolf", "elephant", "eagle", "deer",
    "octopus", "tiger", "bear", "butterfly", "horse", "raven", "cat", "dog",
    "cheetah", "penguin", "parrot", "panda",
]

SYSTEM = f"""You are a behavioral psychologist AI analyzing a user's computer activity.
You will receive multi-layer behavioral data and must output a JSON personality profile.

Output ONLY valid JSON matching this exact schema — no markdown, no explanation:
{{
  "ocean": {{
    "openness": <0.0–1.0>,
    "conscientiousness": <0.0–1.0>,
    "extraversion": <0.0–1.0>,
    "agreeableness": <0.0–1.0>,
    "neuroticism": <0.0–1.0>
  }},
  "interests": [<3–7 strings>],
  "fun_fact": "<one vivid sentence starting with 'This person tends to…'>",
  "spirit_animal": "<one animal from this list: {', '.join(SPIRIT_ANIMALS)}>",
  "spirit_animal_reason": "<one sentence explaining why>"
}}

Rules:
- Base all scores strictly on behavioral evidence in the data.
- spirit_animal must be chosen from the provided list only.
- If prior profiles exist, evolve the scores gradually rather than jumping wildly."""


def infer(context: str) -> dict:
    resp = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Behavioral data:\n\n{context}\n\nGenerate the profile."},
        ],
        format="json",
    )
    return json.loads(resp["message"]["content"])
