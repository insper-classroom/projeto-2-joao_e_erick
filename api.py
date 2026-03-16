import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from waitress import serve


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "imoveis.db"
DEFAULT_INIT_SQL_PATH = BASE_DIR / "db" / "init.sql"

db = SQLAlchemy()

CAMPO_OBRIGATORIOS = ("cidade", "logradouro")
CAMPOS_EDITAVEIS = (
	"logradouro",
	"tipo_logradouro",
	"bairro",
	"cidade",
	"cep",
	"tipo",
	"valor",
	"data_aquisicao",
)


class Imovel(db.Model):
	__tablename__ = "imoveis"

	id = db.Column(db.Integer, primary_key=True)
	logradouro = db.Column(db.String(255), nullable=False)
	tipo_logradouro = db.Column(db.String(100), nullable=True)
	bairro = db.Column(db.String(120), nullable=True)
	cidade = db.Column(db.String(120), nullable=False)
	cep = db.Column(db.String(20), nullable=True)
	tipo = db.Column(db.String(80), nullable=True)
	valor = db.Column(db.Float, nullable=True)
	data_aquisicao = db.Column(db.String(10), nullable=True)

	def to_dict(self):
		return {
			"id": self.id,
			"logradouro": self.logradouro,
			"tipo_logradouro": self.tipo_logradouro,
			"bairro": self.bairro,
			"cidade": self.cidade,
			"cep": self.cep,
			"tipo": self.tipo,
			"valor": self.valor,
			"data_aquisicao": self.data_aquisicao,
		}


def create_app(test_config=None):
	load_dotenv()

	app = Flask(__name__)
	app.config.from_mapping(
		SQLALCHEMY_DATABASE_URI=_obter_database_uri(),
		SQLALCHEMY_TRACK_MODIFICATIONS=False,
		JSON_SORT_KEYS=False,
		INIT_SQL_PATH=str(DEFAULT_INIT_SQL_PATH),
	)

	if test_config:
		app.config.update(test_config)

	engine_options = _obter_engine_options(app.config["SQLALCHEMY_DATABASE_URI"])
	if engine_options:
		config_engine_options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}).copy()
		config_engine_options.update(engine_options)
		app.config["SQLALCHEMY_ENGINE_OPTIONS"] = config_engine_options

	db.init_app(app)
	_registrar_rotas(app)
	_registrar_comandos(app)
	return app


def _obter_database_uri():
	database_uri = os.getenv("DATABASE_URL")

	if not database_uri:
		return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

	if database_uri.startswith("mysql://"):
		return database_uri.replace("mysql://", "mysql+pymysql://", 1)

	return database_uri


def _obter_engine_options(database_uri):
	if database_uri.startswith("sqlite"):
		return {}

	engine_options = {"pool_pre_ping": True}
	mysql_ssl_ca = os.getenv("MYSQL_SSL_CA")

	if mysql_ssl_ca:
		engine_options["connect_args"] = {"ssl": {"ca": mysql_ssl_ca}}

	return engine_options


