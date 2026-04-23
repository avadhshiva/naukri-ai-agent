from __future__ import annotations

import json
from typing import Iterable

from groq import Groq


SYSTEM_PROMPT = """You are a highly precise automated assistant filling out job screening forms.
Your goal is to provide the exact value required for the input field based ONLLY on the provided candidate profile.

STRICT OUTPUT RULES:
1. Return ONLY the final value. NO conversational filler, NO explanations, NO quotes, NO punctuation.
2. For numeric experience questions: Output ONLY the integer (e.g., "7"). If the skill is missing from the profile, output "0".
3. For Yes/No questions: Output ONLY "Yes" or "No".
4. For salary questions: Always output "As per market standards" unless a specific number is requested (then use a reasonable range based on profile).
5. For notice period: Output "Immediate" or "15 days".
6. If the answer is not in the profile, provide the most professionally appropriate generic answer (e.g., "As per industry norms").
7. Never invent specific certifications or company names.

Example User Questions & Correct Responses:
Q: "Total years of experience in Python?" -> A: "5"
Q: "Are you comfortable working in Bangalore?" -> A: "Yes"
Q: "Expected CTC?" -> A: "As per market standards"
"""


class GroqAnswerer:
    def __init__(self, api_key: str, candidate_profile: str):
        self.client = Groq(api_key=api_key) if api_key else None
        self.candidate_profile = candidate_profile

    def answer(self, question: str) -> str:
        if not self.client:
            return "As per profile"

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": f"### CANDIDATE PROFILE ###\n{self.candidate_profile}"},
                    {"role": "user", "content": f"Provide the exact answer for this form field: \"{question}\""},
                ],
                temperature=0.0, # Zero temperature for maximum precision
                max_tokens=50,
            )
            answer = (response.choices[0].message.content or "").strip()
            # Clean up common AI artifacts
            answer = answer.strip(' ".\'')
            return answer or "As per profile"
        except Exception as exc:
            print(f"[Groq] Precision answer() failed: {exc}")
            return "As per profile"

    def choose_option(self, question: str, options: Iterable[str]) -> str:
        option_list = [str(option).strip() for option in options if option and str(option).strip()]
        if not option_list:
            return ""

        if not self.client:
            return option_list[0]

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": f"### CANDIDATE PROFILE ###\n{self.candidate_profile}"},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\n"
                            f"Options: {json.dumps(option_list)}\n\n"
                            "Pick the most accurate option from the list above. Return ONLY the exact text of the chosen option."
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=60,
            )
            answer = (response.choices[0].message.content or "").strip().strip(' ".\'')
        except Exception as exc:
            print(f"[Groq] Precision choose_option() failed: {exc}")
            answer = ""

        # Advanced fuzzy matching
        answer_lower = answer.lower()
        
        # 1. Exact match
        for option in option_list:
            if answer_lower == option.lower():
                return option
                
        # 2. Containment match
        for option in option_list:
            opt_lower = option.lower()
            if answer_lower in opt_lower or opt_lower in answer_lower:
                return option
                
        # 3. Numeric match (if AI returned "5" and option is "5 years")
        import re
        numbers_in_answer = re.findall(r'\d+', answer)
        if numbers_in_answer:
            for option in option_list:
                if numbers_in_answer[0] in option:
                    return option

        return option_list[0]
