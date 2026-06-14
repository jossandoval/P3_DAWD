# controllers.py
"""
Controllers (lógica de negocio) para API mínima de cuestionarios.
Aquí validamos reglas:
- identificar/registrar usuarios
- impedir doble respuesta
- validar quiz y preguntas
- validar required
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import model


# -----------------------------
# Excepción controlada para HTTP
# -----------------------------

@dataclass
class APIError(Exception):
    status_code: int
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


# -----------------------------
# Validaciones básicas
# -----------------------------

def _require_field(obj: Dict[str, Any], field: str) -> Any:
    if field not in obj or obj[field] in (None, "", []):
        raise APIError(400, f"Missing field: {field}")
    return obj[field]

def _ensure_user_exists(user_id: str) -> Dict[str, Any]:
    user = model.get_user(user_id)
    if not user:
        raise APIError(404, "User not found", {"user_id": user_id})
    return user

def _ensure_quiz_exists(quiz_id: str) -> Dict[str, Any]:
    quiz = model.get_quiz(quiz_id)
    if not quiz:
        raise APIError(404, "Quiz not found", {"quiz_id": quiz_id})
    return quiz

def _normalize_identifier(identifier: str) -> str:
    # Suficiente para la tarea: trim + lower.
    # (si tu profe quiere EXACTO, quita lower)
    return identifier.strip().lower()


# -----------------------------
# 1) Corroborar identificación
# -----------------------------

def verify_identifier(payload: Dict[str, Any]) -> Dict[str, Any]:
    identifier = _normalize_identifier(_require_field(payload, "identifier"))
    user = model.get_user_by_identifier(identifier)
    if user:
        return {"registered": True, "user_id": user["user_id"]}
    return {"registered": False, "user_id": None}


# -----------------------------
# 2) Registrar nuevo usuario
# -----------------------------

def register_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    identifier = _normalize_identifier(_require_field(payload, "identifier"))

    if model.identifier_exists(identifier):
        raise APIError(409, "Identifier already registered", {"identifier": identifier})

    created = model.create_user(identifier)
    # Para devolver justo lo requerido por el contrato:
    return {"user_id": created["user_id"], "identifier": created["identifier"]}


# -----------------------------
# 3) Entregar preguntas
# -----------------------------

def deliver_questions(quiz_id: str, user_id: str) -> Dict[str, Any]:
    _ensure_quiz_exists(quiz_id)
    _ensure_user_exists(user_id)

    if model.has_answered(user_id, quiz_id):
        raise APIError(
            409,
            "User already answered this quiz.",
            {"quiz_id": quiz_id, "user_id": user_id, "answered": True},
        )

    questions = model.get_questions(quiz_id) or []
    return {"quiz_id": quiz_id, "answered": False, "questions": questions}


# -----------------------------
# 4) Guardar respuestas
# -----------------------------

def store_answers(quiz_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_quiz_exists(quiz_id)

    user_id = _require_field(payload, "user_id")
    _ensure_user_exists(user_id)

    if model.has_answered(user_id, quiz_id):
        raise APIError(
            409,
            "User already answered this quiz.",
            {"quiz_id": quiz_id, "user_id": user_id},
        )

    answers = _require_field(payload, "answers")
    if not isinstance(answers, list) or len(answers) == 0:
        raise APIError(400, "Field 'answers' must be a non-empty list")

    # Validar que question_id exista en el quiz
    valid_qids = model.get_question_ids_set(quiz_id)
    if valid_qids is None:
        raise APIError(404, "Quiz not found", {"quiz_id": quiz_id})

    seen = set()
    cleaned_answers: List[Dict[str, Any]] = []

    for i, a in enumerate(answers):
        if not isinstance(a, dict):
            raise APIError(400, "Each answer must be an object", {"index": i})

        qid = a.get("question_id")
        if not qid:
            raise APIError(400, "Missing question_id in answers", {"index": i})

        if qid not in valid_qids:
            raise APIError(400, "Invalid question_id", {"question_id": qid})

        if qid in seen:
            raise APIError(400, "Duplicate question_id in answers", {"question_id": qid})

        seen.add(qid)

        # value puede ser string/numero/etc. No imponemos tipo fuerte.
        if "value" not in a:
            raise APIError(400, "Missing value in answers", {"question_id": qid})

        cleaned_answers.append({"question_id": qid, "value": a["value"]})

    # Validar required (todas las preguntas required deben venir)
    quiz = model.get_quiz(quiz_id)
    required_qids = {q["id"] for q in quiz["questions"] if q.get("required") is True}

    missing_required = sorted(list(required_qids - seen))
    if missing_required:
        raise APIError(
            400,
            "Missing required answers",
            {"missing_required": missing_required},
        )

    model.save_responses(user_id, quiz_id, cleaned_answers)
    return {"saved": True, "quiz_id": quiz_id, "user_id": user_id}


# -----------------------------
# 5) Entregar respuestas anteriores
# -----------------------------

def deliver_previous_answers(quiz_id: str, user_id: str) -> Dict[str, Any]:
    _ensure_quiz_exists(quiz_id)
    _ensure_user_exists(user_id)

    stored = model.get_responses(user_id, quiz_id)
    if not stored:
        return {"quiz_id": quiz_id, "user_id": user_id, "answered": False, "answers": []}

    return {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "answered": True,
        "answers": stored["answers"],
        "submitted_at": stored.get("submitted_at"),
    }
