"""

Módulo de auditoria/logs de ações sensíveis (rastreabilidade LGPD).

"""
from app.database import get_connection
from datetime import datetime, timezone


def registrar_log(acao: str, entidade: str, entidade_id: int,
                  cliente_id: int = None, detalhes: str = None):
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO audit_log (acao, entidade, entidade_id, cliente_id, detalhes, criado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (acao, entidade, entidade_id, cliente_id, detalhes,
             datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT ERROR] {e}")