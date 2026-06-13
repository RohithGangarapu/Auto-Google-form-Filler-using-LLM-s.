from __future__ import annotations

from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from models.question import Question, stable_id


class SeleniumFormDriver:
    def __init__(self, headless: bool = False, implicit_wait_seconds: int = 3) -> None:
        self.headless = headless
        self.implicit_wait_seconds = implicit_wait_seconds
        self.driver: WebDriver | None = None

    def start(self) -> None:
        if self.driver:
            return
        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.driver.implicitly_wait(self.implicit_wait_seconds)

    def open_url(self, url: str) -> None:
        self.start()
        assert self.driver is not None
        self.driver.get(url)

    def scrape_questions(self) -> list[Question]:
        assert self.driver is not None, "Browser is not started"
        
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[role='listitem']")
            )
        )
        
        question_blocks = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div[role='listitem']"
        )
        
        questions: list[Question] = []
        for block in question_blocks:
            try:
                question_text = block.text.split("\n")[0].strip().rstrip("*").strip()
                if not question_text:
                    continue
                
                # Check for radios
                radios = block.find_elements(By.CSS_SELECTOR, "[role='radio']")
                # Check for checkboxes
                checkboxes = block.find_elements(By.CSS_SELECTOR, "[role='checkbox']")
                # Check for text fields
                textboxes = block.find_elements(By.CSS_SELECTOR, "input, textarea")
                
                q_type = "radio"
                options = []
                
                if radios:
                    q_type = "radio"
                    for radio in radios:
                        aria_label = radio.get_attribute("aria-label")
                        if aria_label:
                            options.append(aria_label)
                elif checkboxes:
                    q_type = "checkbox"
                    for cb in checkboxes:
                        aria_label = cb.get_attribute("aria-label")
                        if aria_label:
                            options.append(aria_label)
                else:
                    visible_textboxes = []
                    for tb in textboxes:
                        t_type = tb.get_attribute("type")
                        if t_type != "hidden" and tb.tag_name in ["input", "textarea"]:
                            visible_textboxes.append(tb)
                    if visible_textboxes:
                        if any(tb.tag_name == "textarea" for tb in visible_textboxes):
                            q_type = "paragraph"
                        else:
                            q_type = "text"
                            
                questions.append(
                    Question(
                        id=stable_id(question_text),
                        question=question_text,
                        options=options,
                        type=q_type
                    )
                )
            except Exception:
                pass
                
        return questions

    def fill_answers(self, questions: list[Question], answers: dict[str, Any]) -> list[dict[str, Any]]:
        assert self.driver is not None, "Browser is not started"
        results: list[dict[str, Any]] = []
        
        question_blocks = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div[role='listitem']"
        )
        
        block_by_text = {}
        for block in question_blocks:
            try:
                q_text = block.text.split("\n")[0].strip().rstrip("*").strip()
                if q_text:
                    block_by_text[q_text] = block
            except Exception:
                pass
                
        question_by_id = {question.id: question for question in questions}
        
        for question_id, answer in answers.items():
            question = question_by_id.get(question_id)
            if not question:
                results.append({"question_id": question_id, "filled": False, "error": "Unknown question"})
                continue
                
            block = block_by_text.get(question.question)
            if not block:
                results.append({"question_id": question_id, "filled": False, "error": "Question block not found"})
                continue
                
            try:
                filled = False
                
                if question.type == "radio":
                    for radio in block.find_elements(By.CSS_SELECTOR, "[role='radio']"):
                        if radio.get_attribute("aria-label") == answer:
                            radio.click()
                            filled = True
                            break
                            
                elif question.type == "checkbox":
                    target_options = []
                    if isinstance(answer, list):
                        target_options = [str(x).strip() for x in answer]
                    elif isinstance(answer, str):
                        target_options = [x.strip() for x in answer.split(",") if x.strip()]
                    else:
                        target_options = [str(answer).strip()]
                        
                    checkboxes = block.find_elements(By.CSS_SELECTOR, "[role='checkbox']")
                    for cb in checkboxes:
                        aria_label = cb.get_attribute("aria-label")
                        is_checked = cb.get_attribute("aria-checked") == "true"
                        should_be_checked = aria_label in target_options
                        if is_checked != should_be_checked:
                            cb.click()
                    filled = True
                    
                elif question.type in ["text", "paragraph"]:
                    textboxes = block.find_elements(By.CSS_SELECTOR, "input, textarea")
                    visible_tb = None
                    for tb in textboxes:
                        t_type = tb.get_attribute("type")
                        if t_type != "hidden" and tb.tag_name in ["input", "textarea"]:
                            visible_tb = tb
                            break
                            
                    if visible_tb:
                        visible_tb.click()
                        visible_tb.clear()
                        visible_tb.send_keys(str(answer))
                        filled = True
                        
                if filled:
                    results.append({"question_id": question_id, "filled": True})
                else:
                    results.append({"question_id": question_id, "filled": False, "error": f"Failed to fill for type {question.type}"})
            except Exception as exc:
                results.append({"question_id": question_id, "filled": False, "error": str(exc)})
                
        return results

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None
