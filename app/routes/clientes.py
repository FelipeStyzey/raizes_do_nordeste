from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.utils.auth import hash_senha, verificar_senha, gerar_token, requer_autenticacao
from app.utils.helpers import erro, erro_validacao, row_to_dict, validar_cpf_formato, validar_senha
from app.utils.audit import registrar_log

#Para toda rota clientes, colocar clientes/cadastro, clientes/login e etc

clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")

@clientes_bp.route("/cadastro", methods=["POST"])
def cadastrar():
    """
    Cadastra um novo cliente:
    Cria a conta do cliente exigindo consentimento explícito (LGPD).
    A senha é armazenada como hash SHA-256.
    
    tags:
      - Clientes

    parameters:
      - in: body
        name: body
        required: true

        schema:
          type: object
          required: [nome, cpf, senha, consentimento]

        properties:
            nome:
            type: string
            example: "Maria da Silva"
            cpf:
              type: string
              example: "12345678901"
              description: "Exatamente 11 dígitos numéricos"
            senha:
              type: string
              example: "12345"
              description: "Exatamente 5 dígitos numéricos"
            consentimento:
              type: boolean
              example: true
              description: "Aceite obrigatório do uso de dados pessoais (LGPD)"

    responses:
      201:
        description: Cliente cadastrado com sucesso
        examples:
          application/json: {"message": "Cliente cadastrado com sucesso.", "cliente": {"id": 1, "nome": "Maria Silva", "cpf": "12345678901", "pontos": 0}}
      409:
        description: CPF já cadastrado
      422:
        description: Erro de validação de campos
    """

    data = request.get_json(silent=True) or {}
    erros = {}

    nome          = (data.get("nome")  or "").strip()
    cpf           = (data.get("cpf")   or "").strip()
    senha         =  data.get("senha")
    consentimento =  data.get("consentimento")

    if not nome:
        erros["nome"] = "Campo obrigatório."
    if not cpf:
        erros["cpf"] = "Campo obrigatório."
    elif not validar_cpf_formato(cpf):
        erros["cpf"] = "Deve conter exatamente 11 dígitos numéricos."
    if senha is None:
        erros["senha"] = "Campo obrigatório."
    elif not validar_senha(str(senha)):
        erros["senha"] = "Deve conter exatamente 5 dígitos numéricos."
    if consentimento is None:
        erros["consentimento"] = "Campo obrigatório (LGPD: aceite de uso dos dados)."
    elif consentimento is not True:
        erros["consentimento"] = "O consentimento LGPD deve ser true para prosseguir."

    if erros:
        return erro_validacao(erros)

    senha_str = str(senha)
    conn = get_connection()
    try:
        existente = conn.execute("SELECT id FROM clientes WHERE cpf = ?", (cpf,)).fetchone()
        if existente:
            return erro("CPF já cadastrado.", "CPF_DUPLICADO", 409)

        cur = conn.execute(
            "INSERT INTO clientes (nome, cpf, senha, consentimento) VALUES (?, ?, ?, ?)",
            (nome, cpf, hash_senha(senha_str), 1),
        )
        conn.commit()
        cliente_id = cur.lastrowid
        registrar_log("CADASTRO_CLIENTE", "cliente", cliente_id, cliente_id=cliente_id, detalhes="consentimento=true")
    finally:
        conn.close()

    return jsonify({
        "message": "Cliente cadastrado com sucesso.",
        "cliente": {"id": cliente_id, "nome": nome, "cpf": cpf, "pontos": 0},
    }), 201

