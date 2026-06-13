from core.llm_router import LLMRouter
from models.question import Question, AnswerCandidate, stable_id


def test_voting_radio_aggregates_weighted_consensus() -> None:
    question = Question(
        id=stable_id("T-shirt size"),
        question="T-shirt size",
        options=["Small", "Medium", "Large"],
        type="radio",
    )
    router = LLMRouter(models=["a", "b", "c"])

    result = router.aggregate(
        question,
        [
            AnswerCandidate(question_id=question.id, model="a", option="Small", confidence=0.7),
            AnswerCandidate(question_id=question.id, model="b", option="small", confidence=0.8),
            AnswerCandidate(question_id=question.id, model="c", option="Large", confidence=0.9),
        ],
    )

    assert result.selected_option == "Small"
    assert len(result.candidates) == 3


def test_voting_checkbox_aggregates_multi_selection() -> None:
    question = Question(
        id=stable_id("Interests"),
        question="Interests",
        options=["Sports", "Music", "Reading", "Coding"],
        type="checkbox",
    )
    router = LLMRouter(models=["a", "b", "c"])

    result = router.aggregate(
        question,
        [
            AnswerCandidate(question_id=question.id, model="a", option="Sports, Music", confidence=0.8),
            AnswerCandidate(question_id=question.id, model="b", option="Coding, Music", confidence=0.7),
            AnswerCandidate(question_id=question.id, model="c", option="Music", confidence=0.9),
        ],
    )

    # Music is selected by all 3 models.
    assert "Music" in result.selected_option
    # Sports is selected by only 1 model (out of 3). 1 / 3 = 33%, which is less than the 40% threshold.
    assert "Sports" not in result.selected_option
    assert "Coding" not in result.selected_option


def test_voting_text_selects_highest_confidence() -> None:
    question = Question(
        id=stable_id("Tell us about yourself"),
        question="Tell us about yourself",
        options=[],
        type="text",
    )
    router = LLMRouter(models=["a", "b"])

    result = router.aggregate(
        question,
        [
            AnswerCandidate(question_id=question.id, model="a", option="I love coding.", confidence=0.6),
            AnswerCandidate(question_id=question.id, model="b", option="I build AI agents for fun.", confidence=0.95),
        ],
    )

    assert result.selected_option == "I build AI agents for fun."
