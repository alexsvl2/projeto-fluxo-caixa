import sqlite3
import os
import click # LINHA ADICIONADA
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURAÇÃO DO APP E BANCO DE DADOS ---
app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'

RENDER_DATABASE_DIR = '/var/data'
DATABASE = os.path.join(RENDER_DATABASE_DIR, 'fluxo_caixa.db')

if not os.path.exists(RENDER_DATABASE_DIR):
    try:
        os.makedirs(RENDER_DATABASE_DIR)
    except OSError:
        pass

# --- CONFIGURAÇÃO DO FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    user_data = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password=user_data['password'])
    return None

# --- FUNÇÕES DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DATABASE)
    with app.open_resource('schema.sql', mode='r') as f:
        conn.cursor().executescript(f.read())
    conn.commit()
    conn.close()

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print(f'Banco de dados inicializado em {DATABASE}')

@app.cli.command('create-user')
@click.argument('username')
@click.argument('password')
def create_user_command(username, password):
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)',
                     (username, generate_password_hash(password, method='pbkdf2:sha256')))
        conn.commit()
        print(f'Usuário "{username}" criado com sucesso.')
    except sqlite3.IntegrityError:
        print(f'Erro: Usuário "{username}" já existe.')
    finally:
        conn.close()

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        user_data = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'], password=user_data['password'])
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

# --- ROTAS DA APLICAÇÃO (PROTEGIDAS) ---
@app.route('/')
@login_required
def index():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    transacoes = conn.execute('SELECT tipo, valor FROM transacoes WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    total_entradas = sum(row['valor'] for row in transacoes if row['tipo'] == 'entrada')
    total_saidas = sum(row['valor'] for row in transacoes if row['tipo'] == 'saida')
    saldo = total_entradas - total_saidas
    return render_template('index.html', saldo=saldo, total_entradas=total_entradas, total_saidas=total_saidas)

@app.route('/extrato')
@login_required
def extrato():
    # ... (o código da rota extrato continua o mesmo, mas lembre-se de adicionar a lógica de user_id se necessário)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    # ... (lógica de filtro de data)
    query = "SELECT * FROM transacoes WHERE user_id = ? AND data_transacao BETWEEN ? AND ? ORDER BY data_transacao DESC, id DESC"
    # transacoes = conn.execute(query, (current_user.id, str(start_date), str(end_date))).fetchall()
    conn.close()
    # ...
    return render_template('extrato.html', ...)

@app.route('/add', methods=['POST'])
@login_required
def add_transacao():
    data_transacao = request.form.get('data_transacao') or date.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DATABASE)
    conn.execute('INSERT INTO transacoes (data_transacao, tipo, descricao, valor, user_id) VALUES (?, ?, ?, ?, ?)',
                 (data_transacao, request.form['tipo'], request.form['descricao'], float(request.form['valor']), current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transacao(id):
    # ...
    return render_template('edit.html', ...)

@app.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_transacao(id):
    # ...
    return redirect(url_for('extrato'))
