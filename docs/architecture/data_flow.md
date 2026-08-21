# Fluxo de Dados Completo - Forms Denúncia

## 🎯 Visão Geral

Este documento descreve **todos os fluxos de dados** no sistema, do request HTTP inicial até a conclusão de tasks assíncronas.

---

## 🌊 Fluxo 1: Envio de Nova Denúncia (POST /)

```
┌─────────────┐
│  USUÁRIO    │
│ (Browser)   │
└──────┬──────┘
       │ HTTP POST /denunciar/
       │ multipart/form-data
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    NGINX (Futuro)                           │
│  - TLS Termination                                          │
│  - Static/Media serve                                       │
│  - Rate Limit (extra layer)                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ proxy_pass http://web:8000
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    GUNICORN (web:8000)                      │
│  Master Process                                             │
│    ├─ Worker 1 (PID 101)                                    │
│    ├─ Worker 2 (PID 102)                                    │
│    ├─ Worker 3 (PID 103)                                    │
│    └─ Worker 4 (PID 104)                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    DJANGO MIDDLEWARE                        │
│  1. SecurityMiddleware (HSTS, XSS, etc)                    │
│  2. SessionMiddleware  → Redis (SESSION_ENGINE)            │
│  3. CommonMiddleware                                         │
│  4. CsrfViewMiddleware  → Valida CSRF token                │
│  5. AuthenticationMiddleware → request.user                │
│  6. MessageMiddleware                                        │
│  7. XFrameOptionsMiddleware                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              RATE LIMIT CHECK (django-ratelimit)            │
│  @ratelimit(key='ip', rate='10/m', method='POST', block=True)│
│                                                             │
│  Redis: INCR forms_denuncia:rl:ip:192.168.1.1:/denunciar/  │
│         EXPIRE 60s                                          │
│                                                             │
│  Se > 10 → HTTP 429 (ratelimited_error view)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ OK
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    VIEW: core.views.index                   │
│                                                             │
│  1. form = NewDenunciaForm(request.POST)                   │
│  2. files = UploadEvidencias(request.POST, request.FILES)  │
│                                                             │
│  3. if form.is_valid():                                     │
│       denuncia = form.save(commit=False)  # Instancia      │
│       denuncia = form.save()                # INSERT DB    │
│       # Gera: protocolo (UUID), created_at, situacao=True  │
│                                                             │
│       # Arquivos                                           │
│       for f in request.FILES.getlist('imagem'):            │
│           evidencia = Evidencia(denuncia=denuncia, imagem=f)│
│           evidencia.save()  # Salva arquivo em /media/     │
│                                                             │
│           # TASK ASSÍNCRONA                                 │
│           limpar_exif_imagem.delay(evidencia.id)           │
│                                                             │
│       return redirect('core:protocol', protocolo=...)      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP 302 Redirect
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CELERY TASK ENQUEUE                            │
│                                                             │
│  limpar_exif_imagem.delay(evidencia_id)                    │
│                                                             │
│  1. Serializa args: {"args": [42], "kwargs": {}}           │
│  2. Gera task_id (UUID)                                    │
│  3. Mensagem Celery:                                       │
│     {                                                      │
│       "body": "base64(json)",                              │
│       "headers": {"task": "core.tasks.limpar_exif_imagem", │
│                   "id": "uuid", "lang": "py"},             │
│       "properties": {"delivery_mode": 2}                   │
│     }                                                      │
│  4. Redis: LPUSH celery <mensagem>                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │   REDIS (DB 0)      │
              │  Queue: celery      │
              │  LPUSH → BRPOP      │
              └─────────────────────┘
```

---

## 🌊 Fluxo 2: Processamento Assíncrono (Celery Worker)

