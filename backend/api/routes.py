from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import requests

from agents.orchestrator import FormAutomationOrchestrator
from models.session import FormSession


router = APIRouter()
orchestrator = FormAutomationOrchestrator()


class CreateSessionRequest(BaseModel):
    url: HttpUrl


class AnswerQuestionsRequest(BaseModel):
    context: str = ""
    models: list[str] = []


class FillAnswersRequest(BaseModel):
    answers: dict[str, Any] = {}


@router.get("/models")
def get_available_models() -> dict[str, Any]:
    try:
        router_instance = orchestrator.llm_agent.router
        if not router_instance.api_key:
            return {
                "available": [],
                "selected": [],
                "error": "OPENROUTER_API_KEY is not set. Please configure it in backend/.env file."
            }
        return {
            "available": router_instance.get_available_models(),
            "selected": router_instance.models
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sessions", response_model=FormSession)
def create_session(payload: CreateSessionRequest) -> FormSession:
    session = orchestrator.create_session(str(payload.url))
    try:
        return orchestrator.open_browser(session.id)
    except Exception as exc:  # noqa: BLE001 - surface setup failures to UI
        session.status = "error"
        session.error = str(exc)
        session.record("browser_open_failed", {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", response_model=FormSession)
def get_session(session_id: str) -> FormSession:
    try:
        return orchestrator.sessions[session_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc


@router.post("/sessions/{session_id}/scrape", response_model=FormSession)
def scrape_questions(session_id: str) -> FormSession:
    try:
        return orchestrator.scrape_after_user_ready(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/answer", response_model=FormSession)
def answer_questions(session_id: str, payload: AnswerQuestionsRequest) -> FormSession:
    try:
        return orchestrator.answer_questions(
            session_id,
            context=payload.context,
            models=payload.models if payload.models else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/fill")
def fill_answers(session_id: str, payload: FillAnswersRequest) -> dict[str, Any]:
    try:
        return orchestrator.fill_answers(session_id, custom_answers=payload.answers)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/close", response_model=FormSession)
def close_session(session_id: str) -> FormSession:
    try:
        return orchestrator.close(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