def _registrar_rotas(app):
	@app.get("/imoveis")
	def listar_imoveis():
		consulta = Imovel.query.order_by(Imovel.id)
		tipo = request.args.get("tipo")
		cidade = request.args.get("cidade")

		if tipo:
			consulta = consulta.filter(func.lower(Imovel.tipo) == tipo.strip().lower())
		if cidade:
			consulta = consulta.filter(func.lower(Imovel.cidade) == cidade.strip().lower())

		return jsonify([imovel.to_dict() for imovel in consulta.all()])

	@app.get("/imoveis/<int:imovel_id>")
	def buscar_imovel(imovel_id):
		imovel = db.session.get(Imovel, imovel_id)
		if imovel is None:
			return _erro("Imovel nao encontrado", 404)
		return jsonify(imovel.to_dict())

	@app.post("/imoveis")
	def criar_imovel():
		payload, erro = _validar_payload()
		if erro:
			return erro

		campos_ausentes = _campos_obrigatorios_ausentes(payload)
		if campos_ausentes:
			return _erro(
				f"Campos obrigatorios ausentes: {', '.join(campos_ausentes)}",
				400,
			)

		imovel = Imovel(**_filtrar_campos(payload))
		db.session.add(imovel)
		db.session.commit()

		resposta = jsonify(imovel.to_dict())
		resposta.status_code = 201
		resposta.headers["Location"] = url_for("buscar_imovel", imovel_id=imovel.id)
		return resposta

	@app.put("/imoveis/<int:imovel_id>")
	@app.patch("/imoveis/<int:imovel_id>")
	def atualizar_imovel(imovel_id):
		imovel = db.session.get(Imovel, imovel_id)
		if imovel is None:
			return _erro("Imovel nao encontrado", 404)

		payload, erro = _validar_payload()
		if erro:
			return erro

		for campo, valor in _filtrar_campos(payload).items():
			setattr(imovel, campo, valor)

		campos_invalidos = [
			campo for campo in CAMPO_OBRIGATORIOS if not getattr(imovel, campo)
		]
		if campos_invalidos:
			return _erro(
				f"Campos obrigatorios ausentes: {', '.join(sorted(campos_invalidos))}",
				400,
			)

		db.session.commit()
		return jsonify(imovel.to_dict())

	@app.delete("/imoveis/<int:imovel_id>")
	def remover_imovel(imovel_id):
		imovel = db.session.get(Imovel, imovel_id)
		if imovel is None:
			return _erro("Imovel nao encontrado", 404)

		db.session.delete(imovel)
		db.session.commit()
		return ("", 204)

	@app.get("/imoveis/tipo/<string:tipo>")
	def listar_imoveis_por_tipo(tipo):
		consulta = (
			Imovel.query.filter(func.lower(Imovel.tipo) == tipo.strip().lower())
			.order_by(Imovel.id)
			.all()
		)
		return jsonify([imovel.to_dict() for imovel in consulta])

	@app.get("/imoveis/cidade/<path:cidade>")
	def listar_imoveis_por_cidade(cidade):
		consulta = (
			Imovel.query.filter(func.lower(Imovel.cidade) == cidade.strip().lower())
			.order_by(Imovel.id)
			.all()
		)
		return jsonify([imovel.to_dict() for imovel in consulta])


def _registrar_comandos(app):
	@app.cli.command("init-db")
	@click.option("--reset", is_flag=True, help="Recria a tabela antes de carregar o script.")
	def init_db_command(reset):
		inicializar_banco(app.config["INIT_SQL_PATH"], reset=reset)
		print("Banco inicializado com sucesso.")


def _validar_payload():
	payload = request.get_json(silent=True)
	if payload is None or not isinstance(payload, dict):
		return None, _erro("Corpo da requisicao deve ser um JSON valido", 400)
	return payload, None


def _filtrar_campos(payload):
	return {campo: payload[campo] for campo in CAMPOS_EDITAVEIS if campo in payload}


def _campos_obrigatorios_ausentes(payload):
	return sorted(campo for campo in CAMPO_OBRIGATORIOS if not payload.get(campo))


def _erro(mensagem, status_code):
	resposta = jsonify({"erro": mensagem})
	resposta.status_code = status_code
	return resposta


def inicializar_banco(script_path=None, reset=False):
	caminho_script = Path(script_path or DEFAULT_INIT_SQL_PATH)
	conteudo = caminho_script.read_text(encoding="utf-8")
	comandos = []
	buffer = []

	for linha in conteudo.splitlines():
		linha_limpa = linha.strip()
		if not linha_limpa or linha_limpa.startswith("--"):
			continue

		buffer.append(linha)
		if linha_limpa.endswith(";"):
			comandos.append("\n".join(buffer).rstrip().rstrip(";"))
			buffer = []

	if buffer:
		comandos.append("\n".join(buffer).rstrip().rstrip(";"))

	with db.engine.begin() as conexao:
		if reset:
			conexao.exec_driver_sql("DROP TABLE IF EXISTS imoveis")
		for comando in comandos:
			conexao.exec_driver_sql(comando)


app = create_app()


if __name__ == "__main__":
	with app.app_context():
		db.create_all()

	porta = int(os.getenv("PORT", "5000"))
	serve(app, host="0.0.0.0", port=porta)
