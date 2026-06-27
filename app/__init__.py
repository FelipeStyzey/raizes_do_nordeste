from flask import Flask, jsonify
from flasgger import Swagger
from app.database import init_db
from app.routes.clientes import clientes_bp
from app.routes.pedidos import pedidos_bp
from app.routes.estoque import estoque_bp
from app.routes.cardapio import cardapio_bp
from app.routes.pagamentos import pagamentos_bp
from app.routes.audit import audit_bp
from app.utils.helpers import now_iso


#Configuração do Swagger(docmentação):
SWAGGER_CONFIG = {
        "headers":[],
        "specs":[{
            "endpoint": "apispe",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    }

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Raízes do Nordeste — API",
        "description": (
            "API REST da rede de restaurantes Raízes do Nordeste. "
            "Centraliza pedidos multicanal (APP, TOTEM, BALCAO, WEB, PICKUP, TELE_ENTREGA), "
            "cardápio e estoque por unidade, fidelização de clientes e pagamento mock.\n\n"
            "Para testar endpoints protegidos: faça login em **POST /clientes/login**, copie o "
            "`accessToken` retornado, clique em **Authorize** no topo desta página e cole no "
            "formato `Bearer <token>`."
        ),
        "version": "1.0.0",
        "contact": {"name": "Projeto Multidisciplinar — Trilha Back-End — UNINTER 2026"},
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Token JWT no formato: Bearer <seu_token>",
        }
    },
    "tags": [
        {"name": "Clientes",      "description": "Cadastro, autenticação e perfil"},
        {"name": "Fidelização",   "description": "Pontos e ranking de clientes"},
        {"name": "Pedidos",       "description": "Criação, consulta e status de pedidos multicanal"},
        {"name": "Cardápio",      "description": "Pratos por unidade"},
        {"name": "Estoque",       "description": "Controle e transferência de insumos por unidade"},
        {"name": "Pagamentos",    "description": "Integração mock de pagamento"},
        {"name": "Auditoria",     "description": "Logs e rastreabilidade de ações sensíveis"},
    ],
}


def create_app():
    app = Flask(__name__, instance_relative_config=True)

# Configuração da senha:
    app.config["SECRET_KEY"] = "raizes_nordeste_2026"
    app.config["JSON_SORT_KEYS"] = False

# Inicia o banco:
    init_db()

# Registro de blueprints:
    app.register_blueprint(clientes_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(cardapio_bp)
    app.register_blueprint(pagamentos_bp)
    app.register_blueprint(audit_bp)    

# Rota de teste:
    @app.route("/", methods=["GET"])
    def teste():
        return jsonify({ 
            "status": "online",
            "app": "Raízes do Nordeste",
            "versao": "1.0.0",
            "endpoints": [
                "POST /clientes/cadastro",
                "POST /clientes/login",
                "GET /clientes/perfil",
                "GET /clientes/ranking",
                "POST /pedidos",
                "GET /pedidos?canalPedido=&unidade=&status=",
                "GET /pedidos/<id>",
                "GET /cardapio/<id>",
                "GET /cardapio?unidade=&ativo=",
                "POST /cardapio",
                "PUT /cardapio/<id>",
                "DELETE /cardapio/<id>",
                "GET /estoque?unidade=&insumo=",
                "POST /estoque",
                "PUT /estoque/<id>",
                "POST /estoque/transferir",
                "POST /pagamentos",
                "GET /pagamentos/<pedidoId>",
            ],
        })

# Erro 404:
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"Erro": "Rota não encontrada.","codigo": "ROTA_NAO_ENCONTRADA"}), 404

# Erro 405:
    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"Erro": "Método HTTP não permitido.","codigo": "METODO_NAO_PERMITIDO"}), 405

    return app