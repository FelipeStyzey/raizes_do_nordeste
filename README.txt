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
-Autenticação no POSTMAN: 
*Auth type: JWT Bearer (POST/clientes/login)
Copia o token e com o botão direito 'Set a variable' cria a variável token
*Auth type: Bearer Token (GET/clientes/perfil)
Troca o token gigantesco por {{token}} que será refenciado o token copiado no POST/clientes/login

4 - Documentação da API:
Cada endpoint pode ser consultado com a API rodando com '/apidocs' .

5- Fluxo do Postman:

1 - POST/clientes/cadastro  - Cria conta
2 - POST/clientes/login     - Obter token JWT
3 - GET/cardapio?unidade=MATRIZ - Ver cardápio disponível
4 - POST/pedidos            - Criar pedido (usar token)
5 - POST/pagamentos         - Pagar pedido (usar token)
6 - GET/clientes/perfil     - Ver pontos acumulados
7 - GET/clientes/ranking    - Ver ranking de fidelidade

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