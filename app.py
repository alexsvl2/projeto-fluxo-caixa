import sqlite3
import os
import click
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

# O comando 'create-user' não funcionará na Render, mas o manteremos para uso local
@app.cli.command('create-user')
@click.argument('username')
@click.argument('password')
def create_user_command(username, password):
    # ... (código do create_user_command)

# --- ROTA TEMPORÁRIA PARA CRIAR O PRIMEIRO USUÁRIO ---
@app.route('/criar-primeiro-usuario/<username>/<password>')
def criar_primeiro_usuario(username, password):
    conn = sqlite3.connect(DATABASE)
    # Verifica se já existe algum usuário
    user_exists = conn.execute('SELECT * FROM usuarios').fetchone()
    if user_exists:
        conn.close()
        return "Erro: Um usuário já existe. Esta rota só pode ser usada uma vez.", 403

    # Se não existir, cria o novo usuário
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    conn.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()
    return f"Usuário '{username}' criado com sucesso! Agora você pode remover esta rota do seu app.py."

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (código da rota de login)
    return render_template('login.html')

# ... (restante do seu código app.py sem alterações) ...
