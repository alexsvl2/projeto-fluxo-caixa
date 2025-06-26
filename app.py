import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, abort, cli
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# --- CONFIGURAÇÃO DO APP E BANCO DE DADOS ---
app = Flask(__name__)

# Pega a URL de conexão do banco de dados das variáveis de ambiente da Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL is None:
    raise ValueError("Variável de ambiente DATABASE_URL não foi definida.")

# Corrige a URL do PostgreSQL para SQLAlchemy (a Render usa 'postgres://' e o SQLAlchemy espera 'postgresql://')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELO DA TABELA (DEFINIDO COM SQLAlchemy) ---
class Transacao(Base):
    __tablename__ = "transacoes"
    id = Column(Integer, primary_key=True, index=True)
    data_transacao = Column(Date, nullable=False)
    tipo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)

# --- COMANDO PARA INICIALIZAR O BANCO ---
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco de dados."""
    Base.metadata.create_all(bind=engine)
    print("Banco de dados inicializado.")

# --- ROTAS DA APLICAÇÃO ---

@app.route('/')
def index():
    session = SessionLocal()
    transacoes = session.query(Transacao).all()
    session.close()
    
    total_entradas = sum(t.valor for t in transacoes if t.tipo == 'entrada')
    total_saidas = sum(t.valor for t in transacoes if t.tipo == 'saida')
    saldo = total_entradas - total_saidas

    return render_template('index.html', saldo=saldo, total_entradas=total_entradas, total_saidas=total_saidas)

@app.route('/extrato')
def extrato():
    session = SessionLocal()
    periodo = request.args.get('periodo', 'mes_atual')
    today = date.today()
    
    # Lógica de cálculo das datas (mesma de antes)
    if periodo == 'semana_atual':
        start_date, end_date = today - timedelta(days=today.weekday()), today + timedelta(days=6-today.weekday())
    elif periodo == 'ultimos_7_dias':
        start_date, end_date = today - timedelta(days=6), today
    elif periodo == 'ultimos_15_dias':
        start_date, end_date = today - timedelta(days=14), today
    elif periodo == 'personalizado':
        start_date, end_date = request.args.get('start_date'), request.args.get('end_date')
        if not start_date or not end_date:
            return redirect(url_for('extrato', periodo='mes_atual'))
    else: # mes_atual ou padrão
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    transacoes = session.query(Transacao).filter(Transacao.data_transacao.between(start_date, end_date)).order_by(Transacao.data_transacao.desc(), Transacao.id.desc()).all()
    session.close()
    
    return render_template('extrato.html', transacoes=transacoes, periodo_selecionado=periodo, start_date=request.args.get('start_date', ''), end_date=request.args.get('end_date', ''))

@app.route('/add', methods=['POST'])
def add_transacao():
    session = SessionLocal()
    nova_transacao = Transacao(
        data_transacao=date.fromisoformat(request.form.get('data_transacao') or date.today().isoformat()),
        tipo=request.form['tipo'],
        descricao=request.form['descricao'],
        valor=float(request.form['valor'])
    )
    session.add(nova_transacao)
    session.commit()
    session.close()
    return redirect(url_for('index'))

@app.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_transacao(id):
    session = SessionLocal()
    transacao = session.query(Transacao).get(id)
    if transacao is None:
        session.close()
        abort(404)

    if request.method == 'POST':
        transacao.data_transacao = date.fromisoformat(request.form['data_transacao'])
        transacao.tipo = request.form['tipo']
        transacao.descricao = request.form['descricao']
        transacao.valor = float(request.form['valor'])
        session.commit()
        session.close()
        return redirect(url_for('extrato'))
    
    session.close()
    return render_template('edit.html', transacao=transacao)

@app.route('/<int:id>/delete', methods=['POST'])
def delete_transacao(id):
    session = SessionLocal()
    transacao = session.query(Transacao).get(id)
    if transacao:
        session.delete(transacao)
        session.commit()
    session.close()
    return redirect(url_for('extrato'))
