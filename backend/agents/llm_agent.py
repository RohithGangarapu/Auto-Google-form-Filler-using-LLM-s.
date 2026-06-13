from __future__ import annotations

from models.question import Question, VotingResult
from core.llm_router import LLMRouter


class LLMAgent:
    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()

    def answer_questions(
        self,
        questions: list[Question],
        context: str = "",
        models: list[str] | None = None,
    ) -> dict[str, VotingResult]:
        original_models = self.router.models
        original_weights = self.router.model_weights
        
        if models:
            self.router.models = models
            self.router.model_weights = {model: 1.0 for model in models}
            
        try:
            return {
                question.id: self.router.answer_question(question=question, context=context)
                for question in questions
            }
        finally:
            if models:
                self.router.models = original_models
                self.router.model_weights = original_weights
