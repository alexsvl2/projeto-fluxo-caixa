import sqlite3
import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURAÇÃO DO APP E BANCO DE DADOS ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'

RENDER_DATABASE_DIR = '/var/data'
DATABASE = os.path.join(RENDER_DATABASE_DIR, 'fluxo_caixa.db')

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
    if not os.path.exists(DATABASE):
        return None
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    user_data = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password=user_data['password'])
    return None

# --- ROTA DE SETUP (TEMPORÁRIA) ---
@app.route('/setup/<username>/<password>')
def setup_route(username, password):
    """
    Esta rota inicializa o banco de dados e cria o primeiro usuário.
    Deve ser usada apenas uma vez e depois removida por segurança.
    """
    try:
        # Passo 1: Inicializar o banco de dados
        conn = sqlite3.connect(DATABASE)
        with app.open_resource('schema.sql', mode='r') as f:
            conn.cursor().executescript(f.read())
        conn.commit()
        
        # Passo 2: Criar o primeiro usuário, se não houver nenhum
        user_count = conn.execute('SELECT COUNT(id) FROM usuarios').fetchone()[0]
        if user_count == 0:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            conn.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            message = f"Banco de dados inicializado e usuário '{username}' criado com sucesso!"
        else:
            message = "Banco de dados já estava inicializado. Nenhum novo usuário foi criado."
            
        conn.close()
        return f"<h1>Configuração Concluída</h1><p>{message}</p><p><b>IMPORTANTE:</b> Remova agora a rota '/setup' do seu ficheiro app.py e publique novamente.</p>", 200

    except Exception as e:
        return f"<h1>Ocorreu um erro durante a configuração:</h1><pre>{e}</pre>", 500

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # Verifica se o DB existe antes de tentar o login
        if not os.path.exists(DATABASE):
            flash('O sistema ainda não foi configurado. Por favor, contacte o administrador.', 'warning')
            return render_template('login.html')
            
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

# --- ROTAS DA APLICAÇÃO ---
# (As rotas / , /extrato, /add, /edit, /delete continuam exatamente as mesmas da versão anterior)

@app.route('/')
@login_required
def index():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    transacoes = conn.execute('SELECT tipo, valor FROM transacoes').fetchall()
    conn.close()
    total_entradas = sum(row['valor'] for row in transacoes if row['tipo'] == 'entrada')
    total_saidas = sum(row['valor'] for row in transacoes if row['tipo'] == 'saida')
    saldo = total_entradas - total_saidas
    return render_template('index.html', saldo=saldo, total_entradas=total_entradas, total_saidas=total_saidas)

@app.route('/extrato')
@login_required
def extrato():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    periodo = request.args.get('periodo', 'mes_atual')
    today = date.today()

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
    else: 
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    query = "SELECT * FROM transacoes WHERE data_transacao BETWEEN ? AND ? ORDER BY data_transacao DESC, id DESC"
    transacoes = conn.execute(query, (str(start_date), str(end_date))).fetchall()
    conn.close()
    
    total_entradas_periodo = sum(row['valor'] for row in transacoes if row['tipo'] == 'entrada')
    total_saidas_periodo = sum(row['valor'] for row in transacoes if row['tipo'] == 'saida')
    saldo_periodo = total_entradas_periodo - total_saidas_periodo
    
    return render_template('extrato.html', transacoes=transacoes, periodo_selecionado=periodo,
                           start_date=request.args.get('start_date', ''), end_date=request.args.get('end_date', ''),
                           saldo_periodo=saldo_periodo, total_entradas_periodo=total_entradas_periodo, total_saidas_periodo=total_saidas_periodo)

@app.route('/add', methods=['POST'])
@login_required
def add_transacao():
    data_transacao = request.form.get('data_transacao') or date.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DATABASE)
    conn.execute('INSERT INTO transacoes (data_transacao, tipo, descricao, valor) VALUES (?, ?, ?, ?)',
                 (data_transacao, request.form['tipo'], request.form['descricao'], float(request.form['valor'])))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def get_transacao(transacao_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    transacao = conn.execute('SELECT * FROM transacoes WHERE id = ?', (transacao_id,)).fetchone()
    conn.close()
    if transacao is None:
        abort(404)
    return transacao

@app.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transacao(id):
    transacao = get_transacao(id)
    if request.method == 'POST':
        conn = sqlite3.connect(DATABASE)
        conn.execute('UPDATE transacoes SET data_transacao = ?, tipo = ?, descricao = ?, valor = ? WHERE id = ?',
                     (request.form['data_transacao'], request.form['tipo'], request.form['descricao'], float(request.form['valor']), id))
        conn.commit()
        conn.close()
        return redirect(url_for('extrato'))
    return render_template('edit.html', transacao=transacao)

@app.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_transacao(id):
    get_transacao(id)
    conn = sqlite3.connect(DATABASE)
    conn.execute('DELETE FROM transacoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('extrato'))
