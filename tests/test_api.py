import pytest

from api import Imovel, create_app, db


def _novo_imovel(**overrides):
	dados = {
		"logradouro": "Avenida Paulista",
		"tipo_logradouro": "Avenida",
		"bairro": "Bela Vista",
		"cidade": "Sao Paulo",
		"cep": "01311-000",
		"tipo": "apartamento",
		"valor": 950000.0,
		"data_aquisicao": "2024-01-10",
	}
	dados.update(overrides)
	return Imovel(**dados)


@pytest.fixture
def app():
	app = create_app(
		{
			"TESTING": True,
			"SQLALCHEMY_DATABASE_URI": "sqlite://",
			"SQLALCHEMY_TRACK_MODIFICATIONS": False,
		}
	)

	with app.app_context():
		db.drop_all()
		db.create_all()
		db.session.add_all(
			[
				_novo_imovel(),
				_novo_imovel(
					logradouro="Rua das Flores",
					tipo_logradouro="Rua",
					bairro="Centro",
					cidade="Campinas",
					cep="13010-000",
					tipo="casa",
					valor=780000.0,
					data_aquisicao="2023-07-22",
				),
				_novo_imovel(
					logradouro="Alameda Santos",
					tipo_logradouro="Alameda",
					bairro="Jardins",
					cidade="Sao Paulo",
					cep="01419-002",
					tipo="apartamento",
					valor=1100000.0,
					data_aquisicao="2022-12-01",
				),
			]
		)
		db.session.commit()

		yield app

		db.session.remove()
		db.drop_all()


@pytest.fixture
def client(app):
	return app.test_client()


def test_listar_todos_os_imoveis(client):
	resposta = client.get("/imoveis")

	assert resposta.status_code == 200
	dados = resposta.get_json()
	assert len(dados) == 3
	assert dados[0].keys() == {
		"id",
		"logradouro",
		"tipo_logradouro",
		"bairro",
		"cidade",
		"cep",
		"tipo",
		"valor",
		"data_aquisicao",
	}


def test_busca_imovel_por_id(client):
	resposta = client.get("/imoveis/1")

	assert resposta.status_code == 200
	dados = resposta.get_json()
	assert dados["id"] == 1
	assert dados["cidade"] == "Sao Paulo"
	assert dados["tipo"] == "apartamento"


def test_retorna_404_quando_imovel_nao_existe(client):
	resposta = client.get("/imoveis/999")

	assert resposta.status_code == 404
	assert resposta.get_json() == {"erro": "Imovel nao encontrado"}


def test_criar_um_novo_imovel(client):
	payload = {
		"logradouro": "Rua Oscar Freire",
		"tipo_logradouro": "Rua",
		"bairro": "Pinheiros",
		"cidade": "Sao Paulo",
		"cep": "05409-010",
		"tipo": "casa",
		"valor": 1250000.0,
		"data_aquisicao": "2025-02-15",
	}

	resposta = client.post("/imoveis", json=payload)

	assert resposta.status_code == 201
	dados = resposta.get_json()
	assert dados["id"] == 4
	assert dados["logradouro"] == payload["logradouro"]
	assert resposta.headers["Location"] == "/imoveis/4"


def test_validar_campos_obrigatorios_na_criacao(client):
	resposta = client.post("/imoveis", json={"bairro": "Centro"})

	assert resposta.status_code == 400
	assert resposta.get_json() == {
		"erro": "Campos obrigatorios ausentes: cidade, logradouro"
	}


def test_atualizar_um_imovel_existente(client):
	resposta = client.put(
		"/imoveis/2",
		json={
			"cidade": "Valinhos",
			"tipo": "casa",
			"valor": 820000.0,
		},
	)

	assert resposta.status_code == 200
	dados = resposta.get_json()
	assert dados["id"] == 2
	assert dados["cidade"] == "Valinhos"
	assert dados["valor"] == 820000.0
	assert dados["logradouro"] == "Rua das Flores"


def test_remover_um_imovel_existente(client):
	resposta = client.delete("/imoveis/3")

	assert resposta.status_code == 204
	assert client.get("/imoveis/3").status_code == 404
	assert len(client.get("/imoveis").get_json()) == 2


def test_listar_imoveis_por_tipo(client):
	resposta = client.get("/imoveis/tipo/APARTAMENTO")

	assert resposta.status_code == 200
	dados = resposta.get_json()
	assert len(dados) == 2
	assert {item["logradouro"] for item in dados} == {
		"Avenida Paulista",
		"Alameda Santos",
	}


def test_listar_imoveis_por_cidade(client):
	resposta = client.get("/imoveis/cidade/sao paulo")

	assert resposta.status_code == 200
	dados = resposta.get_json()
	assert len(dados) == 2
	assert {item["tipo"] for item in dados} == {"apartamento"}
