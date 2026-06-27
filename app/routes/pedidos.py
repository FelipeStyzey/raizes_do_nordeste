from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import requer_autenticacao
from app.utils.helpers import erro, erro_validacao, row_to_dict, now_iso, CANAIS_VALIDOS, UNIDADES_VALIDAS, TRANSICOES_STATUS
from app.utils.audit import registrar_log
import json

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")
PONTOS_POR_REAL = 1

@pedidos_bp.route("", methods=["POST"])
@requer_autenticacao
def criar_pedido(cliente_payload):
    """
    Cria um pedido
    Centraliza pedidos de qualquer canal (APP, TOTEM, BALCAO, WEB, PICKUP, TELE_ENTREGA). 
    O campo canalPedido é obrigatório.
    
    tags:
      - Pedidos

    security:
      - Bearer: []

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [canalPedido, itens, formaPagamento]
          properties:
            canalPedido:
              type: string
              enum: [APP, TOTEM, BALCAO, TELE_ENTREGA, WEB, PICKUP]
              example: "TOTEM"
            unidade:
              type: string
              enum: [MATRIZ, FILIAL_1, FILIAL_2]
              example: "MATRIZ"
            itens:
              type: array
              items:
                type: object
                properties:
                  pratoId:
                    type: integer
                    example: 1
                  quantidade:
                    type: integer
                    example: 2
            formaPagamento:
              type: string
              enum: [PIX, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO]
              example: "PIX"

    responses:
      201:
        description: Pedido criado com sucesso
        examples:
          application/json: {"pedidoId": 1, "status": "AGUARDANDO_PAGAMENTO", "total": 40.0, "canalPedido": "TOTEM", "pontosGanhos": 40}
      401:
        description: Token ausente, inválido ou expirado
      404:
        description: Prato não encontrado na unidade informada
      422:
        description: "Erro de validação (ex: canalPedido ausente ou inválido)"
    """

    data = request.get_json(silent=True) or {}
    erros = {}

    canal      = (data.get("canalPedido")   or "").strip().upper()
    unidade    = (data.get("unidade")        or "MATRIZ").strip().upper()
    itens      =  data.get("itens")
    forma_pgto = (data.get("formaPagamento") or "").strip().upper()

    if not canal:
        erros["canalPedido"] = "Campo obrigatório."
    elif canal not in CANAIS_VALIDOS:
        erros["canalPedido"] = f"Valor inválido. Permitidos: {sorted(CANAIS_VALIDOS)}"

    if unidade not in UNIDADES_VALIDAS:
        erros["unidade"] = f"Valor inválido. Permitidos: {sorted(UNIDADES_VALIDAS)}"

    if not itens or not isinstance(itens, list) or len(itens) == 0:
        erros["itens"] = "Informe ao menos 1 item."

    if not forma_pgto:
        erros["formaPagamento"] = "Campo obrigatório."
    elif forma_pgto not in {"PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "DINHEIRO"}:
        erros["formaPagamento"] = "Valor inválido."

    if erros:
        return erro_validacao(erros)

    conn = get_connection()
    try:
        total = 0.0
        itens_validados = []

        for idx, item in enumerate(itens):
            prato_id   = item.get("pratoId")
            quantidade = item.get("quantidade", 1)

            if not prato_id:
                return erro_validacao({f"itens[{idx}].pratoId": "Obrigatório."})
            if not isinstance(quantidade, int) or quantidade < 1:
                return erro_validacao({f"itens[{idx}].quantidade": "Deve ser inteiro >= 1."})

            prato = conn.execute(
                "SELECT * FROM cardapio WHERE id = ? AND unidade = ? AND ativo = 1",
                (prato_id, unidade),
            ).fetchone()

            if not prato:
                return erro(f"Prato id={prato_id} não encontrado ou inativo na unidade {unidade}.", "PRATO_NAO_ENCONTRADO", 404)

            subtotal = prato["preco"] * quantidade
            total += subtotal
            itens_validados.append({"prato_id": prato_id, "quantidade": quantidade, "preco_unit": prato["preco"]})

        cur = conn.execute(
            """INSERT INTO pedidos (canal_pedido, cliente_id, unidade, total, forma_pagamento, status)
               VALUES (?,?,?,?,?,?)""",
            (canal, cliente_payload["sub"], unidade, total, forma_pgto, "AGUARDANDO_PAGAMENTO"),
        )
        pedido_id = cur.lastrowid

        for it in itens_validados:
            conn.execute(
                "INSERT INTO itens_pedido (pedido_id, prato_id, quantidade, preco_unit) VALUES (?,?,?,?)",
                (pedido_id, it["prato_id"], it["quantidade"], it["preco_unit"]),
            )

        pontos_ganhos = int(total * PONTOS_POR_REAL)
        conn.execute("UPDATE clientes SET pontos = pontos + ? WHERE id = ?", (pontos_ganhos, cliente_payload["sub"]))
        conn.commit()

        pedido = row_to_dict(conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone())
        registrar_log("CRIACAO_PEDIDO", "pedido", pedido_id, cliente_id=cliente_payload["sub"],
                     detalhes=json.dumps({"canal": canal, "total": total, "unidade": unidade}))
    finally:
        conn.close()

    return jsonify({
        "pedidoId": pedido_id, "status": pedido["status"], "total": pedido["total"],
        "canalPedido": pedido["canal_pedido"], "unidade": pedido["unidade"],
        "itens": [{"pratoId": it["prato_id"], "quantidade": it["quantidade"], "precoUnitario": it["preco_unit"]} for it in itens_validados],
        "pontosGanhos": pontos_ganhos, "createdAt": pedido["criado_em"],
    }), 201


@pedidos_bp.route("", methods=["GET"])
@requer_autenticacao
def listar_pedidos(cliente_payload):
    """
    Lista pedidos do cliente (com filtros e paginação).
    Permite filtrar por canal, unidade e status. 
    Suporta paginação via page/limit.
    
    tags:
      - Pedidos

    security:
      - Bearer: []

    parameters:
      - in: query
        name: canalPedido
        type: string
        enum: [APP, TOTEM, BALCAO, TELE_ENTREGA, WEB, PICKUP]
        required: false
      - in: query
        name: unidade
        type: string
        enum: [MATRIZ, FILIAL_1, FILIAL_2]
        required: false
      - in: query
        name: status
        type: string
        required: false
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 10

    responses:
      200:
        description: Lista paginada de pedidos
        examples:
          application/json: {"total": 1, "page": 1, "limit": 10, "pages": 1, "pedidos": [{"id": 1, "canal_pedido": "TOTEM", "status": "EM_PREPARO", "total": 40.0}]}
      401:
        description: Token ausente, inválido ou expirado
    """

    canal   = (request.args.get("canalPedido") or "").strip().upper() or None
    unidade = (request.args.get("unidade")     or "").strip().upper() or None
    status  = (request.args.get("status")      or "").strip().upper() or None

    try:
        page  = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 10))))
    except ValueError:
        return erro_validacao({"page/limit": "Devem ser números inteiros."})

    if canal and canal not in CANAIS_VALIDOS:
        return erro(f"canalPedido inválido. Permitidos: {sorted(CANAIS_VALIDOS)}", "CANAL_INVALIDO")
    if unidade and unidade not in UNIDADES_VALIDAS:
        return erro(f"unidade inválida. Permitidos: {sorted(UNIDADES_VALIDAS)}", "UNIDADE_INVALIDA")

    query  = "SELECT * FROM pedidos WHERE cliente_id = ?"
    params = [cliente_payload["sub"]]

    if canal:
        query += " AND canal_pedido = ?"; params.append(canal)
    if unidade:
        query += " AND unidade = ?"; params.append(unidade)
    if status:
        query += " AND status = ?"; params.append(status)

    count_q = query.replace("SELECT *", "SELECT COUNT(*)")
    query += " ORDER BY criado_em DESC LIMIT ? OFFSET ?"
    params_page = params + [limit, (page - 1) * limit]

    conn = get_connection()
    try:
        total_rows = conn.execute(count_q, params).fetchone()[0]
        rows = conn.execute(query, params_page).fetchall()
    finally:
        conn.close()

    return jsonify({
        "total": total_rows, "page": page, "limit": limit,
        "pages": (total_rows + limit - 1) // limit,
        "pedidos": [row_to_dict(r) for r in rows],
    }), 200


