# gunicorn_config.py
# Configurações para o servidor Gunicorn em produção

# O número de processos de trabalho para rodar.
# A Render geralmente sugere um valor entre 2 e 4.
workers = 4

# O endereço e a porta em que o servidor vai escutar.
# '0.0.0.0' permite que a Render se conecte ao nosso app.
# A porta é definida por uma variável de ambiente da Render.
bind = "0.0.0.0:10000"

# O nome do nosso módulo Flask.
# 'app' é o nome do arquivo (app.py) e o segundo 'app' é o nome da variável Flask dentro dele.
wsgi_app = "app:app"