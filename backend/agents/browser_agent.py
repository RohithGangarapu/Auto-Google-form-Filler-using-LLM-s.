from __future__ import annotations

from typing import Any

from core.selenium_driver import SeleniumFormDriver
from models.question import Question


class BrowserAgent:
    def __init__(self, driver: SeleniumFormDriver | None = None) -> None:
        self.driver = driver or SeleniumFormDriver()

    def open_for_manual_auth(self, url: str) -> None:
        self.driver.open_url(url)

    def scrape_questions_after_user_ready(self) -> list[Question]:
        return self.driver.scrape_questions()

    def fill_without_submitting(self, questions: list[Question], answers: dict[str, Any]) -> list[dict[str, Any]]:
        return self.driver.fill_answers(questions, answers)

    def close(self) -> None:
        self.driver.close()
