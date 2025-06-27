-- Apaga a tabela 'transacoes' se ela já existir, para garantir uma recriação limpa.
DROP TABLE IF EXISTS transacoes;

-- Apaga a tabela 'usuarios' se ela já existir.
DROP TABLE IF EXISTS usuarios;

-- Cria a nova tabela 'transacoes' sem a coluna user_id
CREATE TABLE transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data_transacao TEXT NOT NULL,
  tipo TEXT NOT NULL,
  descricao TEXT NOT NULL,
  valor REAL NOT NULL
);

-- Cria a nova tabela 'usuarios' para o sistema de login.
CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);
