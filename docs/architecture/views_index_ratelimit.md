# View Index com Rate Limiting (core/views.py)

## 📍 Arquivo: `core/views.py` - função `index`

## 🎯 O que é
View principal que **renderiza o formulário** (GET) e **processa o envio** (POST) de nova denúncia. Protegida por rate limiting.

---

## 💻 Código Completo

```python
from django_ratelimit.decorators import ratelimit

# GET: 30 req/min por IP
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
# POST: 10 req/min por IP (protege envio de formulário)
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def index(request):
    if request.method == 'POST':
        form = NewDenunciaForm(request.POST)
        files = UploadEvidencias(request.POST, request.FILES)

        if form.is_valid():
            denuncia = form.save(commit=False)
            denuncia = form.save()

            file = request.FILES.getlist('imagem')
            for f in file:
                evidencia = Evidencia(denuncia=denuncia, imagem=f)
                evidencia.save()
                # ENQUEUE ASYNC
                limpar_exif_imagem.delay(evidencia.id)

            return redirect('core:protocol', protocolo=denuncia.protocolo)
    else:
        form = NewDenunciaForm()
        files = UploadEvidencias()

    return render(request, 'core/index.html', {
        'form': form,
        'files': files,
        'title': 'Nova Denuncia',
    })
```

---

## 🔍 Decorators `@ratelimit` - Análise Detalhada

### Ordem dos Decorators (Importante!)
```python
@ratelimit(key='ip', rate='30/m', method='GET', block=True)   # 1º - GET
@ratelimit(key='ip', rate='10/m', method='POST', block=True)  # 2º - POST
def index(request):
```
**Execução:** Django aplica **de baixo para cima** (POST primeiro, depois GET).
- Request POST → verifica POST rate limit → depois GET (não bate, method diferente).
- Request GET → verifica GET rate limit.

### Parâmetros Comuns
| Parâmetro | Valor | Significado |
|-----------|-------|-------------|
| `key='ip'` | `'ip'` | Identifica por `request.META['REMOTE_ADDR']` |
| `rate='30/m'` | `'30/m'` | 30 requisições por **minuto** |
| `method='GET'` | `'GET'` | Só aplica a GET |
| `block=True` | `True` | **Bloqueia** (HTTP 429) vs só marca `request.limited` |

### Taxas Escolhidas
| Método | Taxa | Justificativa |
|--------|------|---------------|
| GET | 30/min | Usuário navega, recarrega, abre aba - generoso |
| POST | 10/min | **Envio de formulário** - restritivo (spam/bot protection) |

---

## 🔍 Lógica POST - Passo a Passo

```python
if request.method == 'POST':
    # 1. Bind forms com dados
    form = NewDenunciaForm(request.POST)
    files = UploadEvidencias(request.POST, request.FILES)

    # 2. Validação
    if form.is_valid():
        # 3. Salva denúncia (commit=False → instancia sem salvar)
        denuncia = form.save(commit=False)
        # 4. Salva de verdade (gera protocolo UUID, created_at)
        denuncia = form.save()

        # 5. Processa arquivos (múltiplos)
        file = request.FILES.getlist('imagem')
        for f in file:
            # 5a. Cria objeto Evidencia vinculado
            evidencia = Evidencia(denuncia=denuncia, imagem=f)
            evidencia.save()  # Salva arquivo em /media/denuncia_images/

            # 5b. ENQUEUE TASK ASSÍNCRONA
            limpar_exif_imagem.delay(evidencia.id)

        # 6. Redirect PRG (Post-Redirect-Get)
        return redirect('core:protocol', protocolo=denuncia.protocolo)
```

### `form.save(commit=False)` vs `form.save()`
| Chamada | Função |
|---------|--------|
| `save(commit=False)` | Instancia modelo **sem INSERT** (permite modificar antes) |
| `save()` | Faz INSERT real, gera `protocolo` (UUID), `created_at` |

**Por que dois saves?** Padrão Django para quando você precisa setar campos extras antes de salvar. Aqui não modifica nada entre os dois, mas mantém padrão.

### `request.FILES.getlist('imagem')`
- **`getlist`** = retorna **lista** (mesmo campo `name="imagem"` múltiplo).
- `request.FILES['imagem']` retorna **apenas último** arquivo.

### `limpar_exif_imagem.delay(evidencia.id)`
- **Não bloqueia** response HTTP.
- Serializa `{"args": [id]}` → `LPUSH` Redis → Worker processa.
- Retorna `AsyncResult` (ignorado aqui).

---

## 🔍 Lógica GET

```python
else:
    form = NewDenunciaForm()      # Form vazio
    files = UploadEvidencias()    # Form vazio para arquivos

return render(request, 'core/index.html', {
    'form': form,
    'files': files,
    'title': 'Nova Denuncia',
})
```

---

## 🔗 Rate Limit → Redis → 429

```
Request POST /denunciar/
    │
    ▼
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
    │
    ├─ Redis: INCR forms_denuncia:rl:ip:192.168.1.1:/denunciar/
    │         TTL 60s
    │
    ├─ Se contador <= 10 → Permite → View executa
    │
    └─ Se contador > 10  → BLOQUEIA
         │
         ▼
    RATELIMIT_VIEW = 'core.views.ratelimited_error'
         │
         ▼
    HTTP 429 "Muitas requisições..."
```

---

## 📝 Template Context

| Variável | Tipo | Uso no Template |
|----------|------|-----------------|
| `form` | `NewDenunciaForm` | `{{ form.as_p }}` ou campos individuais |
| `files` | `UploadEvidencias` | `{{ files.as_p }}` para input multiple |
| `title` | `str` | `<h1>{{ title }}</h1>` |

---

## 📚 Referências
- [django-ratelimit Decorator](https://django-ratelimit.readthedocs.io/en/stable/decorators.html)
- [Django Forms](https://docs.djangoproject.com/en/5.2/topics/forms/)
- [File Uploads](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/)