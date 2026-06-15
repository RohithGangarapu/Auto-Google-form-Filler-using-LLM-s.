from __future__ import annotations

from typing import Any

from agents.browser_agent import BrowserAgent
from agents.llm_agent import LLMAgent
from models.session import FormSession


from models.question import VotingResult


class FormAutomationOrchestrator:
    def __init__(self) -> None:
        self.sessions: dict[str, FormSession] = {}
        self.browser_agents: dict[str, BrowserAgent] = {}
        self.llm_agent = LLMAgent()

    def create_session(self, url: str) -> FormSession:
        session = FormSession(url=url)
        session.record("session_created", {"url": url})
        self.sessions[session.id] = session
        return session

    def open_browser(self, session_id: str) -> FormSession:
        session = self._session(session_id)
        browser_agent = BrowserAgent()
        browser_agent.open_for_manual_auth(session.url)
        self.browser_agents[session_id] = browser_agent
        session.status = "waiting_for_user_auth"
        session.record("browser_opened_for_manual_auth")
        return session

    def scrape_after_user_ready(self, session_id: str, mode: str = "auto") -> FormSession:
        session = self._session(session_id)
        browser_agent = self._browser_agent(session_id)
        session.questions = browser_agent.scrape_questions_after_user_ready(mode=mode)
        session.status = "scraped"
        session.record("questions_scraped", {"count": len(session.questions), "mode": mode})
        return session

    def answer_questions(
        self,
        session_id: str,
        context: str = "",
        models: list[str] | None = None,
    ) -> FormSession:
        session = self._session(session_id)
        session.answers = self.llm_agent.answer_questions(
            session.questions,
            context=context,
            models=models,
        )
        session.status = "answered"
        session.record(
            "questions_answered",
            {
                "count": len(session.answers),
                "audit": {
                    question_id: answer.model_dump()
                    for question_id, answer in session.answers.items()
                },
            },
        )
        return session

    def fill_answers(
        self,
        session_id: str,
        custom_answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._session(session_id)
        browser_agent = self._browser_agent(session_id)
        
        # Merge or use custom answers
        if custom_answers is not None:
            selected_answers = custom_answers
            # Keep session.answers in sync with manual user edits
            for q_id, opt in custom_answers.items():
                if q_id in session.answers:
                    session.answers[q_id].selected_option = str(opt)
                else:
                    session.answers[q_id] = VotingResult(
                        question_id=q_id,
                        selected_option=str(opt),
                        confidence=1.0,
                        candidates=[],
                        scores={},
                    )
        else:
            selected_answers = {
                question_id: voting_result.selected_option
                for question_id, voting_result in session.answers.items()
            }
            
        fill_results = browser_agent.fill_without_submitting(session.questions, selected_answers)
        session.status = "filled"
        session.record("answers_filled_without_submit", {"results": fill_results})
        return {"session": session, "fill_results": fill_results}

    def close(self, session_id: str) -> FormSession:
        session = self._session(session_id)
        browser_agent = self.browser_agents.pop(session_id, None)
        if browser_agent:
            browser_agent.close()
        session.status = "closed"
        session.record("session_closed")
        return session

    def _session(self, session_id: str) -> FormSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session: {session_id}") from exc

    def _browser_agent(self, session_id: str) -> BrowserAgent:
        try:
            return self.browser_agents[session_id]
        except KeyError as exc:
            raise KeyError(f"Browser is not open for session: {session_id}") from exc