@clientes_bp.route("/login", methods=["POST"])
def login():
    """
    Autentica o cliente.
    Verifica CPF e senha e retorna um token JWT válido por 8 horas.
    
    tags:
      - Clientes

    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [cpf, senha]
          properties:
            cpf:
              type: string
              example: "12345678901"
            senha:
              type: string
              example: "12345"

    responses:
      200:
        description: Login realizado com sucesso
        examples:
          application/json: {"accessToken": "eyJhbGciOiJIUzI1NiJ9...", "tokenType": "Bearer", "expiresIn": 28800, "user": {"id": 1, "nome": "Maria Silva", "pontos": 0, "perfil": "CLIENTE"}}
      400:
        description: CPF ou senha não informados
      401:
        description: Credenciais inválidas
    """
    data  = request.get_json(silent=True) or {}
    cpf   = (data.get("cpf")   or "").strip()
    senha =  str(data.get("senha") or "")

    if not cpf or not senha:
        return erro("CPF e senha são obrigatórios.", "CREDENCIAIS_AUSENTES", 400)

    conn = get_connection()
    try:
        cliente = conn.execute("SELECT * FROM clientes WHERE cpf = ?", (cpf,)).fetchone()
    finally:
        conn.close()

    if not cliente or not verificar_senha(senha, cliente["senha"]):
        return erro("CPF ou senha inválidos.", "CREDENCIAIS_INVALIDAS", 401)

    token = gerar_token(cliente["id"], cliente["cpf"])
    registrar_log("LOGIN", "cliente", cliente["id"], cliente_id=cliente["id"])

    return jsonify({
        "accessToken": token,
        "tokenType":   "Bearer",
        "expiresIn":   28800,
        "user": {
            "id": cliente["id"], "nome": cliente["nome"],
            "pontos": cliente["pontos"], "perfil": "CLIENTE",
        },
    }), 200

@clientes_bp.route("/perfil", methods=["GET"])
@requer_autenticacao
def perfil(cliente_payload):
    """
    Consulta o perfil do cliente autenticado.
    Retorna os dados do cliente logado. O CPF não é exibido (minimização de dados — LGPD).
    
    tags:
      - Clientes

    security:
      - Bearer: []

    responses:
      200:
        description: Dados do cliente
        examples:
          application/json: {"cliente": {"id": 1, "nome": "Maria Silva", "pontos": 40, "criado_em": "2026-06-07 10:00:00"}}
      401:
        description: Token ausente, inválido ou expirado
      404:
        description: Cliente não encontrado
    """

    conn = get_connection()
    try:
        cliente = conn.execute(
            "SELECT id, nome, pontos, criado_em FROM clientes WHERE id = ?",
            (cliente_payload["sub"],),
        ).fetchone()
    finally:
        conn.close()

    if not cliente:
        return erro("Cliente não encontrado.", "NAO_ENCONTRADO", 404)

    return jsonify({"cliente": row_to_dict(cliente)}), 200

@clientes_bp.route("/fidelidade", methods=["GET"])
@requer_autenticacao
def fidelidade(cliente_payload):
    """
    Consulta saldo e histórico de fidelidade.
    Retorna o saldo de pontos acumulados e o histórico recente de pedidos do cliente.
    
    tags:
      - Fidelização

    security:
      - Bearer: []

    responses:
      200:
        description: Saldo e histórico de pontos
        examples:
          application/json: {"saldoPontos": 70, "historico": [{"id": 5, "total": 40.0, "status": "ENTREGUE", "pontos_obtidos": 40}]}
      401:
        description: Token ausente, inválido ou expirado
    """

    conn = get_connection()
    try:
        cliente = conn.execute(
            "SELECT id, nome, pontos FROM clientes WHERE id = ?", (cliente_payload["sub"],)
        ).fetchone()
        historico = conn.execute(
            """SELECT id, total, status, criado_em, CAST(total AS INTEGER) AS pontos_obtidos
               FROM pedidos WHERE cliente_id = ? ORDER BY criado_em DESC LIMIT 20""",
            (cliente_payload["sub"],),
        ).fetchall()
    finally:
        conn.close()

    if not cliente:
        return erro("Cliente não encontrado.", "NAO_ENCONTRADO", 404)

    return jsonify({
        "saldoPontos": cliente["pontos"],
        "historico":   [row_to_dict(h) for h in historico],
    }), 200

@clientes_bp.route("/ranking", methods=["GET"])
def ranking():
    """
    Ranking de fidelização.
    Retorna os 10 clientes com mais pontos acumulados. 
    O CPF do cliente não é exibido.

    tags:
      - Fidelização

    responses:
      200:
        description: Lista do ranking
        examples:
          application/json: {"ranking": [{"posicao": 1, "id": 3, "nome": "João Souza", "pontos": 150}]}
    """
    
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nome, pontos FROM clientes ORDER BY pontos DESC LIMIT 10"
        ).fetchall()
    finally:
        conn.close()

    return jsonify({
        "ranking": [{"posicao": i + 1, **row_to_dict(r)} for i, r in enumerate(rows)]
    }), 200