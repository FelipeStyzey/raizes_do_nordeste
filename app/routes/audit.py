from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import requer_autenticacao
from app.utils.helpers import erro, row_to_dict

audit_bp = Blueprint("audit", __name__, url_prefix="/auditoria")

@audit_bp.route("", methods=["GET"])
@requer_autenticacao
def listar_logs(cliente_payload):
    """
    Lista registros de auditoria do cliente
    Rastreabilidade de ações sensíveis (LGPD): cadastro, login, criação de pedido, mudança de status e pagamento.
    ---
    tags:
      - Auditoria
    security:
      - Bearer: []
    parameters:
      - in: query
        name: acao
        type: string
        required: false
        description: "Filtra por tipo de ação (ex.: LOGIN, CRIACAO_PEDIDO)"
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 20
    responses:
      200:
        description: Lista paginada de logs
        examples:
          application/json: {"total": 5, "page": 1, "limit": 20, "logs": [{"id": 1, "acao": "LOGIN", "entidade": "cliente", "criado_em": "2026-06-07T14:00:00Z"}]}
      401:
        description: Token ausente, inválido ou expirado
    """
    acao = (request.args.get("acao") or "").strip().upper() or None
    try:
        page  = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 20))))
    except ValueError:
        return erro("Parâmetros de paginação inválidos.", "PARAMETROS_INVALIDOS")

    query  = "SELECT * FROM audit_log WHERE cliente_id = ?"
    params = [cliente_payload["sub"]]
    if acao:
        query += " AND acao = ?"; params.append(acao)

    count_q = query.replace("SELECT *", "SELECT COUNT(*)")
    query  += " ORDER BY criado_em DESC LIMIT ? OFFSET ?"
    params_p = params + [limit, (page - 1) * limit]

    conn = get_connection()
    try:
        total = conn.execute(count_q, params).fetchone()[0]
        rows  = conn.execute(query, params_p).fetchall()
    finally:
        conn.close()

    return jsonify({"total": total, "page": page, "limit": limit, "logs": [row_to_dict(r) for r in rows]}), 200