@pedidos_bp.route("/<int:pedido_id>", methods=["GET"])
@requer_autenticacao
def detalhar_pedido(pedido_id, cliente_payload):
    """
    Detalha um pedido.
    Retorna os dados completos de um pedido, incluindo os itens.

    tags:
      - Pedidos

    security:
      - Bearer: []

    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true

    responses:
      200:
        description: Pedido detalhado com itens
      401:
        description: Token ausente, inválido ou expirado
      404:
        description: Pedido não encontrado
    """

    conn = get_connection()
    try:
        pedido = conn.execute(
            "SELECT * FROM pedidos WHERE id = ? AND cliente_id = ?",
            (pedido_id, cliente_payload["sub"]),
        ).fetchone()

        if not pedido:
            return erro("Pedido não encontrado.", "NAO_ENCONTRADO", 404)

        itens = conn.execute(
            """SELECT ip.quantidade, ip.preco_unit, c.id as prato_id, c.nome AS prato, c.descricao
               FROM itens_pedido ip JOIN cardapio c ON c.id = ip.prato_id WHERE ip.pedido_id = ?""",
            (pedido_id,),
        ).fetchall()
    finally:
        conn.close()

    return jsonify({"pedido": {**row_to_dict(pedido), "itens": [row_to_dict(i) for i in itens]}}), 200