```
┌─────────────────────────────────────────────────────────────┐
│                  CELERY WORKER (4 processos)                │
│                                                             │
│  Loop infinito:                                             │
│  1. BRPOP celery (bloqueia até chegar msg)                 │
│  2. Deserializa mensagem                                   │
│  3. Importa task function                                  │
│  4. EXECUTA: limpar_exif_imagem(42)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              TASK: limpar_exif_imagem(42)                   │
│                                                             │
│  try:                                                       │
│      # 1. ORM → PostgreSQL                                  │
│      evidencia = Evidencia.objects.get(id=42)              │
│      # SELECT * FROM core_evidencia WHERE id=42            │
│                                                             │
│      # 2. File System → Media Volume                        │
│      caminho = evidencia.imagem.path                        │
│      # /app/media/denuncia_images/foto_abc123.jpg          │
│                                                             │
│      # 3. Pillow Processamento                              │
│      img = Image.open(caminho)                              │
│      # Lê pixels, descarta EXIF/GPS/ICC/Thumbnail          │
│      pixels = list(img.getdata())                           │
│      img_limpa = Image.new(img.mode, img.size)              │
│      img_limpa.putdata(pixels)                              │
│      img_limpa.save(caminho)  # SOBRESCREVE                │
│                                                             │
│      # 4. Return → Result Backend                           │
│      return "SUCESSO: EXIF limpo para evidência #42"       │
│                                                             │
│  except Evidencia.DoesNotExist:                             │
│      return "Erro: Evidência #42 não encontrada"           │
│  except Exception as e:                                     │
│      return f"Erro ao processar: {e}"                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              REDIS RESULT BACKEND (DB 0)                    │
│                                                             │
│  SETEX celery-task-meta-<task_id> 86400                    │
│  '{"status": "SUCCESS", "result": "SUCESSO: ...",          │
│   "traceback": null, "children": []}'                      │
│                                                             │
│  TTL: 24h (default)                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌊 Fluxo 3: Consulta de Protocolo (GET /protocolo/<uuid>/)

```
┌─────────────┐
│  USUÁRIO    │
└──────┬──────┘
       │ GET /protocolo/550e8400-e29b-41d4-a716-446655440000/
       ▼
┌─────────────────────────────────────────────────────────────┐
│              RATE LIMIT (60/min GET)                        │
│  Redis: INCR forms_denuncia:rl:ip:...:/protocolo/.../      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              VIEW: core.views.protocol                      │
│                                                             │
│  1. denuncia = Denuncia.objects.filter(                    │
│         protocolo=protocolo).first()                       │
│     # SELECT * FROM core_denuncia WHERE protocolo='...'    │
│                                                             │
│  2. evidencia = Evidencia.objects.filter(                  │
│         denuncia=denuncia)                                 │
│     # SELECT * FROM core_evidencia WHERE denuncia_id=...   │
│                                                             │
│  3. usuario_autenticado = request.user.is_authenticated    │
│     base_template = 'dashboard/base.html' if auth else     │
│                     'core/base.html'                       │
│                                                             │
│  4. if POST:  # Equipe atualiza status                     │
│       close = CloseDenunciaForm(request.POST, instance=...) │
│       if valid: denuncia.situacao = not denuncia.situacao  │
│       close.save()  # UPDATE denuncia SET situacao=...,    │
│                        resposta=...                         │
│                                                             │
│  5. render('core/protocolo.html', context)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              TEMPLATE: core/protocolo.html                  │
│                                                             │
│  Extends: {{ base }}                                        │
│  Shows:                                                     │
│  - denuncia.nome_empresa                                    │
│  - denuncia.protocolo (UUID)                                │
│  - denuncia.situacao (Aberta/Fechada)                       │
│  - denuncia.resposta (se fechada)                           │
│  - evidencia loop (imagens)                                 │
│  - Form closeForm (se autenticado)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌊 Fluxo 4: Busca por Protocolo (GET /pesquisar/)

```
GET /pesquisar/?query=550e8400-e29b-41d4-a716-446655440000
       │
       ▼
Rate Limit (60/min)
       │
       ▼
View: pesquisar()
       │
       ├─ query = request.GET.get('query', '')
       │
       └─ if query: redirect('core:protocol', protocolo=query)
            │
            ▼
       302 → /protocolo/<uuid>/
```

---

## 🌊 Fluxo 5: Autenticação Dashboard (Login)

```
GET /dashboard/login/
       │
       ▼
Django Auth Views (LoginView)
       │
       ├─ template: dashboard/login.html
       ├─ form: LoginForm
       └─ success: /dashboard/

POST /dashboard/login/
       │
       ▼
AuthenticationMiddleware
       │
       ├─ authenticate(username, password)
       │   └─ UserBackend → SELECT * FROM auth_user WHERE username=...
       │
       ├─ login(request, user)
       │   └─ SessionMiddleware → request.session['_auth_user_id'] = user.pk
       │       └─ SESSION_ENGINE=cache → Redis SETEX session_key data
       │
       └─ Redirect /dashboard/

GET /dashboard/
       │
       ▼
@login_required
View: dashboard.views.index
       │
       ├─ Denuncia.objects.all() → Paginator
       └─ render dashboard/index.html
```

---

## 🌊 Fluxo 6: Agendamento Periódico (Celery Beat)

