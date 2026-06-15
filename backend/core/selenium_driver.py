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
        import os
        self.headless = headless or os.environ.get("SELENIUM_HEADLESS", "").lower() == "true"
        self.implicit_wait_seconds = implicit_wait_seconds
        self.driver: WebDriver | None = None

    def start(self) -> None:
        if self.driver:
            return
        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
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

    def scrape_questions(self, mode: str = "auto") -> list[Question]:
        assert self.driver is not None, "Browser is not started"
        
        if mode == "google":
            return self._scrape_google_form()
        elif mode == "generic":
            return self._scrape_generic_form()
        else:
            google_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
            if google_elements:
                return self._scrape_google_form()
            else:
                return self._scrape_generic_form()

    def _scrape_google_form(self) -> list[Question]:
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
                
                radios = block.find_elements(By.CSS_SELECTOR, "[role='radio']")
                checkboxes = block.find_elements(By.CSS_SELECTOR, "[role='checkbox']")
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

    def _scrape_generic_form(self) -> list[Question]:
        js_parser = """
        const getFormFields = () => {
          const fields = [];
          let fieldIndex = 0;
          
          const clean = (s) => (s || '').replace(/^\\*\\s*|\\s*\\*$/g, '').trim().replace(/:$/, '').trim();
          
          const getSelector = (el) => {
            if (el.id) return '#' + el.id;
            if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
            let path = '';
            let parent = el;
            while (parent && parent.nodeType === Node.ELEMENT_NODE) {
              let tag = parent.tagName.toLowerCase();
              let index = 1;
              let sibling = parent.previousSibling;
              while (sibling) {
                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === parent.tagName) {
                  index++;
                }
                sibling = sibling.previousSibling;
              }
              path = '/' + tag + '[' + index + ']' + path;
              parent = parent.parentNode;
            }
            return 'xpath:' + path;
          };
          
          const getQuestionTitle = (el) => {
            let curr = el;
            while (curr) {
              const titleEl = curr.querySelector('[data-automation-id="questionTitle"]');
              if (titleEl && titleEl.innerText.trim()) return titleEl.innerText.trim();
              curr = curr.parentElement;
            }
            curr = el;
            while (curr) {
              if (curr.tagName === 'FIELDSET') {
                const legend = curr.querySelector('legend');
                if (legend && legend.innerText.trim()) return legend.innerText.trim();
              }
              curr = curr.parentElement;
            }
            let labelledby = el.getAttribute('aria-labelledby');
            if (labelledby) {
              const labelEl = document.getElementById(labelledby.split(/\\s+/)[0]);
              if (labelEl && labelEl.innerText.trim()) return labelEl.innerText.trim();
            }
            return '';
          };
          
          const getLabel = (el) => {
            let labelledby = el.getAttribute('aria-labelledby');
            if (labelledby) {
              const ids = labelledby.split(/\\s+/);
              const labelTexts = [];
              ids.forEach(id => {
                const labelEl = document.getElementById(id);
                if (labelEl && labelEl.innerText.trim()) labelTexts.push(labelEl.innerText.trim());
              });
              if (labelTexts.length > 0) return labelTexts.join(' ').trim();
            }
            
            if (el.labels && el.labels.length > 0) {
              for (let i = 0; i < el.labels.length; i++) {
                if (el.labels[i].innerText.trim()) return el.labels[i].innerText.trim();
              }
            }
            
            let parent = el.parentElement;
            while (parent) {
              if (parent.tagName === 'LABEL') {
                const cloned = parent.cloneNode(true);
                const inputs = cloned.querySelectorAll('input, select, textarea');
                inputs.forEach(i => i.remove());
                if (cloned.innerText.trim()) return cloned.innerText.trim();
              }
              parent = parent.parentElement;
            }
            
            let placeholder = el.getAttribute('placeholder');
            if (placeholder && placeholder.trim()) return placeholder.trim();
            
            let ariaLabel = el.getAttribute('aria-label');
            if (ariaLabel && ariaLabel.trim()) {
              const cleanedVal = ariaLabel.trim().toLowerCase();
              const genericLabels = ["single line text", "multi-line text", "text input", "input text", "number", "text", "option", "choice"];
              if (!genericLabels.includes(cleanedVal)) return ariaLabel.trim();
            }
            
            let prev = el.previousElementSibling;
            if (prev && (prev.tagName === 'LABEL' || prev.tagName.match(/^H[1-6]$/)) && prev.innerText.trim()) {
              return prev.innerText.trim();
            }
            
            if (el.parentElement) {
              const containerText = el.parentElement.innerText.split('\\n')[0].trim();
              if (containerText && containerText.length < 100) return containerText;
            }
            
            return el.name || el.id || '';
          };
          
          const getFullLabel = (el) => {
            const title = getQuestionTitle(el);
            const subLabel = getLabel(el);
            
            const cleanTitle = clean(title);
            const cleanSub = clean(subLabel);
            
            if (cleanTitle && cleanSub && cleanTitle !== cleanSub) {
              const subLower = cleanSub.toLowerCase();
              const generic = ["single line text", "multi-line text", "text", "input", "value", "answer"];
              if (generic.includes(subLower) || cleanTitle.toLowerCase().includes(subLower)) {
                return cleanTitle;
              }
              return cleanTitle + ' - ' + cleanSub;
            }
            return cleanTitle || cleanSub || 'Field';
          };
          
          const inputs = Array.from(document.querySelectorAll('input, textarea, select, [role="radio"], [role="checkbox"]'));
          
          const radioGroups = {};
          const checkboxGroups = {};
          const standaloneFields = [];
          
          inputs.forEach(el => {
            const tagName = el.tagName.toLowerCase();
            const typeAttr = (el.getAttribute('type') || '').toLowerCase();
            const role = (el.getAttribute('role') || '').toLowerCase();
            
            const isRadio = (tagName === 'input' && typeAttr === 'radio') || role === 'radio';
            const isCheckbox = (tagName === 'input' && typeAttr === 'checkbox') || role === 'checkbox';
            
            if (tagName === 'input' && ['hidden', 'submit', 'button', 'image', 'reset'].includes(typeAttr)) {
              return;
            }
            
            if (isRadio) {
              const title = getQuestionTitle(el);
              const groupName = el.getAttribute('name') || ('radio_grp_' + title);
              if (!radioGroups[groupName]) {
                radioGroups[groupName] = { elements: [], title: title || groupName };
              }
              radioGroups[groupName].elements.push(el);
            } else if (isCheckbox) {
              const title = getQuestionTitle(el);
              const groupName = el.getAttribute('name') || ('cb_grp_' + title);
              if (!checkboxGroups[groupName]) {
                checkboxGroups[groupName] = { elements: [], title: title || groupName };
              }
              checkboxGroups[groupName].elements.push(el);
            } else {
              standaloneFields.push(el);
            }
          });
          
          standaloneFields.forEach(el => {
            const tagName = el.tagName.toLowerCase();
            let type = 'text';
            let options = [];
            
            if (tagName === 'textarea') {
              type = 'paragraph';
            } else if (tagName === 'select') {
              type = 'select';
              options = Array.from(el.options)
                .map(o => o.text.trim())
                .filter(t => t && t !== '' && !t.includes('Select...'));
            } else {
              type = 'text';
            }
            
            const labelText = getFullLabel(el);
            const fillId = 'field_' + (fieldIndex++);
            el.setAttribute('data-fill-id', fillId);
            
            fields.push({
              id: fillId,
              label: labelText,
              type: type,
              selector: getSelector(el),
              placeholder: el.getAttribute('placeholder') || '',
              options: options,
              required: el.required || false
            });
          });
          
          Object.keys(radioGroups).forEach(groupName => {
            const group = radioGroups[groupName];
            const elements = group.elements;
            const groupLabel = clean(group.title || groupName);
            
            const options = [];
            const fillId = 'field_' + (fieldIndex++);
            
            elements.forEach((radio, idx) => {
              let radioLabel = getLabel(radio);
              if (!radioLabel || clean(radioLabel) === groupLabel) {
                let sibling = radio.nextSibling;
                if (sibling && sibling.nodeType === Node.TEXT_NODE) {
                  radioLabel = sibling.textContent.trim();
                } else if (radio.nextElementSibling) {
                  radioLabel = radio.nextElementSibling.innerText.trim();
                }
              }
              options.push(radioLabel || radio.getAttribute('value') || ('Option ' + (idx + 1)));
              radio.setAttribute('data-fill-id', fillId + '_option_' + idx);
            });
            
            fields.push({
              id: fillId,
              label: groupLabel,
              type: 'radio',
              selector: elements[0].tagName.toLowerCase() === 'input' ? ('input[name="' + elements[0].getAttribute('name') + '"]') : '[role="radio"]',
              placeholder: '',
              options: options,
              required: elements.some(r => r.required)
            });
          });
          
          Object.keys(checkboxGroups).forEach(groupName => {
            const group = checkboxGroups[groupName];
            const elements = group.elements;
            const groupLabel = clean(group.title || groupName);
            
            if (elements.length === 1) {
              const cb = elements[0];
              const labelText = getFullLabel(cb);
              const fillId = 'field_' + (fieldIndex++);
              cb.setAttribute('data-fill-id', fillId);
              
              fields.push({
                id: fillId,
                label: labelText,
                type: 'checkbox',
                selector: getSelector(cb),
                placeholder: '',
                options: [],
                required: cb.required || false
              });
            } else {
              const options = [];
              const fillId = 'field_' + (fieldIndex++);
              
              elements.forEach((cb, idx) => {
                let cbLabel = getLabel(cb);
                if (!cbLabel || clean(cbLabel) === groupLabel) {
                  let sibling = cb.nextSibling;
                  if (sibling && sibling.nodeType === Node.TEXT_NODE) {
                    cbLabel = sibling.textContent.trim();
                  } else if (cb.nextElementSibling) {
                    cbLabel = cb.nextElementSibling.innerText.trim();
                  }
                }
                options.push(cbLabel || cb.getAttribute('value') || ('Option ' + (idx + 1)));
                cb.setAttribute('data-fill-id', fillId + '_option_' + idx);
              });
              
              fields.push({
                id: fillId,
                label: groupLabel,
                type: 'checkbox',
                selector: elements[0].tagName.toLowerCase() === 'input' ? ('input[name="' + elements[0].getAttribute('name') + '"]') : '[role="checkbox"]',
                placeholder: '',
                options: options,
                required: elements.some(c => c.required)
              });
            }
          });
          
          return fields;
        };
        return getFormFields();
        """
        raw_fields = self.driver.execute_script(js_parser)
        questions: list[Question] = []
        for field in raw_fields:
            questions.append(
                Question(
                    id=field["id"],
                    question=field["label"],
                    options=field["options"],
                    type=field["type"],
                    selector=field["selector"],
                    placeholder=field["placeholder"]
                )
            )
        return questions

    def fill_answers(self, questions: list[Question], answers: dict[str, Any]) -> list[dict[str, Any]]:
        assert self.driver is not None, "Browser is not started"
        
        is_generic = any(getattr(q, "selector", None) is not None for q in questions)
        if is_generic:
            return self._fill_generic_answers(questions, answers)
            
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

    def _fill_generic_answers(self, questions: list[Question], answers: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        question_by_id = {q.id: q for q in questions}
        
        for q_id, answer in answers.items():
            question = question_by_id.get(q_id)
            if not question:
                results.append({"question_id": q_id, "filled": False, "error": "Unknown question ID"})
                continue
                
            try:
                filled = False
                ans_str = str(answer).strip()
                
                if question.type in ["text", "paragraph"]:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}"]')
                    if elements:
                        el = elements[0]
                        el.click()
                        el.clear()
                        el.send_keys(ans_str)
                        filled = True
                        
                elif question.type == "select":
                    elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}"]')
                    if elements:
                        from selenium.webdriver.support.ui import Select
                        el = elements[0]
                        select = Select(el)
                        best_opt, match_score = self._find_best_matching_option(ans_str, question.options)
                        if best_opt:
                            select.select_by_visible_text(best_opt)
                            filled = True
                        else:
                            try:
                                select.select_by_visible_text(ans_str)
                                filled = True
                            except Exception:
                                select.select_by_value(ans_str)
                                filled = True
                                
                elif question.type == "radio":
                    best_opt, match_score = self._find_best_matching_option(ans_str, question.options)
                    if best_opt:
                        opt_idx = question.options.index(best_opt)
                        radio_elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}_option_{opt_idx}"]')
                        if radio_elements:
                            radio_elements[0].click()
                            filled = True
                    else:
                        for idx, opt in enumerate(question.options):
                            if ans_str.lower() in opt.lower():
                                radio_elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}_option_{idx}"]')
                                if radio_elements:
                                    radio_elements[0].click()
                                    filled = True
                                    break
                                    
                elif question.type == "checkbox":
                    if question.options:
                        target_options = []
                        if isinstance(answer, list):
                            target_options = [str(x).strip().lower() for x in answer]
                        elif isinstance(answer, str):
                            target_options = [x.strip().lower() for x in answer.split(",") if x.strip()]
                        else:
                            target_options = [str(answer).strip().lower()]
                            
                        for idx, opt in enumerate(question.options):
                            cb_elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}_option_{idx}"]')
                            if cb_elements:
                                cb_el = cb_elements[0]
                                is_checked = cb_el.is_selected()
                                if cb_el.tag_name != "input":
                                    is_checked = cb_el.get_attribute("aria-checked") == "true"
                                    
                                should_be_checked = opt.strip().lower() in target_options
                                if is_checked != should_be_checked:
                                    cb_el.click()
                        filled = True
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, f'[data-fill-id="{q_id}"]')
                        if elements:
                            el = elements[0]
                            is_checked = el.is_selected()
                            if el.tag_name != "input":
                                is_checked = el.get_attribute("aria-checked") == "true"
                                
                            should_be_checked = ans_str.lower() in ["true", "yes", "checked", "1", "select"]
                            if is_checked != should_be_checked:
                                el.click()
                            filled = True
                            
                if filled:
                    results.append({"question_id": q_id, "filled": True})
                else:
                    results.append({"question_id": q_id, "filled": False, "error": f"Failed to locate or fill for type {question.type}"})
            except Exception as exc:
                results.append({"question_id": q_id, "filled": False, "error": str(exc)})
                
        return results

    def _find_best_matching_option(self, candidate_option: str, options: list[str]) -> tuple[str | None, float]:
        if not options or not candidate_option:
            return None, 0.0
        import difflib
        best_option = None
        best_score = 0.0
        cand = candidate_option.strip().lower()
        for option in options:
            opt = option.strip().lower()
            if cand == opt:
                return option, 1.0
            if cand in opt or opt in cand:
                score = 0.9
            else:
                score = difflib.SequenceMatcher(None, cand, opt).ratio()
            if score > best_score:
                best_score = score
                best_option = option
        return best_option, best_score

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

