from flask import request, jsonify
import re
from datetime import datetime, timezone

CANAIS_VALIDOS    = {"APP", "TOTEM", "BALCAO", "TELE_ENTREGA", "WEB", "PICKUP"}
UNIDADES_VALIDAS  = {"MATRIZ", "FILIAL_1", "FILIAL_2"}
METODOS_PAGAMENTO = {"PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "DINHEIRO"}

TRANSICOES_STATUS = {
    "AGUARDANDO_PAGAMENTO": {"EM_PREPARO", "CANCELADO"},
    "EM_PREPARO":           {"PRONTO", "CANCELADO"},
    "PRONTO":               {"ENTREGUE"},
    "ENTREGUE":             set(),
    "CANCELADO":            set(),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def erro(mensagem: str, codigo: str, status: int = 400, details: list = None, path: str = None):
    payload = {
        "error":     codigo,
        "message":   mensagem,
        "details":   details or [],
        "timestamp": now_iso(),
        "path":      path or request.path,
    }
    return jsonify(payload), status


def erro_validacao(campos: dict):
    details = [{"field": k, "issue": v} for k, v in campos.items()]
    payload = {
        "error":     "VALIDACAO",
        "message":   "Dados inválidos. Verifique os campos informados.",
        "details":   details,
        "timestamp": now_iso(),
        "path":      request.path,
    }
    return jsonify(payload), 422


CPF_RE = re.compile(r"^\d{11}$")


def validar_cpf_formato(cpf: str) -> bool:
    return bool(CPF_RE.match(cpf))


def validar_senha(senha: str) -> bool:
    return isinstance(senha, str) and len(senha) == 5 and senha.isdigit()


def row_to_dict(row) -> dict:
    return dict(row) if row else None
