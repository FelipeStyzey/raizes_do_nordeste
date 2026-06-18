from flask import Flask, jsonify
from app.database import init_db
from app.routes.clientes import clientes_bp
from app.routes.pedidos import pedidos_bp
from app.routes.estoque import estoque_bp
from app.routes.cardapio import cardapio_bp
from app.routes.pagamentos import pagamentos_bp

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