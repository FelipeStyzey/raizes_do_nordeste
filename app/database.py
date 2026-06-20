import os
import sqlite3

DB_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "instance", "raizes.db")

def get_connection():
    conn = sqlite3.connect(DB_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursos()

# Criação da tabela Clientes:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id          INTERGER    PRIMARY KEY AUTOINCREMENT,
            nome        TEXT        NOT NULL,
            cpf         TEXT        NOT NULL UNIQUE,
            senha       TEXT        NOT NULL,
            pontos      INTEGER    NOT NULL DEFAULT 0,
            consentimento   INTEGER     NOT NULL DEFAULT 0,
            criado_em   TEXT      NOT NULL DEFAULT (datetime('now'))
        )
    """)

# Criação da tabela Pedidos:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id              INTEGER     PRIMARY KEY AUTOINCREMENT,
            canal_pedido    TEXT        NOT NULL,
            cliente_id      INTERGER    NOT NULL,
            unidade         TEXT        NOT NULL DEFAULT 'MATRIZ',
            status          TEXT        NOT NULL DEFAULT 'PENDENTE',
            total           REAL        NOT NULL DEFAULT 0.0,
            criado_em       TEXT        NOT NULL DEFAULT(datetime('now')),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            pedido_id   INTEGER   NOT NULL,
            prato_id    INTEGER   NOT NULL,
            quantidade  INTEGER   NOT NULL DEFAULT 1,
            preco_unit  REAL      NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
            FOREIGN KEY (prato_id) REFERENCES cardapio(id)        
        )
    """)

# Criação da tabela Estoque:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (            
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            unidade     TEXT        NOT NULL,
            insumo      TEXT        NOT NULL,
            quantidade  INTEGER     NOT NULL DEFAULT 0,                
            UNIQUE(unidade,insumo)
    )                
    """)

# Criação da tabela Cardápio:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cardapio (
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            unidade     TEXT        NOT NULL,
            nome        TEXT        NOT NULL,
            descricao   TEXT,
            preco       REAL        NOT NULL,
            ativo       INTEGER     NOT NULL DEFAULT 1,
            UNIQUE(unidade,nome)       
        )
    """)

# Criação da tabela Pagamentos:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            pedido_id   INTEGER     NOT NULL UNIQUE,
            metodo      TEXT        NOT NULL,
            status      TEXT        NOT NULL,
            processado_em   TEXT    NOT NULL DEFAULT(datetime('now')),
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        )
    """)

# Criação da tabela Auditoria:
    cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id      INTEGER     PRIMARY KEY AUTOINCREMENT,
                acao    TEXT        NOT NULL,
                entidade    TEXT    NOT NULL,
                entidade_id INTEGER NOT NULL,
                cliente_id  INTEGER NOT NULL,
                detalhes    TEXT,
                criado_em   TEXT    NOT NULL DEFAULT(datetime('now')),
                )
            """)

# Seed inicial:
    _seed(cur)

    conn.commit()
    conn.close()
    print(f"[DB] Banco iniciado em: {DB_PATH}")

def _seed(cur):
    """ Insere dados iniciais caso as tabelas estejam vazias."""
    
#Populando o banco de dados:

    # Estoque:
    estoque_seed = [
        ("MATRIZ", "Produto 1", 200),   ("MATRIZ", "Produto 2", 180),
        ("MATRIZ", "Produto 3", 150),   ("MATRIZ", "Produto 4", 120),
        ("FILIAL_1", "Produto 1", 50),  ("FILIAL_1", "Produto 2", 40),
        ("FILIAL_1", "Produto 3",30),
        ("FILIAL_2", "Produto 1", 50),  ("FILIAL_2", "Produto 2", 40),
        ("FILIAL_2", "Produto 3", 30),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO estoque (unidade, insumo, quantidade) VALUES (?,?,?)",
        estoque_seed,
    )

    # Cardápio:
    cardapio_seed = [
        ("MATRIZ", "Prato 1", "Carne de sol com macaxeira", 20.00),
        ("MATRIZ", "Prato 2", "Especialidade da casa", 30.00),
        ("MATRIZ", "Prato 3", "Frutos do mar", 50.00),
        ("FILIAL_1", "Prato 1", "Carne de sol com macaxeira", 20.00),
        ("FILIAL_1", "Prato 2", "Especialidade da casa", 30.00),
        ("FILIAL_2", "Prato 1", "Carne de sol com macaxeira", 20.00),
        ("FILIAL_2", "Prato 2", "Especialidade da casa", 30.00),
        ("FILIAL_2", "Prato 3", "Frutos do mar", 50.00),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO cardapio (unidade, nome , descricao, preco) VALUES (?,?,?,?)",
        cardapio_seed,
    )