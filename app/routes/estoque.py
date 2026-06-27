from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import requer_autenticacao
from app.utils.helpers import erro, erro_validacao, row_to_dict, UNIDADES_VALIDAS

estoque_bp = Blueprint("estoque", __name__, url_prefix="/estoque")

@estoque_bp.route("", methods=["GET"])
@requer_autenticacao
def listar_estoque(cliente_payload):
    """
    Consulta o estoque por unidade.
    
    tags:
      - Estoque

    security:
      - Bearer: []

    parameters:
      - in: query
        name: unidade
        type: string
        enum: [MATRIZ, FILIAL_1, FILIAL_2]
        required: false
      - in: query
        name: insumo
        type: string
        required: false
        description: Busca parcial pelo nome do insumo

    responses:
      200:
        description: Lista de itens em estoque
        examples:
          application/json: {"total": 4, "estoque": [{"id": 1, "unidade": "MATRIZ", "insumo": "Produto 1", "quantidade": 200}]}
      401:
        description: Token ausente, inválido ou expirado.
    """

    unidade = (request.args.get("unidade") or "").strip().upper() or None
    insumo  = (request.args.get("insumo")  or "").strip()         or None

    if unidade and unidade not in UNIDADES_VALIDAS:
        return erro(f"unidade inválida. Permitidos: {sorted(UNIDADES_VALIDAS)}", "UNIDADE_INVALIDA")

    query  = "SELECT * FROM estoque WHERE 1=1"
    params = []
    if unidade:
        query += " AND unidade = ?"; params.append(unidade)
    if insumo:
        query += " AND insumo LIKE ?"; params.append(f"%{insumo}%")
    query += " ORDER BY unidade, insumo"

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return jsonify({"total": len(rows), "estoque": [row_to_dict(r) for r in rows]}), 200

