# Configuração do Banco de Dados PostgreSQL

## 📍 Arquivo: `forms_denuncia/settings.py`

## 🎯 O que é
Esta configuração diz ao Django **como conectar** no banco de dados PostgreSQL. É o "endereço e credenciais" que o Django usa para salvar e buscar denúncias, usuários, cidades, etc.

---

## 💻 Código Completo

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'forms_denuncia'),
        'USER': os.getenv('POSTGRES_USER', 'forms_denuncia'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'change-me'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}
```

---

## 🔍 Linha por Linha Explicada

### `'ENGINE': 'django.db.backends.postgresql'`
**O que faz:** Diz ao Django: "Use o driver PostgreSQL".
- O Django suporta vários bancos (SQLite, MySQL, PostgreSQL, Oracle).
- Este engine usa a biblioteca `psycopg2` (instalada via `psycopg2-binary`).
- **Por que PostgreSQL?** ACID completo, suporte nativo a UUID, JSONB, busca textual (`pg_trgm`), concorrência superior a SQLite/MySQL.

### `'NAME': os.getenv('POSTGRES_DB', 'forms_denuncia')`
**O que faz:** Nome do banco de dados dentro do PostgreSQL.
- `os.getenv('POSTGRES_DB', ...)` lê a variável de ambiente `POSTGRES_DB`.
- Se não existir, usa `'forms_denuncia'` como padrão (desenvolvimento).
- **Por que variável de ambiente?** Segurança (não hardcoda senhas/nomes no código) e flexibilidade (mesmo código roda em dev, staging, prod com bancos diferentes).

### `'USER': os.getenv('POSTGRES_USER', 'forms_denuncia')`
**O que faz:** Usuário de autenticação no PostgreSQL.
- Princípio de menor privilégio: usuário dedicado `forms_denuncia` (não `postgres` superuser).

### `'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'change-me')`
**O que faz:** Senha do usuário.
- **⚠️ Importante:** O padrão `'change-me'` é **inseguro para produção**. Em produção, a variável `POSTGRES_PASSWORD` **deve** ser definida no `.env` com senha forte.

### `'HOST': os.getenv('POSTGRES_HOST', 'db')`
**O que faz:** Endereço do servidor PostgreSQL.
- `'db'` é o **nome do serviço no Docker Compose**.
- Docker cria DNS interno: `db` resolve para o IP do container PostgreSQL.
- Em desenvolvimento local (sem Docker), você mudaria para `'localhost'` ou `'127.0.0.1'` via `.env`.

### `'PORT': os.getenv('POSTGRES_PORT', '5432')`
**O que faz:** Porta do PostgreSQL (padrão 5432).
- String `'5432'` porque `os.getenv` retorna string.

### `'CONN_MAX_AGE': 60`
**O que faz:** **Connection Pooling nativo do Django**.
- Mantém a conexão aberta por 60 segundos após o request.
- **Sem isso:** Django abre/fecha conexão a **cada request** (lento, gasta recursos).
- **Com isso:** Reutiliza conexão para requests subsequentes do mesmo worker Gunicorn.
- **Valor 60:** Equilíbrio entre performance (conexão quente) e não segurar conexões ociosas demais no Postgres.

### `'OPTIONS': {'connect_timeout': 10}`
**O que faz:** Timeout de **conexão inicial** (não query).
- Se o Postgres não responder em 10s, falha rápido.
- Evita workers travados indefinidamente se o banco cair.

---

## 🔗 Como se Conecta com a Arquitetura

```
┌─────────────┐     HOST=db      ┌─────────────┐
│   Django    │ ───────────────▶ │ PostgreSQL  │
│  (Web/      │   Docker DNS     │  (Container)│
│  Worker)    │                  │             │
└─────────────┘                  └─────────────┘
       │                                │
       │ CONN_MAX_AGE=60                │
       │ Reutiliza conexão              │
       ▼                                ▼
  Gunicorn                          Dados Persistidos
  Workers                           (Volume docker)
```

- **Web (Gunicorn):** Cada worker mantém pool de conexões (até 60s).
- **Celery Worker:** Também usa esta config (mesmo `settings.py`).
- **Migrations:** `docker compose exec web python manage.py migrate` cria tabelas aqui.

---

## ⚙️ Parâmetros e Escolhas

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Engine | postgresql | Produção, ACID, UUID, JSONB, busca textual |
| CONN_MAX_AGE | 60s | Performance: evita handshake TCP/SSL a cada request |
| connect_timeout | 10s | Fail-fast: não travar worker se DB indisponível |
| Variáveis de ambiente | Sim | 12-Factor App: config no ambiente, não no código |

---

## 🤔 Por Que Não SQLite?
- SQLite **não suporta concorrência real** (apenas 1 escrita por vez).
- Celery Workers + Gunicorn Workers = **múltiplos processos escrevendo**.
- SQLite corrompe ou trava em produção com carga.

## 🤔 Por Que Não MySQL?
- PostgreSQL tem suporte nativo melhor a **UUID** (PK da Denuncia).
- `pg_trgm` para busca textual (futuro: busca por descrição).
- JSONB nativo performático (futuro: metadados flexíveis).
- MVCC (Multi-Version Concurrency Control) superior.

---

## 📚 Referências
- [Django Database Settings](https://docs.djangoproject.com/en/5.2/ref/settings/#databases)
- [PostgreSQL Connection Pooling](https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-connection-pooling)
- [12-Factor App Config](https://12factor.net/config)