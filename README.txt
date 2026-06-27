    Trabalho: Restaurante Raízes do Nordeste 

Centralizar em uma API todas as formas de atender os pedidos no Raízes do Nordeste, que são: 
App; Totem; Balcão; Tele-entrega; Web.

Além dos pedidos, criar cadastros de clientes e programas de fidelização (respeitando a LGPD), 
gerenciador de estoque das unidades, cardápio e integração com pagamentos.


    *Linguagem utilizada:
    Python 3.11.3
    Flask 3.1.3
    Banco: SQLlite

    *Link do projeto no github: https://github.com/FelipeStyzey/raizes_do_nordeste


    Como executar o projeto:

1.1- Após baixar o projeto, executar no terminal da IDE a criação do .env :
python -m venv .venv

1.2 - Se quiser ver se a pasta .venv foi criada corretamente:
Get-ChildItem .\.venv\Scripts\

1.3 - Ative o ambiente:
.\.venv\Scripts\Activate.ps1

1.4 - Instalar as dependências:
pip install -r requirements.txt

2 - Executar o run.py
No terminal: python run.py ou selecionando o arquivo run.py e executando.

2.1 - O banco SQlite é criado automaticamente em instance/raizes.db na primeira execução do código.

3 - Abre o POSTMAN:

-Base URL: http://localhost:5000
-Formato: JSON

*Auth type: Bearer Token (GET/clientes/perfil)
O token é obtido em `POST /clientes/login` e tem validade de **8 horas** (28800 segundos).
Troca o token gigantesco por {{token}} que será refenciado o token copiado no POST/clientes/login

4 - Documentação da API:
Cada endpoint pode ser consultado com a API rodando com '/apidocs' .

5- Fluxo do Postman:

5.1 - POST/clientes/cadastro  - Cria conta
- No body, seleciona raw e o formato JSON:
{
    "nome" : "Felipe",
    "cpf" : "12345678912",
    "senha": "12345",
    "consentimento": true
}

5.2 - POST/clientes/login     - Obter token JWT
- No body, seleciona raw e o formato JSON:
{
    "cpf": "12345678912",
    "senha": "12345"
}

Gerará um token, basta selecionar o token e com o botão direito 'Set a variable' cria a variável token.
Utiliza a variável {{token}} como autenticação tipo 'Bearer Token' em todas as rotas necessárias.

5.3 - GET/clientes/perfil
5.3 - GET/cardapio?unidade=MATRIZ - Ver cardápio disponível
5.4 - POST/pedidos            - Criar pedido (usar token)
5.5 - POST/pagamentos         - Pagar pedido (usar token)
5.6 - GET/clientes/perfil     - Ver pontos acumulados
5.7 - GET/clientes/ranking    - Ver ranking de fidelidade

6 - Códigos de status utilizados:
    Status - Significado

    200 -   OK
    201 -   Criado com sucesso
    400 -   Requisição inválida
    401 -   Não autenticado
    402 -   Pagamento recusado
    404 -   Recurso não encontrado
    405 -   Método não permitido
    409 -   Conflito
    422 -   Erro de validação de campos

7 - Tabela-Resumo de Todos os Endpoints

| # | Recurso | Método | Rota | Auth |

| 1 | Clientes | POST | /clientes/cadastro | Pública |
| 2 | Clientes | POST | /clientes/login | Pública |
| 3 | Clientes | GET | /clientes/perfil | JWT |
| 4 | Cardápio | GET | /cardapio | Pública |
| 5 | Cardápio | GET | /cardapio/{id} | Pública |
| 6 | Cardápio | POST | /cardapio | JWT |
| 7 | Cardápio | PUT | /cardapio/{id} | JWT |
| 8 | Cardápio | DELETE | /cardapio/{id} | JWT |
| 9 | Estoque | GET | /estoque | JWT |
| 10 | Estoque | POST | /estoque | JWT |
| 11 | Estoque | POST | /estoque/transferir | JWT |
| 12 | Estoque | PUT | /estoque/{id} | JWT |
| 13 | Pedidos | POST | /pedidos | JWT |
| 14 | Pedidos | GET | /pedidos (com filtro canalPedido) | JWT |
| 15 | Pedidos | GET | /pedidos/{id} | JWT |
| 16 | Pedidos | PATCH | /pedidos/{id}/status | JWT |
| 17 | Pagamentos | POST | /pagamentos | JWT |
| 18 | Pagamentos | GET | /pagamentos/{pedidoId} | JWT |
| 19 | Fidelidade | GET | /clientes/fidelidade | JWT |
| 20 | Fidelidade | GET | /clientes/ranking | Pública |
| 21 | Auditoria | GET | /auditoria | JWT |