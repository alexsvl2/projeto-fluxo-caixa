import sqlite3
import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS E DA APP ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'

db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"


# --- MODELOS DO BANCO DE DADOS (TABELAS) ---
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Transacao(db.Model):
    __tablename__ = 'transacoes'
    id = db.Column(db.Integer, primary_key=True)
    data_transacao = db.Column(db.Date, nullable=False, default=date.today)
    tipo = db.Column(db.String(10), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)


# --- FUNÇÃO DE CARREGAMENTO DE UTILIZADOR ---
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# --- ROTA DE SETUP (TEMPORÁRIA) ---
@app.route('/setup/<username>/<password>')
def setup_route(username, password):
    """
    Esta rota inicializa o banco de dados e cria o primeiro usuário.
    Deve ser usada apenas uma vez e depois removida por segurança.
    """
    try:
        # Cria todas as tabelas (se não existirem)
        with app.app_context():
            db.create_all()

        # Verifica se já existe algum usuário
        user_count = Usuario.query.count()
        if user_count == 0:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = Usuario(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            message = f"Banco de dados inicializado e usuário '{username}' criado com sucesso!"
        else:
            message = "Banco de dados já estava inicializado. Nenhum novo usuário foi criado."
            
        return f"<h1>Configuração Concluída</h1><p>{message}</p><p><b>IMPORTANTE:</b> Remova agora a rota '/setup' do seu ficheiro app.py e publique novamente.</p>", 200

    except Exception as e:
        return f"<h1>Ocorreu um erro durante a configuração:</h1><pre>{e}</pre>", 500


# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login inválido. Verifique o usuário e a senha.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
@login_required
def index():
    transacoes = Transacao.query.all()
    total_entradas = sum(t.valor for t in transacoes if t.tipo == 'entrada')
    total_saidas = sum(t.valor for t in transacoes if t.tipo == 'saida')
    total_fiados = sum(t.valor for t in transacoes if t.tipo == 'fiado')
    
    saldo = total_entradas - total_saidas

    return render_template(
        'index.html', 
        saldo=saldo, 
        total_entradas=total_entradas, 
        total_saidas=total_saidas,
        total_fiados=total_fiados
    )

@app.route('/extrato')
@login_required
def extrato():
    query = Transacao.query
    tipo_filtro = request.args.get('tipo_filtro', 'todos')
    if tipo_filtro and tipo_filtro != 'todos':
        query = query.filter(Transacao.tipo == tipo_filtro)
    
    periodo = request.args.get('periodo', 'mes_atual')
    today = date.today()
    
    if periodo == 'semana_atual':
        start_date = today - timedelta(days=today.weekday())
        query = query.filter(Transacao.data_transacao >= start_date)
    elif periodo == 'ultimos_7_dias':
        start_date = today - timedelta(days=6)
        query = query.filter(Transacao.data_transacao >= start_date)
    elif periodo == 'ultimos_15_dias':
        start_date = today - timedelta(days=14)
        query = query.filter(Transacao.data_transacao >= start_date)
    elif periodo == 'personalizado':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            query = query.filter(Transacao.data_transacao.between(start_date, end_date))
    else: # mes_atual
        start_date = today.replace(day=1)
        query = query.filter(Transacao.data_transacao >= start_date)
        
    transacoes = query.order_by(Transacao.data_transacao.desc(), Transacao.id.desc()).all()
    
    total_entradas_periodo = sum(t.valor for t in transacoes if t.tipo == 'entrada')
    total_saidas_periodo = sum(t.valor for t in transacoes if t.tipo == 'saida')
    total_fiados_periodo = sum(t.valor for t in transacoes if t.tipo == 'fiado')
    saldo_periodo = total_entradas_periodo - total_saidas_periodo
    
    return render_template('extrato.html', transacoes=transacoes, 
                           periodo_selecionado=periodo,
                           tipo_selecionado=tipo_filtro,
                           start_date=request.args.get('start_date', ''), end_date=request.args.get('end_date', ''),
                           saldo_periodo=saldo_periodo, total_entradas_periodo=total_entradas_periodo, 
                           total_saidas_periodo=total_saidas_periodo, total_fiados_periodo=total_fiados_periodo)

@app.route('/add', methods=['POST'])
@login_required
def add_transacao():
    data_str = request.form.get('data_transacao')
    nova_transacao = Transacao(
        data_transacao=date.fromisoformat(data_str) if data_str else date.today(),
        tipo=request.form['tipo'],
        descricao=request.form['descricao'],
        valor=float(request.form['valor'])
    )
    db.session.add(nova_transacao)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transacao(id):
    transacao = Transacao.query.get_or_404(id)
    if request.method == 'POST':
        transacao.data_transacao = date.fromisoformat(request.form['data_transacao'])
        transacao.tipo = request.form['tipo']
        transacao.descricao = request.form['descricao']
        transacao.valor = float(request.form['valor'])
        db.session.commit()
        return redirect(url_for('extrato'))
    return render_template('edit.html', transacao=transacao)

@app.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_transacao(id):
    transacao = Transacao.query.get_or_404(id)
    db.session.delete(transacao)
    db.session.commit()
    return redirect(url_for('extrato'))
