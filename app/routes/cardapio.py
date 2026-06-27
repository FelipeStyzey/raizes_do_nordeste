from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import requer_autenticacao
from app.utils.helpers import erro, erro_validacao, row_to_dict, UNIDADES_VALIDAS

cardapio_bp = Blueprint("cardapio", __name__, url_prefix="/cardapio")

@cardapio_bp.route("", methods = ["GET"])
def listar():
    """
    Listar o cardapio por unidade
    Consulta pública.
    Por padrão retorna apenas pratos ativos
    
    tags:
        - Cardápio
    
    parameters:
        - in: query
        name: unidade
        type: string
        enum: [MATRIZ, FILIAL_1, FILIAL_2]
        required: false

        -in: query
        name: ativo
        type: string
        default: "true"
        required: false
    responses:
    
    200:
        description: lista de pratos
        examples:
            applicatio/json: {
                "total": 3,
                "cardapio":[{
                    "id": 1,
                    "unidade": "MATRIZ",
                    "nome: "Carne de sol com macaxeira",
                    "preco": 20.00,
                    "ativo": 1}]}
    """

    unidade = (request.args.get("unidade") or "").strip().upper() or None
    ativo_q = (request.args.get("ativo") or "true").strip().lower()
    ativo = 1 if ativo_q != "false" else 0

    if unidade and unidade not in UNIDADES_VALIDAS:
        return erro(f"unidade inválida. Permitidos: {sorted(UNIDADES_VALIDAS)}", "UNIDADE_INVALIDA")

    query = "SELECT * FROM cardapio WHERE ativo = ?"
    params = [ativo]
    if unidade:
        query += " AND unidade = ?"
        params.append(unidade)
    query += " ORDER BY unidade, preco"

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return jsonify({"total": len(rows), "cardapio": [row_to_dict(r) for r in rows]}), 200

@cardapio_bp.route("/<int:prato_id>", methods=["GET"])
def detalhar(prato_id):
    """
    Detalha um prato
    
    tags:
      - Cardápio

    parameters:
      - in: path
        name: prato_id
        type: integer
        required: true

    responses:
      200:
        description: Dados do prato
      404:
        description: Prato não encontrado
    """

    conn = get_connection()
    try:
        prato = conn.execute("SELECT * FROM cardapio WHERE id = ?", (prato_id,)).fetchone()
    finally:
        conn.close()

    if not prato:
        return erro("Prato não encontrado.", "NAO_ENCONTRADO", 404)

    return jsonify({"prato": row_to_dict(prato)}), 200

@cardapio_bp.route("", methods=["POST"])
@requer_autenticacao
def criar(cliente_payload):
    """
    Adiciona um prato ao cardápio
    
    tags:
      - Cardápio

    security:
      - Bearer: []

    parameters:
      - in: body
        name: body
        required: true

        schema:
          type: object
          required: [unidade, nome, preco]
          properties:
            unidade:
              type: string
              enum: [MATRIZ, FILIAL_1, FILIAL_2]
            nome:
              type: string
              example: "Prato 4"
            preco:
              type: number
              example: 25.0
            descricao:
              type: string
              example: "Escondidinho de carne de sol"
              
    responses:
      201:
        description: Prato criado com sucesso
      409:
        description: Prato já existe nessa unidade
      422:
        description: Erro de validação
    """

    data = request.get_json(silent=True) or {}
    erros = {}
    unidade   = (data.get("unidade") or "").strip().upper()
    nome      = (data.get("nome")    or "").strip()
    preco     =  data.get("preco")
    descricao = (data.get("descricao") or "").strip() or None

    if not unidade:
        erros["unidade"] = "Campo obrigatório."
    elif unidade not in UNIDADES_VALIDAS:
        erros["unidade"] = f"Valor inválido. Permitidos: {sorted(UNIDADES_VALIDAS)}"
    if not nome:
        erros["nome"] = "Campo obrigatório."
    if preco is None:
        erros["preco"] = "Campo obrigatório."
    elif not isinstance(preco, (int, float)) or preco <= 0:
        erros["preco"] = "Deve ser número > 0."

    if erros:
        return erro_validacao(erros)

    conn = get_connection()
    try:
        existente = conn.execute("SELECT id FROM cardapio WHERE unidade = ? AND nome = ?", (unidade, nome)).fetchone()
        if existente:
            return erro("Já existe um prato com esse nome nessa unidade.", "PRATO_DUPLICADO", 409)

        cur = conn.execute(
            "INSERT INTO cardapio (unidade, nome, descricao, preco) VALUES (?,?,?,?)",
            (unidade, nome, descricao, float(preco)),
        )
        conn.commit()
        prato = row_to_dict(conn.execute("SELECT * FROM cardapio WHERE id = ?", (cur.lastrowid,)).fetchone())
    finally:
        conn.close()

    return jsonify({"message": "Prato adicionado ao cardápio.", "prato": prato}), 201

