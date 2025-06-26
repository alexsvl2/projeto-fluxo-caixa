import sqlite3
import os
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, cli, abort

# --- CONFIGURAÇÃO DO APP E BANCO DE DADOS ---
app = Flask(__name__, instance_relative_config=True)

# --- TRECHO MODIFICADO ---
# Define o caminho para o disco persistente da Render.
# A Render vai criar um disco em '/var/data'. Usamos essa pasta para salvar nosso banco.
RENDER_DATABASE_DIR = '/var/data'
DATABASE = os.path.join(RENDER_DATABASE_DIR, 'fluxo_caixa.db')

# Cria o diretório do banco de dados se ele não existir
if not os.path.exists(RENDER_DATABASE_DIR):
    try:
        os.makedirs(RENDER_DATABASE_DIR)
    except OSError:
        # Ignora o erro se o diretório já foi criado por outro processo
        pass
# --- FIM DO TRECHO MODIFICADO ---


# --- FUNÇÕES DO BANCO DE DADOS ---
@app.cli.command('init-db')
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    # Garante que o diretório exista antes de conectar
    if not os.path.exists(RENDER_DATABASE_DIR):
        os.makedirs(RENDER_DATABASE_DIR)
        
    conn = sqlite3.connect(DATABASE)
    with app.open_resource('schema.sql', mode='r') as f:
        conn.cursor().executescript(f.read())
    conn.commit()
    conn.close()
    print(f'Banco de dados inicializado em {DATABASE}')

def get_transacao(transacao_id):
    """Busca uma única transação pelo seu ID."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    transacao = conn.execute('SELECT * FROM transacoes WHERE id = ?', (transacao_id,)).fetchone()
    conn.close()
    if transacao is None:
        abort(404)
    return transacao

# --- ROTAS DA APLICAÇÃO (sem alterações) ---

@app.route('/')
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
    else: # mes_atual ou padrão
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    query = "SELECT * FROM transacoes WHERE data_transacao BETWEEN ? AND ? ORDER BY data_transacao DESC, id DESC"
    transacoes = conn.execute(query, (str(start_date), str(end_date))).fetchall()
    conn.close()
    return render_template('extrato.html', transacoes=transacoes, periodo_selecionado=periodo, start_date=request.args.get('start_date', ''), end_date=request.args.get('end_date', ''))

@app.route('/add', methods=['POST'])
def add_transacao():
    data_transacao = request.form.get('data_transacao') or date.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DATABASE)
    conn.execute('INSERT INTO transacoes (data_transacao, tipo, descricao, valor) VALUES (?, ?, ?, ?)',
                 (data_transacao, request.form['tipo'], request.form['descricao'], float(request.form['valor'])))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/<int:id>/edit', methods=['GET', 'POST'])
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
def delete_transacao(id):
    get_transacao(id)
    conn = sqlite3.connect(DATABASE)
    conn.execute('DELETE FROM transacoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('extrato'))

# O bloco if __name__ == '__main__': não é mais necessário para produção, mas pode ser mantido para testes locais.
# if __name__ == '__main__':
#     app.run(debug=True)