```
┌─────────────────────────────────────────────────────────────┐
│                    CELERY BEAT CONTAINER                    │
│                                                             │
│  Scheduler Loop (a cada 30s default):                      │
│                                                             │
│  1. SELECT * FROM django_celery_beat_periodictask          │
│     WHERE enabled=1 AND last_run_at < NOW()                │
│                                                             │
│  2. Para cada task devido:                                 │
│     LPUSH celery {task_message}                            │
│     UPDATE periodictask SET last_run_at=NOW()              │
│                                                             │
│  Exemplo tasks configuradas no Admin:                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Name: "Limpeza evidências órfãs"                    │   │
│  │ Task: core.tasks.limpar_evidencias_orfas            │   │
│  │ Schedule: Crontab 0 3 * * * (3:00 AM daily)         │   │
│  │ Args: []  Kwargs: {}                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ LPUSH
                          ▼
              ┌─────────────────────┐
              │   REDIS (DB 0)      │
              │  Queue: celery      │
              └─────────────────────┘
                          │
                          ▼ (Worker consome normalmente)
```

---

## 🌊 Fluxo 7: Upload de Arquivo (Detalhado)

```
┌─────────────┐
│  Browser    │
│  <input     │
│   type      │
│   file      │
│   multiple> │
└──────┬──────┘
       │ multipart/form-data
       │ Content-Disposition: form-data; name="imagem"; filename="foto.jpg"
       │ Content-Type: image/jpeg
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Django Request Processing                                  │
│                                                             │
│  request.FILES['imagem'] → InMemoryUploadedFile            │
│  (se < 2.5MB) ou TemporaryUploadedFile (se > 2.5MB)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Form Validation                                            │
│                                                             │
│  UploadEvidencias(form)                                     │
│  ├─ Clean: valida se é imagem (Pillow)                     │
│  └─ Save: evidencia = Evidencia(imagem=f, denuncia=d)      │
│       evidencia.save()                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  File Storage (ImageField)                                  │
│                                                             │
│  1. Gera nome único: foto_<uuid>.jpg                       │
│  2. Path: MEDIA_ROOT/upload_to/nome                        │
│     /app/media/denuncia_images/foto_a1b2c3.jpg             │
│  3. Salva arquivo no volume media_volume                    │
│  4. DB: UPDATE core_evidencia SET imagem='denuncia_images/ │
│     foto_a1b2c3.jpg' WHERE id=...                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  MEDIA VOLUME       │
              │  /app/media/        │
              │  denuncia_images/   │
              │    foto_a1b2c3.jpg  │
              └─────────────────────┘
                          │
              (Worker lê mesmo volume para processar EXIF)
```

---

## 📊 Resumo de Armazenamento por Componente

| Componente | Onde Armazena | Tipo | TTL/Persistência |
|------------|---------------|------|------------------|
| **Denúncias** | PostgreSQL | Relacional | Permanente |
| **Evidências (metadados)** | PostgreSQL | Relacional | Permanente |
| **Evidências (arquivos)** | Volume `media_volume` | Arquivos | Permanente |
| **Cache Views** | Redis DB 1 | Key-Value | 5 min (config) |
| **Sessões** | Redis DB 1 | Key-Value | 2 semanas |
| **Rate Limit** | Redis DB 1 | Key-Value | 1 min (janela) |
| **Celery Broker** | Redis DB 0 | Listas | Até consumo |
| **Celery Results** | Redis DB 0 | Strings | 24h |
| **Beat Schedule** | PostgreSQL | Relacional | Permanente |
| **Static Files** | Volume `static_volume` | Arquivos | Permanente |

---

## 🔄 Diagramas de Sequência Resumidos

### Envio Denúncia
```
User → Nginx → Gunicorn → Django Middleware → RateLimit → View.index()
    → Form.save() → PostgreSQL INSERT (Denuncia)
    → Evidencia.save() → Media Volume + PostgreSQL INSERT
    → limpar_exif_imagem.delay() → Redis LPUSH
    → HTTP 302 Redirect
    → Celery Worker BRPOP → Processa → Redis SETEX Result
```

### Consulta Protocolo
```
User → Nginx → Gunicorn → Middleware → RateLimit → View.protocol()
    → PostgreSQL SELECT (Denuncia + Evidencia)
    → Template Render
    → HTTP 200 HTML
```

---

## 📚 Referências
- [Django Request/Response Cycle](https://docs.djangoproject.com/en/5.2/topics/http/views/)
- [Celery Architecture](https://docs.celeryq.dev/en/stable/userguide/architecture.html)
- [Redis Data Types](https://redis.io/docs/latest/develop/data-types/)