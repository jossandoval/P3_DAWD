# routes.py
from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS

import controllers


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # permite consumir desde otro puerto/origen (front desacoplado)

    # -----------------------------
    # Error handling centralizado
    # -----------------------------
    @app.errorhandler(controllers.APIError)
    def handle_api_error(err: controllers.APIError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(err):
        # En producción NO expondrías err, pero para tarea ayuda a depurar
        return jsonify({"error": "Internal server error", "details": str(err)}), 500

    # -----------------------------
    # Health check (opcional)
    # -----------------------------
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # -----------------------------
    # 1) Corroborar identificación
    # POST /auth/verify
    # -----------------------------
    @app.post("/auth/verify")
    def auth_verify():
        payload = request.get_json(silent=True) or {}
        result = controllers.verify_identifier(payload)
        return jsonify(result), 200

    # -----------------------------
    # 2) Registrar nuevo usuario
    # POST /users
    # -----------------------------
    @app.post("/users")
    def users_create():
        payload = request.get_json(silent=True) or {}
        result = controllers.register_user(payload)
        return jsonify(result), 201

    # -----------------------------
    # 3) Entregar preguntas
    # GET /quizzes/<quiz_id>/questions?user_id=...
    # -----------------------------
    @app.get("/quizzes/<quiz_id>/questions")
    def quizzes_questions(quiz_id: str):
        user_id = request.args.get("user_id", type=str)
        if not user_id:
            raise controllers.APIError(400, "Missing query param: user_id")

        result = controllers.deliver_questions(quiz_id, user_id)
        return jsonify(result), 200

    # -----------------------------
    # 4) Guardar respuestas
    # POST /quizzes/<quiz_id>/responses
    # -----------------------------
    @app.post("/quizzes/<quiz_id>/responses")
    def quizzes_responses_post(quiz_id: str):
        payload = request.get_json(silent=True) or {}
        result = controllers.store_answers(quiz_id, payload)
        return jsonify(result), 201

    # -----------------------------
    # 5) Entregar respuestas anteriores
    # GET /quizzes/<quiz_id>/responses?user_id=...
    # -----------------------------
    @app.get("/quizzes/<quiz_id>/responses")
    def quizzes_responses_get(quiz_id: str):
        user_id = request.args.get("user_id", type=str)
        if not user_id:
            raise controllers.APIError(400, "Missing query param: user_id")

        result = controllers.deliver_previous_answers(quiz_id, user_id)
        return jsonify(result), 200

    return app


if __name__ == "__main__":
    app = create_app()
    # debug=True para tarea; host=0.0.0.0 si lo necesitas en red local
    app.run(debug=True, port=5000)
