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