@estoque_bp.route("", methods=["POST"])
@requer_autenticacao
def adicionar_estoque(cliente_payload):
    """
    Adiciona quantidade a um insumo.
    Cria o registro se não existir, ou soma à quantidade existente (UPSERT).
    
    tags:
      - Estoque

    security:
      - Bearer: []

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [unidade, insumo, quantidade]
          properties:
            unidade:
              type: string
              enum: [MATRIZ, FILIAL_1, FILIAL_2]
            insumo:
              type: string
              example: "Produto 5"
            quantidade:
              type: integer
              example: 100

    responses:
      200:
        description: Estoque atualizado
      422:
        description: Erro de validação
    """

    data = request.get_json(silent=True) or {}
    erros = {}
    unidade    = (data.get("unidade") or "").strip().upper()
    insumo     = (data.get("insumo")  or "").strip()
    quantidade =  data.get("quantidade")

    if not unidade:
        erros["unidade"] = "Campo obrigatório."
    elif unidade not in UNIDADES_VALIDAS:
        erros["unidade"] = f"Valor inválido. Permitidos: {sorted(UNIDADES_VALIDAS)}"
    if not insumo:
        erros["insumo"] = "Campo obrigatório."
    if quantidade is None:
        erros["quantidade"] = "Campo obrigatório."
    elif not isinstance(quantidade, int) or quantidade <= 0:
        erros["quantidade"] = "Deve ser inteiro > 0."

    if erros:
        return erro_validacao(erros)

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO estoque (unidade, insumo, quantidade) VALUES (?, ?, ?)
               ON CONFLICT(unidade, insumo) DO UPDATE SET quantidade = quantidade + excluded.quantidade""",
            (unidade, insumo, quantidade),
        )
        conn.commit()
        row = row_to_dict(conn.execute("SELECT * FROM estoque WHERE unidade = ? AND insumo = ?", (unidade, insumo)).fetchone())
    finally:
        conn.close()

    return jsonify({"message": "Estoque atualizado.", "estoque": row}), 200

@estoque_bp.route("/transferir", methods=["POST"])
@requer_autenticacao
def transferir(cliente_payload):
    """
    Transfere insumo da MATRIZ para uma filial.
    
    tags:
      - Estoque

    security:
      - Bearer: []

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [destino, insumo, quantidade]
          properties:
            destino:
              type: string
              enum: [FILIAL_1, FILIAL_2]
            insumo:
              type: string
              example: "Produto 1"
            quantidade:
              type: integer
              example: 10

    responses:
      200:
        description: Transferência realizada
      404:
        description: Insumo não encontrado na MATRIZ
      409:
        description: Estoque insuficiente na MATRIZ
      422:
        description: Erro de validação
    """

    data = request.get_json(silent=True) or {}
    erros = {}
    destino    = (data.get("destino") or "").strip().upper()
    insumo     = (data.get("insumo")  or "").strip()
    quantidade =  data.get("quantidade")

    if not destino:
        erros["destino"] = "Campo obrigatório."
    elif destino not in {"FILIAL_1", "FILIAL_2"}:
        erros["destino"] = "Apenas FILIAL_1 ou FILIAL_2 são destinos válidos."
    if not insumo:
        erros["insumo"] = "Campo obrigatório."
    if quantidade is None:
        erros["quantidade"] = "Campo obrigatório."
    elif not isinstance(quantidade, int) or quantidade <= 0:
        erros["quantidade"] = "Deve ser inteiro > 0."

    if erros:
        return erro_validacao(erros)

    conn = get_connection()
    try:
        origem_row = conn.execute("SELECT * FROM estoque WHERE unidade = 'MATRIZ' AND insumo = ?", (insumo,)).fetchone()
        if not origem_row:
            return erro(f"Insumo '{insumo}' não encontrado na MATRIZ.", "INSUMO_NAO_ENCONTRADO", 404)
        if origem_row["quantidade"] < quantidade:
            return erro(f"Estoque insuficiente na MATRIZ. Disponível: {origem_row['quantidade']}.", "ESTOQUE_INSUFICIENTE", 409)

        conn.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE unidade = 'MATRIZ' AND insumo = ?", (quantidade, insumo))
        conn.execute(
            """INSERT INTO estoque (unidade, insumo, quantidade) VALUES (?, ?, ?)
               ON CONFLICT(unidade, insumo) DO UPDATE SET quantidade = quantidade + excluded.quantidade""",
            (destino, insumo, quantidade),
        )
        conn.commit()

        matriz_atual  = row_to_dict(conn.execute("SELECT * FROM estoque WHERE unidade = 'MATRIZ' AND insumo = ?", (insumo,)).fetchone())
        destino_atual = row_to_dict(conn.execute("SELECT * FROM estoque WHERE unidade = ? AND insumo = ?", (destino, insumo)).fetchone())
    finally:
        conn.close()

    return jsonify({
        "message": f"{quantidade}x '{insumo}' transferido(s) da MATRIZ para {destino}.",
        "matriz": matriz_atual, "destino": destino_atual,
    }), 200

@estoque_bp.route("/<int:estoque_id>", methods=["PUT"])
@requer_autenticacao
def atualizar_estoque(estoque_id, cliente_payload):
    """
    Atualiza a quantidade absoluta de um item.
    Útil para correções de inventário.

    tags:
      - Estoque

    security:
      - Bearer: []

    parameters:
      - in: path
        name: estoque_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [quantidade]
          properties:
            quantidade:
              type: integer
              example: 250

    responses:
      200:
        description: Estoque atualizado
      404:
        description: Item de estoque não encontrado
      422:
        description: Erro de validação
    """
    
    data = request.get_json(silent=True) or {}
    quantidade = data.get("quantidade")

    if quantidade is None or not isinstance(quantidade, int) or quantidade < 0:
        return erro_validacao({"quantidade": "Deve ser inteiro >= 0."})

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM estoque WHERE id = ?", (estoque_id,)).fetchone()
        if not row:
            return erro("Item de estoque não encontrado.", "NAO_ENCONTRADO", 404)

        conn.execute("UPDATE estoque SET quantidade = ? WHERE id = ?", (quantidade, estoque_id))
        conn.commit()
        updated = row_to_dict(conn.execute("SELECT * FROM estoque WHERE id = ?", (estoque_id,)).fetchone())
    finally:
        conn.close()

    return jsonify({"message": "Estoque atualizado.", "estoque": updated}), 200
   