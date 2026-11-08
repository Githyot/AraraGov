"""Modelo de dados. Funciona em SQLite (desenvolvimento) e Postgres (produção)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Iterator, Optional

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import database_url

CASAS = ("camara", "senado")


class Base(DeclarativeBase):
    pass


class Politico(Base):
    """Parlamentar. `codigo` é o id oficial da casa (Câmara: id do deputado;
    Senado: CodigoParlamentar)."""

    __tablename__ = "politico"
    __table_args__ = (UniqueConstraint("casa", "codigo", name="uq_politico_casa_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    cargo: Mapped[str] = mapped_column(String(30))
    codigo: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(200))
    nome_civil: Mapped[Optional[str]] = mapped_column(String(200))
    partido: Mapped[Optional[str]] = mapped_column(String(30))
    uf: Mapped[Optional[str]] = mapped_column(String(2))
    sexo: Mapped[Optional[str]] = mapped_column(String(20))
    url_foto: Mapped[Optional[str]] = mapped_column(String(400))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    em_exercicio: Mapped[Optional[bool]]
    legislatura: Mapped[Optional[int]] = mapped_column(Integer)
    # De onde veio o cadastro quando não é a própria casa (ex.: "tse").
    fonte: Mapped[Optional[str]] = mapped_column(String(20))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Votacao(Base):
    """Votação nominal em plenário ou comissão. `id` = "{casa}:{codigo}"."""

    __tablename__ = "votacao"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo: Mapped[str] = mapped_column(String(60))
    data: Mapped[Optional[datetime]] = mapped_column(DateTime)
    orgao: Mapped[Optional[str]] = mapped_column(String(40))
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    proposicao: Mapped[Optional[str]] = mapped_column(String(80))
    ementa: Mapped[Optional[str]] = mapped_column(Text)
    resultado: Mapped[Optional[str]] = mapped_column(String(200))
    link: Mapped[Optional[str]] = mapped_column(String(400))
    # Orientação de cada partido/bloco, ex.: {"PT": "Sim", "PL": "Não"}.
    # Base para classificar a votação no espectro na etapa de análises.
    orientacoes: Mapped[Optional[dict]] = mapped_column(JSON)


class Voto(Base):
    __tablename__ = "voto"
    __table_args__ = (
        UniqueConstraint("votacao_id", "codigo_politico", name="uq_voto_votacao_politico"),
        Index("ix_voto_politico", "casa", "codigo_politico"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    votacao_id: Mapped[str] = mapped_column(ForeignKey("votacao.id", ondelete="CASCADE"))
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    nome_politico: Mapped[Optional[str]] = mapped_column(String(200))
    # Partido no dia da votação (pode ser diferente do partido atual).
    partido: Mapped[Optional[str]] = mapped_column(String(30))
    uf: Mapped[Optional[str]] = mapped_column(String(2))
    voto_original: Mapped[Optional[str]] = mapped_column(String(60))
    # sim | nao | abstencao | obstrucao | ausente | presidente | outro
    voto: Mapped[str] = mapped_column(String(20))


class Despesa(Base):
    """Gasto da cota parlamentar (CEAP na Câmara, CEAPS no Senado)."""

    __tablename__ = "despesa"
    __table_args__ = (
        UniqueConstraint("casa", "chave_fonte", name="uq_despesa_casa_chave"),
        Index("ix_despesa_politico", "casa", "codigo_politico", "ano", "mes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    chave_fonte: Mapped[str] = mapped_column(String(120))
    # Nulo para gastos de lideranças partidárias, que não têm parlamentar.
    codigo_politico: Mapped[Optional[int]] = mapped_column(Integer)
    nome_politico: Mapped[Optional[str]] = mapped_column(String(200))
    ano: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    categoria: Mapped[Optional[str]] = mapped_column(String(400))
    fornecedor: Mapped[Optional[str]] = mapped_column(String(400))
    cnpj_cpf: Mapped[Optional[str]] = mapped_column(String(30))
    data_documento: Mapped[Optional[date]] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    url_documento: Mapped[Optional[str]] = mapped_column(String(400))


class Assessor(Base):
    """Pessoa lotada no gabinete do parlamentar (secretário parlamentar na
    Câmara, comissionado no gabinete no Senado). Lista substituída a cada coleta."""

    __tablename__ = "assessor"
    __table_args__ = (Index("ix_assessor_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[Optional[int]] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[Optional[str]] = mapped_column(String(200))
    funcao: Mapped[Optional[str]] = mapped_column(String(200))
    lotacao: Mapped[Optional[str]] = mapped_column(String(300))
    desde: Mapped[Optional[date]] = mapped_column(Date)
    # Remuneração bruta do mês de referência, quando a casa publica (Senado).
    remuneracao: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    remuneracao_ref: Mapped[Optional[str]] = mapped_column(String(7))  # "2026-09"


class AssessorAnterior(Base):
    """Quem já trabalhou no gabinete. As fontes só listam a equipe de hoje, então
    o AraraGov guarda a lista de cada coleta (historico.py) e, quando alguém some
    da lista, registra a saída na data da coleta em que deixou de aparecer."""

    __tablename__ = "assessor_anterior"
    __table_args__ = (Index("ix_assessor_anterior_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[Optional[str]] = mapped_column(String(200))
    funcao: Mapped[Optional[str]] = mapped_column(String(200))
    desde: Mapped[Optional[date]] = mapped_column(Date)
    # Nulo: estava na equipe na coleta anterior (ainda não se sabe se saiu).
    ate: Mapped[Optional[date]] = mapped_column(Date)


class Emenda(Base):
    """Emenda parlamentar ao orçamento federal (Portal da Transparência/CGU).
    Valores acumulados desde o ano da emenda; `codigo_politico` fica nulo
    para emendas de bancada, comissão e relator, que não têm um autor só."""

    __tablename__ = "emenda"
    __table_args__ = (Index("ix_emenda_politico", "casa", "codigo_politico", "ano"),)

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    ano: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[Optional[str]] = mapped_column(String(120))
    autor: Mapped[Optional[str]] = mapped_column(String(200))
    casa: Mapped[Optional[str]] = mapped_column(String(10))
    codigo_politico: Mapped[Optional[int]] = mapped_column(Integer)
    localidade: Mapped[Optional[str]] = mapped_column(String(200))
    uf: Mapped[Optional[str]] = mapped_column(String(40))
    funcao: Mapped[Optional[str]] = mapped_column(String(120))
    acao: Mapped[Optional[str]] = mapped_column(String(400))
    empenhado: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    pago: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class Favorecido(Base):
    """Quem recebeu dinheiro das emendas de cada parlamentar, somado no ano."""

    __tablename__ = "favorecido"
    __table_args__ = (Index("ix_favorecido_politico", "casa", "codigo_politico", "ano"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    ano: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(300))
    documento: Mapped[Optional[str]] = mapped_column(String(20))
    tipo: Mapped[Optional[str]] = mapped_column(String(60))
    municipio: Mapped[Optional[str]] = mapped_column(String(200))
    uf: Mapped[Optional[str]] = mapped_column(String(2))
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class Beneficio(Base):
    """Benefício além do salário (auxílio-moradia, imóvel funcional...).
    Lista substituída a cada coleta, como um retrato do mês."""

    __tablename__ = "beneficio"
    __table_args__ = (Index("ix_beneficio_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(40))
    descricao: Mapped[str] = mapped_column(String(300))
    valor_mensal: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    referencia: Mapped[Optional[str]] = mapped_column(String(40))
    fonte: Mapped[Optional[str]] = mapped_column(String(400))
    # Câmara: o benefício é informado por ano, com o total recebido no ano.
    ano: Mapped[Optional[int]] = mapped_column(Integer)
    valor_ano: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))


class RecursoMensal(Base):
    """Valor mensal publicado pela casa: salário bruto pago ao parlamentar
    ("salario") e verba de gabinete gasta com secretários ("verba_gabinete")."""

    __tablename__ = "recurso_mensal"
    __table_args__ = (Index("ix_recurso_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(20))
    ano: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    disponivel: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))


class Atividade(Base):
    """Atuação parlamentar publicada pela Câmara: propostas de autoria,
    relatorias, presença no Plenário, discursos, comissões e frentes.
    `dados` guarda o bloco já no formato da API; `ano` é nulo para o que vale
    pela legislatura (comissões e frentes)."""

    __tablename__ = "atividade"
    __table_args__ = (Index("ix_atividade_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    ano: Mapped[Optional[int]] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(30))
    dados: Mapped[dict] = mapped_column(JSON)


class Ocorrencia(Base):
    """Registro oficial ligado ao político: situação de candidatura no TSE,
    sanção no CEIS/CNEP (CGU), inabilitação no TCU, ou o link das certidões
    entregues ao TSE (tipo "certidoes"). Recriado a cada coleta. Nenhum CPF é
    gravado: ele só serve, em memória, para conferir que não é um homônimo."""

    __tablename__ = "ocorrencia"
    __table_args__ = (Index("ix_ocorrencia_politico", "casa", "codigo_politico"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    codigo_politico: Mapped[int] = mapped_column(Integer)
    fonte: Mapped[str] = mapped_column(String(10))  # tse | cgu | tcu
    tipo: Mapped[str] = mapped_column(String(30))
    titulo: Mapped[str] = mapped_column(String(300))
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    situacao: Mapped[str] = mapped_column(String(30))
    data: Mapped[Optional[date]] = mapped_column(Date)
    orgao: Mapped[Optional[str]] = mapped_column(String(300))
    processo: Mapped[Optional[str]] = mapped_column(String(120))
    link: Mapped[Optional[str]] = mapped_column(String(400))
    conferencia: Mapped[Optional[str]] = mapped_column(String(200))


class ConsultaOcorrencia(Base):
    """Quais fontes de ocorrências foram consultadas na coleta e quando, para
    o app dizer "nada encontrado em X, consultado em D" só quando é verdade."""

    __tablename__ = "consulta_ocorrencia"

    fonte: Mapped[str] = mapped_column(String(10), primary_key=True)
    consultado_em: Mapped[date] = mapped_column(Date)
    registros: Mapped[int] = mapped_column(Integer)
    # Quantos políticos puderam ser conferidos por CPF nesta fonte.
    conferidos: Mapped[Optional[int]] = mapped_column(Integer)


class VerificacaoOcorrencia(Base):
    """Fonte em que o político pôde ser conferido (achado no TSE; CPF
    conferível para CGU e TCU). Sem esta linha, o app não diz "nada
    encontrado": diz que não foi possível conferir."""

    __tablename__ = "verificacao_ocorrencia"

    casa: Mapped[str] = mapped_column(String(10), primary_key=True)
    codigo_politico: Mapped[int] = mapped_column(Integer, primary_key=True)
    fonte: Mapped[str] = mapped_column(String(10), primary_key=True)


class Ipca(Base):
    """Variação mensal do IPCA (%), série 433 do Banco Central."""

    __tablename__ = "ipca"

    competencia: Mapped[date] = mapped_column(Date, primary_key=True)
    variacao: Mapped[Decimal] = mapped_column(Numeric(8, 4))


class Subsidio(Base):
    """Salário (subsídio) bruto mensal de um cargo a partir de uma data."""

    __tablename__ = "subsidio"
    __table_args__ = (UniqueConstraint("cargo", "vigencia_inicio", name="uq_subsidio"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo: Mapped[str] = mapped_column(String(60))
    vigencia_inicio: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    ato: Mapped[Optional[str]] = mapped_column(String(200))
    fonte: Mapped[Optional[str]] = mapped_column(String(400))


_engine: Optional[Engine] = None
_Session: Optional[sessionmaker] = None


def configurar(url: Optional[str] = None) -> Engine:
    """Cria (ou recria) o engine e as tabelas."""
    global _engine, _Session
    _engine = create_engine(url or database_url(), future=True)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


@contextmanager
def sessao() -> Iterator[Session]:
    if _Session is None:
        configurar()
    assert _Session is not None
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
