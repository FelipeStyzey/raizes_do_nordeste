import random
import json
from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import requer_autenticacao
from app.utils.helpers import erro, erro_validacao, row_to_dict, now_iso, METODOS_PAGAMENTO
from app.utils.audit import registrar_log

pagamentos_bp = Blueprint("pagamentos", __name__, url_prefix="/pagamentos")
TAXA_APROVACAO = 0.80 

@pagamentos_bp.route("", methods=["POST"])
@requer_autenticacao
def processar(cliente_payload):
    """
    Processa o pagamento de um pedido (mock).
    Simula um gateway externo. 
    Aprovação aleatória com taxa de 80%. 
    Não processa valores reais.

    tags:
      - Pagamentos

    security:
      - Bearer: []

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [pedidoId, metodo]
          properties:
            pedidoId:
              type: integer
              example: 1
            metodo:
              type: string
              enum: [PIX, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO]
              example: "PIX"

    responses:
      200:
        description: Pagamento aprovado
        examples:
          application/json: {"message": "Pagamento do pedido aprovado.", "aprovado": true, "pedidoId": 1, "total": 40.0}
      402:
        description: Pagamento recusado
      404:
        description: Pedido não encontrado
      409:
        description: Pedido em status inválido para pagamento, ou já pago
      422:
        description: Erro de validação
    """

    data = request.get_json(silent=True) or {}
    erros = {}
    pedido_id = data.get("pedidoId")
    metodo    = (data.get("metodo") or "").strip().upper()

    if pedido_id is None:
        erros["pedidoId"] = "Campo obrigatório."
    elif not isinstance(pedido_id, int):
        erros["pedidoId"] = "Deve ser inteiro."
    if not metodo:
        erros["metodo"] = "Campo obrigatório."
    elif metodo not in METODOS_PAGAMENTO:
        erros["metodo"] = f"Valor inválido. Permitidos: {sorted(METODOS_PAGAMENTO)}"

    if erros:
        return erro_validacao(erros)

    conn = get_connection()
    try:
        pedido = conn.execute(
            "SELECT * FROM pedidos WHERE id = ? AND cliente_id = ?", (pedido_id, cliente_payload["sub"])
        ).fetchone()

        if not pedido:
            return erro("Pedido não encontrado.", "NAO_ENCONTRADO", 404)
        if pedido["status"] not in ("AGUARDANDO_PAGAMENTO", "PENDENTE"):
            return erro(f"Pedido com status '{pedido['status']}' não pode ser pago.", "STATUS_INVALIDO_PARA_PAGAMENTO", 409)

        pag_existente = conn.execute("SELECT * FROM pagamentos WHERE pedido_id = ?", (pedido_id,)).fetchone()
        if pag_existente:
            return erro("Já existe um processamento de pagamento para este pedido.", "PAGAMENTO_JA_PROCESSADO", 409)

        aprovado      = random.random() < TAXA_APROVACAO
        status_pgto   = "APROVADO" if aprovado else "RECUSADO"
        status_pedido = "EM_PREPARO" if aprovado else "AGUARDANDO_PAGAMENTO"
        mensagem      = "Pagamento do pedido aprovado." if aprovado else "Pagamento do pedido recusado. Tente novamente ou use outro método."

        conn.execute("INSERT INTO pagamentos (pedido_id, metodo, status) VALUES (?,?,?)", (pedido_id, metodo, status_pgto))
        conn.execute("UPDATE pedidos SET status = ?, atualizado_em = ? WHERE id = ?", (status_pedido, now_iso(), pedido_id))
        conn.commit()

        pagamento = row_to_dict(conn.execute("SELECT * FROM pagamentos WHERE pedido_id = ?", (pedido_id,)).fetchone())
        registrar_log("PAGAMENTO_PROCESSADO", "pagamento", pagamento["id"], cliente_id=cliente_payload["sub"],
                     detalhes=json.dumps({"pedido_id": pedido_id, "status": status_pgto, "metodo": metodo}))
    finally:
        conn.close()

    http_status = 200 if aprovado else 402
    return jsonify({
        "message": mensagem, "aprovado": aprovado, "pedidoId": pedido_id,
        "total": pedido["total"], "pagamento": pagamento,
    }), http_status

@pagamentos_bp.route("/<int:pedido_id>", methods=["GET"])
@requer_autenticacao
def consultar(pedido_id, cliente_payload):
    """
    Consulta o status de pagamento de um pedido

    tags:
      - Pagamentos

    security:
      - Bearer: []

    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true

    responses:
      200:
        description: Status do pagamento
      404:
        description: Pedido não encontrado
    """

    conn = get_connection()
    try:
        pedido = conn.execute(
            "SELECT id FROM pedidos WHERE id = ? AND cliente_id = ?", (pedido_id, cliente_payload["sub"])
        ).fetchone()
        if not pedido:
            return erro("Pedido não encontrado.", "NAO_ENCONTRADO", 404)

        pagamento = conn.execute("SELECT * FROM pagamentos WHERE pedido_id = ?", (pedido_id,)).fetchone()
    finally:
        conn.close()

    if not pagamento:
        return jsonify({"pedidoId": pedido_id, "status": "SEM_PAGAMENTO", "message": "Nenhum pagamento registrado para este pedido."}), 200

    return jsonify({"pagamento": row_to_dict(pagamento)}), 200
