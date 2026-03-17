# API Imobiliaria

API RESTful em Flask para cadastro e consulta de imoveis.

## API publica (EC2 AWS)

Base da API: http://3.239.5.102/imoveis

## Rotas

- `GET /imoveis`: lista todos os imoveis.
- `GET /imoveis/<id>`: busca um imovel pelo id.
- `POST /imoveis`: cria um novo imovel.
- `PUT /imoveis/<id>`: atualiza um imovel existente.
- `PATCH /imoveis/<id>`: atualiza parcialmente um imovel existente.
- `DELETE /imoveis/<id>`: remove um imovel.
- `GET /imoveis/tipo/<tipo>`: filtra por tipo.
- `GET /imoveis/cidade/<cidade>`: filtra por cidade.
- `GET /imoveis?tipo=apartamento`: filtro alternativo por query string.
- `GET /imoveis?cidade=Sao Paulo`: filtro alternativo por query string.

## Rodando localmente

1. Crie e ative a virtualenv.
2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Crie o arquivo `.env` na raiz do projeto com as credenciais do MySQL.

4. Rode os testes:

```bash
pytest -q
```

5. Inicie a API:

```bash
python api.py
```

## Banco MySQL no Aiven

1. Baixe o certificado CA do servico MySQL no Aiven.
2. Crie o arquivo `.env` na raiz do projeto.
3. Preencha as variaveis de conexao com o banco.
4. Ajuste `ssl_ca` com o caminho do certificado baixado.

Exemplo:

```env
host=mysql-seu-projeto.aivencloud.com
port=12345
user=avnadmin
password=SUA_SENHA
database=defaultdb
ssl_ca=ca.pem
PORT=5000
```

Para criar a tabela e carregar os dados do script fornecido:

```bash
flask --app api init-db --reset
```

O comando usa o arquivo `db/init.sql`.

## TDD

O fluxo esperado do projeto e:

1. Escrever ou ajustar testes em `tests/test_api.py`.
2. Rodar os testes e observar a falha.
3. Implementar o minimo necessario em `api.py`.
4. Rodar os testes novamente e refatorar mantendo tudo verde.

## Deploy no EC2

Passo a passo sugerido:

1. Crie uma instancia EC2 Ubuntu.
2. Libere a porta 5000 no Security Group, ou use Nginx na porta 80 como proxy.
3. Instale Python e git no servidor.
4. Clone o repositorio.
5. Crie a virtualenv e instale `requirements.txt`.
6. Crie o arquivo `.env` na raiz do projeto.
7. Copie o certificado `ca.pem` para o servidor.
8. Execute `flask --app api init-db --reset` para preparar o banco.
9. Suba a API com `python api.py`.
10. Para manter o processo ativo, configure um servico `systemd`.

Exemplo de `ExecStart` em um servico `systemd`:

```ini
ExecStart=/home/ubuntu/projeto/.venv/bin/python /home/ubuntu/projeto/api.py
```