@pedidos_bp.route("/<int:pedido_id>/status", methods=["PATCH"])
@requer_autenticacao
def atualizar_status(pedido_id, cliente_payload):
    """
    Atualiza o status do pedido
    Fluxo válido: AGUARDANDO_PAGAMENTO → EM_PREPARO → PRONTO → ENTREGUE. 
    Cancelamento permitido em qualquer etapa, exceto ENTREGUE.
    
    tags:
      - Pedidos

    security:
      - Bearer: []

    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [status]
          properties:
            status:
              type: string
              enum: [AGUARDANDO_PAGAMENTO, EM_PREPARO, PRONTO, ENTREGUE, CANCELADO]
              example: "PRONTO"

    responses:
      200:
        description: Status atualizado com sucesso
      401:
        description: Token ausente, inválido ou expirado
      404:
        description: Pedido não encontrado
      409:
        description: Transição de status inválida
      422:
        description: Status ausente ou inválido
    """

    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip().upper()

    if not novo_status:
        return erro_validacao({"status": "Campo obrigatório."})
    if novo_status not in TRANSICOES_STATUS:
        return erro_validacao({"status": f"Status inválido. Permitidos: {sorted(TRANSICOES_STATUS.keys())}"})

    conn = get_connection()
    try:
        pedido = conn.execute(
            "SELECT * FROM pedidos WHERE id = ? AND cliente_id = ?",
            (pedido_id, cliente_payload["sub"]),
        ).fetchone()

        if not pedido:
            return erro("Pedido não encontrado.", "NAO_ENCONTRADO", 404)

        status_atual = pedido["status"]
        if novo_status not in TRANSICOES_STATUS.get(status_atual, set()):
            return erro(
                f"Transição inválida: {status_atual} → {novo_status}. Permitidas: {sorted(TRANSICOES_STATUS.get(status_atual, set()))}",
                "TRANSICAO_INVALIDA", 409,
            )

        conn.execute("UPDATE pedidos SET status = ?, atualizado_em = ? WHERE id = ?", (novo_status, now_iso(), pedido_id))
        conn.commit()

        pedido_atualizado = row_to_dict(conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone())
        registrar_log("MUDANCA_STATUS", "pedido", pedido_id, cliente_id=cliente_payload["sub"],
                     detalhes=json.dumps({"de": status_atual, "para": novo_status}))
        
    finally:
        conn.close()

    return jsonify({"message": f"Status atualizado de {status_atual} para {novo_status}.", "pedido": pedido_atualizado}), 200
