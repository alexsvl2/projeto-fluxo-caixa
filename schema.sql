-- Apaga as tabelas existentes para garantir uma recriação limpa.
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS transacoes;

-- A tabela de usuários continua igual, para controlar o acesso.
CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

-- TRECHO MODIFICADO: A tabela de transações não tem mais a coluna 'user_id'.
CREATE TABLE transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data_transacao TEXT NOT NULL,
  tipo TEXT NOT NULL,
  descricao TEXT NOT NULL,
  valor REAL NOT NULL
);