@cardapio_bp.route("/<int:prato_id>", methods=["PUT"])
@requer_autenticacao
def atualizar(prato_id, cliente_payload):
    """
    Atualiza um prato do cardápio

    tags:
      - Cardápio

    security:
      - Bearer: []

    parameters:
      - in: path
        name: prato_id
        type: integer
        required: true
      - in: body
        name: body

        schema:
          type: object
          properties:
            nome:
              type: string
            preco:
              type: number
            descricao:
              type: string
            ativo:
              type: boolean

    responses:
      200:
        description: Prato atualizado
      404:
        description: Prato não encontrado
      422:
        description: Erro de validação
    """

    data = request.get_json(silent=True) or {}
    erros = {}

    conn = get_connection()
    try:
        prato = conn.execute("SELECT * FROM cardapio WHERE id = ?", (prato_id,)).fetchone()
        if not prato:
            return erro("Prato não encontrado.", "NAO_ENCONTRADO", 404)

        nome      = (data.get("nome")      or "").strip() or prato["nome"]
        descricao = (data.get("descricao") or "").strip() or prato["descricao"]
        preco     =  data.get("preco",       prato["preco"])
        ativo     =  data.get("ativo",       bool(prato["ativo"]))

        if not isinstance(preco, (int, float)) or preco <= 0:
            erros["preco"] = "Deve ser número > 0."
        if not isinstance(ativo, bool):
            erros["ativo"] = "Deve ser booleano."
        if erros:
            return erro_validacao(erros)

        conn.execute(
            "UPDATE cardapio SET nome=?, descricao=?, preco=?, ativo=? WHERE id=?",
            (nome, descricao, float(preco), 1 if ativo else 0, prato_id),
        )
        conn.commit()
        updated = row_to_dict(conn.execute("SELECT * FROM cardapio WHERE id = ?", (prato_id,)).fetchone())
    finally:
        conn.close()

    return jsonify({"message": "Prato atualizado.", "prato": updated}), 200

@cardapio_bp.route("/<int:prato_id>", methods=["DELETE"])
@requer_autenticacao
def remover(prato_id, cliente_payload):
    """
    Remove (desativa) um prato
    Soft delete — o prato permanece no histórico de pedidos mas não aparece em novas consultas.
    
    tags:
      - Cardápio

    security:
      - Bearer: []

    parameters:
      - in: path
        name: prato_id
        type: integer
        required: true

    responses:
      200:
        description: Prato desativado
      404:
        description: Prato não encontrado
    """

    conn = get_connection()
    try:
        prato = conn.execute("SELECT id FROM cardapio WHERE id = ?", (prato_id,)).fetchone()
        if not prato:
            return erro("Prato não encontrado.", "NAO_ENCONTRADO", 404)

        conn.execute("UPDATE cardapio SET ativo = 0 WHERE id = ?", (prato_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "Prato removido do cardápio (desativado)."}), 200