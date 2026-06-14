# model.py
"""
Modelo en memoria para una API mínima de cuestionarios (tipo Google Forms).
- No usa BD: guarda todo en estructuras globales (diccionarios).
- Provee funciones de lectura/escritura que usarán los controllers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Dict, Any, Optional, Tuple, List

# -----------------------------
# "Base de datos" en memoria
# -----------------------------

USERS: Dict[str, Dict[str, Any]] = {}            # user_id -> {"identifier": str, "created_at": iso}
IDENT_INDEX: Dict[str, str] = {}                 # identifier -> user_id


QUIZZES: Dict[str, Dict[str, Any]] = {
    "quiz1": {
        "title": "Cuestionario 1",
        "questions": [
            {"id": "q1", "text": "¿Cuál es tu nombre?", "type": "text", "required": True},
            {"id": "q2", "text": "¿Qué semestre cursas?", "type": "text", "required": True},
            {"id": "q3", "text": "Califica tu experiencia (1-5)", "type": "number", "required": False},
        ],
    }
}

# (user_id, quiz_id) -> {"answers": [{"question_id":..., "value":...}, ...], "submitted_at": iso}
RESPONSES: Dict[Tuple[str, str], Dict[str, Any]] = {}


# -----------------------------
# Helpers internos
# -----------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _new_uuid() -> str:
    return str(uuid.uuid4())


# -----------------------------
# Users
# -----------------------------

def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Regresa el usuario si el identifier existe, si no None."""
    user_id = IDENT_INDEX.get(identifier)
    if not user_id:
        return None
    user = USERS.get(user_id)
    if not user:
        return None
    return {"user_id": user_id, **user}

def identifier_exists(identifier: str) -> bool:
    return identifier in IDENT_INDEX

def create_user(identifier: str) -> Dict[str, Any]:
    """
    Crea un usuario nuevo.
    Recomendación: validar en controller que no exista antes.
    """
    user_id = _new_uuid()
    USERS[user_id] = {"identifier": identifier, "created_at": _now_iso()}
    IDENT_INDEX[identifier] = user_id
    return {"user_id": user_id, **USERS[user_id]}

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Regresa usuario por user_id o None."""
    user = USERS.get(user_id)
    if not user:
        return None
    return {"user_id": user_id, **user}


# -----------------------------
# Quizzes / Questions
# -----------------------------

def quiz_exists(quiz_id: str) -> bool:
    return quiz_id in QUIZZES

def get_quiz(quiz_id: str) -> Optional[Dict[str, Any]]:
    """Regresa el quiz completo (incluye title y questions) o None."""
    return QUIZZES.get(quiz_id)

def get_questions(quiz_id: str) -> Optional[List[Dict[str, Any]]]:
    """Regresa lista de preguntas o None si el quiz no existe."""
    quiz = QUIZZES.get(quiz_id)
    if not quiz:
        return None
    return quiz["questions"]

def get_question_ids_set(quiz_id: str) -> Optional[set]:
    """Set de ids válidos de preguntas para el quiz."""
    questions = get_questions(quiz_id)
    if questions is None:
        return None
    return {q["id"] for q in questions}


# -----------------------------
# Responses
# -----------------------------

def has_answered(user_id: str, quiz_id: str) -> bool:
    return (user_id, quiz_id) in RESPONSES

def save_responses(user_id: str, quiz_id: str, answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Guarda respuestas. No valida duplicados ni formatos complejos:
    esa lógica vive en controllers. Aquí solo persiste en memoria.
    """
    key = (user_id, quiz_id)
    RESPONSES[key] = {"answers": answers, "submitted_at": _now_iso()}
    return {"user_id": user_id, "quiz_id": quiz_id, **RESPONSES[key]}

def get_responses(user_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
    """Regresa respuestas si existen, si no None."""
    return RESPONSES.get((user_id, quiz_id))

def clear_memory() -> None:
    """
    Útil para pruebas/manual: limpia todo.
    """
    USERS.clear()
    IDENT_INDEX.clear()
    RESPONSES.clear()
