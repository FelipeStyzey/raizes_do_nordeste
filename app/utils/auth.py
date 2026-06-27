import jwt
import hashlib
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from app.utils.helpers import now_iso


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def verificar_senha(senha: str, hashed: str) -> bool:
    return hash_senha(senha) == hashed


def gerar_token(cliente_id: int, cpf: str) -> str:
    payload = {
        "sub": str(cliente_id),
        "cpf": cpf,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def requer_autenticacao(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({
                "error": "TOKEN_AUSENTE", "message": "Token de autenticação não informado.",
                "details": [], "timestamp": now_iso(), "path": request.path,
            }), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = decodificar_token(token)
            payload["sub"] = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return jsonify({
                "error": "TOKEN_EXPIRADO", "message": "Token expirado. Faça login novamente.",
                "details": [], "timestamp": now_iso(), "path": request.path,
            }), 401
        except jwt.InvalidTokenError as e:
            return jsonify({
                "error": "TOKEN_INVALIDO", "message": "Token de autenticação inválido.",
                "details": [], "timestamp": now_iso(), "path": request.path,
            }), 401
        kwargs["cliente_payload"] = payload
        return f(*args, **kwargs)
    return wrapper