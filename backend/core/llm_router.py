from __future__ import annotations

import difflib
import json
import os
import re
from collections import defaultdict
from typing import Any

import requests

from models.question import AnswerCandidate, Question, VotingResult


class LLMRouter:
    def __init__(
        self,
        models: list[str] | None = None,
        model_weights: dict[str, float] | None = None,
        timeout_seconds: int = 90,
    ) -> None:
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        
        # Curated list of default models to use if not specified
        if models:
            self.models = models
        else:
            self.models = [
                "google/gemma-4-31b-it:free",
                "qwen/qwen-2.5-72b-instruct",
                "deepseek/deepseek-chat",
            ]
            
        self.model_weights = model_weights or {model: 1.0 for model in self.models}
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def get_available_models() -> list[str]:
        return [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-4-31b-it:free",
            "qwen/qwen3-coder:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
            "qwen/qwen-2.5-72b-instruct",
            "deepseek/deepseek-chat",
        ]

    def answer_question(self, question: Question, context: str = "") -> VotingResult:
        candidates: list[AnswerCandidate] = []
        for model in self.models:
            try:
                candidates.append(self._ask_model(model, question, context))
            except Exception as exc:  # noqa: BLE001 - keep audit visible per model
                candidates.append(
                    AnswerCandidate(
                        question_id=question.id,
                        model=model,
                        option="",
                        confidence=0.0,
                        reasoning=f"Model call failed: {exc}",
                    )
                )
        return self.aggregate(question, candidates)

    def aggregate(self, question: Question, candidates: list[AnswerCandidate]) -> VotingResult:
        # Determine active candidates
        active_candidates = [c for c in candidates if c.confidence > 0 or c.option]
        if not active_candidates:
            active_candidates = candidates
            
        total_weight = sum(self.model_weights.get(c.model, 1.0) for c in active_candidates) or 1.0

        if question.type == "checkbox" and question.options:
            # Checkbox voting: score each option individually
            option_scores: dict[str, float] = defaultdict(float)
            option_voters: dict[str, list[str]] = defaultdict(list)
            
            for option in question.options:
                canonical_opt = self._canonical_option(option)
                for candidate in candidates:
                    if not candidate.option:
                        continue
                    # A candidate answer could be a comma-separated list of selected options
                    candidate_options = [self._canonical_option(o) for o in candidate.option.split(",")]
                    # Check if our option matches any candidate option
                    matched = False
                    for cand_opt in candidate_options:
                        _, match_score = self._find_best_matching_option(cand_opt, [option])
                        if match_score >= 0.8:
                            matched = True
                            break
                    if matched:
                        weight = self.model_weights.get(candidate.model, 1.0)
                        option_scores[option] += candidate.confidence * weight
                        option_voters[option].append(candidate.model)
            
            # Select options that have majority support
            selected_options = []
            final_scores = {}
            for option in question.options:
                score = option_scores.get(option, 0.0)
                voters = option_voters.get(option, [])
                if len(voters) >= len(active_candidates) * 0.4 or (len(voters) > 0 and len(option_voters) == 1):
                    selected_options.append(option)
                final_scores[option] = score
                
            selected_str = ", ".join(selected_options)
            
            # Confidence is the average confidence of selected options
            avg_confidence = 0.0
            if selected_options:
                voters_conf = []
                for opt in selected_options:
                    for c in candidates:
                        if c.model in option_voters.get(opt, []):
                            voters_conf.append(c.confidence)
                avg_confidence = sum(voters_conf) / len(voters_conf) if voters_conf else 0.5
            
            return VotingResult(
                question_id=question.id,
                selected_option=selected_str,
                confidence=avg_confidence,
                candidates=candidates,
                scores=final_scores,
            )
            
        elif question.type in ["text", "paragraph"]:
            # Free-text: choose candidate with highest confidence
            best_candidate = None
            for candidate in candidates:
                if not candidate.option:
                    continue
                if best_candidate is None:
                    best_candidate = candidate
                elif candidate.confidence > best_candidate.confidence:
                    best_candidate = candidate
                elif candidate.confidence == best_candidate.confidence:
                    if len(candidate.option) > len(best_candidate.option):
                        best_candidate = candidate
            
            if best_candidate:
                return VotingResult(
                    question_id=question.id,
                    selected_option=best_candidate.option,
                    confidence=best_candidate.confidence,
                    candidates=candidates,
                    scores={c.model: c.confidence for c in candidates if c.option},
                )
            else:
                return VotingResult(
                    question_id=question.id,
                    selected_option="",
                    confidence=0.0,
                    candidates=candidates,
                    scores={},
                )
        else:
            # Radio/choice-based questions
            scores: dict[str, float] = defaultdict(float)
            display_labels: dict[str, str] = {}
            for candidate in candidates:
                if not candidate.option:
                    continue
                best_opt, match_score = self._find_best_matching_option(candidate.option, question.options)
                if best_opt and match_score >= 0.3:
                    option_key = self._canonical_option(best_opt)
                    weight = self.model_weights.get(candidate.model, 1.0)
                    scores[option_key] += candidate.confidence * weight * match_score
                    display_labels[option_key] = best_opt
                    
            if not scores:
                return VotingResult(
                    question_id=question.id,
                    selected_option="",
                    confidence=0.0,
                    candidates=candidates,
                    scores={},
                )
                
            selected_key, selected_score = max(scores.items(), key=lambda item: item[1])
            total_score = sum(scores.values()) or 1.0
            return VotingResult(
                question_id=question.id,
                selected_option=display_labels.get(selected_key, selected_key),
                confidence=min(selected_score / total_score, 1.0),
                candidates=candidates,
                scores=dict(scores),
            )

    def _find_best_matching_option(self, candidate_option: str, options: list[str]) -> tuple[str | None, float]:
        if not options or not candidate_option:
            return None, 0.0

        canonical_candidate = self._canonical_option(candidate_option)
        if not canonical_candidate:
            return None, 0.0

        best_option = None
        best_score = 0.0

        for option in options:
            canonical_label = self._canonical_option(option)

            # Exact match check
            if canonical_candidate == canonical_label:
                return option, 1.0

            # Substring match check
            if canonical_candidate in canonical_label:
                score = 0.95
            elif canonical_label in canonical_candidate:
                score = 0.9
            else:
                # Fuzzy match using SequenceMatcher
                score = difflib.SequenceMatcher(None, canonical_candidate, canonical_label).ratio()

            if score > best_score:
                best_score = score
                best_option = option

        return best_option, best_score

    def _ask_model(self, model: str, question: Question, context: str) -> AnswerCandidate:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set. Please configure it in backend/.env file.")

        prompt = self._build_prompt(question, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/RohithGangarapu/Auto-Google-form-Filler-using-LLM-s",
            "X-Title": "Auto Google Form Filler",
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        
        resp_json = response.json()
        raw_text = ""
        if "choices" in resp_json and len(resp_json["choices"]) > 0:
            raw_text = resp_json["choices"][0].get("message", {}).get("content", "")
            
        parsed = self._parse_model_json(raw_text)
        
        opt_val = parsed.get("option", "")
        if isinstance(opt_val, list):
            opt_str = ", ".join(str(o).strip() for o in opt_val)
        else:
            opt_str = str(opt_val).strip()

        return AnswerCandidate(
            question_id=question.id,
            model=model,
            option=opt_str,
            confidence=self._coerce_confidence(parsed.get("confidence")),
            reasoning=str(parsed.get("reasoning", "")).strip(),
            raw_response=raw_text,
        )

    def answer_questions_bulk(
        self,
        questions: list[Question],
        context: str = "",
    ) -> dict[str, VotingResult]:
        candidates_by_question: dict[str, list[AnswerCandidate]] = {
            q.id: [] for q in questions
        }
        
        for model in self.models:
            try:
                model_answers = self._ask_model_bulk(model, questions, context)
                for q_id, candidate in model_answers.items():
                    if q_id in candidates_by_question:
                        candidates_by_question[q_id].append(candidate)
            except Exception as exc:
                for q in questions:
                    candidates_by_question[q.id].append(
                        AnswerCandidate(
                            question_id=q.id,
                            model=model,
                            option="",
                            confidence=0.0,
                            reasoning=f"Bulk model call failed: {exc}",
                        )
                    )
                    
        results = {}
        for q in questions:
            results[q.id] = self.aggregate(q, candidates_by_question[q.id])
            
        return results

    def _ask_model_bulk(self, model: str, questions: list[Question], context: str) -> dict[str, AnswerCandidate]:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set. Please configure it in backend/.env file.")

        prompt = self._build_bulk_prompt(questions, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/RohithGangarapu/Auto-Google-form-Filler-using-LLM-s",
            "X-Title": "Auto Google Form Filler",
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        
        resp_json = response.json()
        raw_text = ""
        if "choices" in resp_json and len(resp_json["choices"]) > 0:
            raw_text = resp_json["choices"][0].get("message", {}).get("content", "")
            
        parsed_bulk = self._parse_model_json(raw_text)
        
        candidates = {}
        for question in questions:
            q_data = parsed_bulk.get(question.id, {})
            if not isinstance(q_data, dict):
                q_data = {"option": q_data, "confidence": 0.5, "reasoning": ""}
                
            opt_val = q_data.get("option", "")
            if isinstance(opt_val, list):
                opt_str = ", ".join(str(o).strip() for o in opt_val)
            else:
                opt_str = str(opt_val).strip()
                
            candidates[question.id] = AnswerCandidate(
                question_id=question.id,
                model=model,
                option=opt_str,
                confidence=self._coerce_confidence(q_data.get("confidence", 0.0 if not opt_str else 0.5)),
                reasoning=str(q_data.get("reasoning", "")).strip(),
                raw_response=raw_text,
            )
            
        return candidates

    def _build_bulk_prompt(self, questions: list[Question], context: str) -> str:
        fields_desc = []
        for q in questions:
            field_info = {
                "id": q.id,
                "label": q.question,
                "type": q.type,
            }
            if q.options:
                field_info["options"] = q.options
            fields_desc.append(field_info)
            
        fields_json = json.dumps(fields_desc, indent=2)
        
        return (
            "You are helping a user fill out a web form (such as a job application).\n"
            "Use the provided User Context (like their resume or personal details) to answer all questions in the form.\n\n"
            f"--- USER CONTEXT ---\n{context or 'No context provided.'}\n\n"
            f"--- FORM FIELDS ---\n{fields_json}\n\n"
            "--- INSTRUCTIONS ---\n"
            "For each field, determine the appropriate response based on the user context:\n"
            "1. For 'text' or 'paragraph' fields: Provide a direct, concise response.\n"
            "2. For 'select' or 'radio' fields: Choose the exact option from the list of options that best matches. If none match, pick the closest match or leave empty if not required.\n"
            "3. For 'checkbox' fields: Select one or more matching options, and return them as a comma-separated list (e.g. 'Option A, Option C').\n\n"
            "Return ONLY a valid JSON object matching the following schema. Do NOT wrap it in HTML or write any explanatory text outside the JSON. "
            "The root keys must be the exact field IDs, and each value must be an object with keys 'option', 'confidence' (value between 0.0 and 1.0), and 'reasoning'.\n\n"
            "Example output format:\n"
            "{\n"
            "  \"field_0\": {\n"
            "    \"option\": \"John Doe\",\n"
            "    \"confidence\": 1.0,\n"
            "    \"reasoning\": \"User's first and last name from context\"\n"
            "  }\n"
            "}\n"
        )

    def _build_prompt(self, question: Question, context: str) -> str:
        options = question.options
        if question.type == "checkbox":
            instruction = (
                "This is a multiple-selection checkbox question. You can select one or more options. "
                "Return a JSON array of selected options in the 'option' field, e.g. [\"Option A\", \"Option C\"]."
            )
        elif question.type in ["text", "paragraph"]:
            instruction = (
                "This is a free-text open-ended question. "
                "Provide a concise, direct answer in the 'option' field."
            )
        else:
            instruction = (
                "This is a single-choice multiple-choice question. "
                "Choose the best single answer from the available options. "
                "Return the exact chosen option in the 'option' field."
            )

        return (
            "You are helping fill a web form. Do NOT explain your answer. Be as fast as possible. Omit any reasoning or extra text.\n"
            f"{instruction}\n"
            "Return only valid JSON with keys: \"option\", \"confidence\". Do NOT write any other keys or explanation. Do not write text outside the JSON.\n\n"
            f"Context:\n{context or 'No extra context provided.'}\n\n"
            f"Question:\n{question.question}\n"
            f"Options: {json.dumps(options, ensure_ascii=True)}\n"
        )

    @staticmethod
    def _parse_model_json(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        # Clean up markdown code blocks if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {"option": "", "confidence": 0.0, "reasoning": raw_text}

    @staticmethod
    def _coerce_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        if confidence > 1.0:
            confidence = confidence / 100.0
        return max(0.0, min(confidence, 1.0))

    @staticmethod
    def _canonical_option(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip().casefold()
