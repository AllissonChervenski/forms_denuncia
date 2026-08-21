# View Protocol com Rate Limiting (core/views.py)

## 📍 Arquivo: `core/views.py` - função `protocol`

## 🎯 O que é
View que **exibe detalhes** de uma denúncia via protocolo UUID. Permite **atualização de status/resposta** (POST) pela equipe de segurança. Dupla proteção: rate limit + autenticação (dashboard).

---

## 💻 Código Completo

```python
from django_ratelimit.decorators import ratelimit

# GET: 60 req/min por IP
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
# POST: 20 req/min por IP
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def protocol(request, protocolo):
    denuncia = Denuncia.objects.filter(protocolo=protocolo).first()
    usuario_autenticado = request.user.is_authenticated
    base_template = 'core/base.html'
    evidencia = Evidencia.objects.filter(denuncia=denuncia)

    if request.method == 'POST':
        close = CloseDenunciaForm(request.POST, instance=denuncia)

        if close.is_valid():
            if denuncia.situacao:
                denuncia.situacao = False
            else:
                denuncia.situacao = True

            close = close.save(commit=False)
            close.save()
    else:
        close = CloseDenunciaForm(instance=denuncia)

    if usuario_autenticado:
        base_template = 'dashboard/base.html'

    return render(request, 'core/protocolo.html', {
        'denuncia': denuncia,
        'evidencia': evidencia,
        'base': base_template,
        'closeForm': close
    })
```

---

## 🔍 Rate Limiting

```python
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
```

| Método | Taxa | Justificativa |
|--------|------|---------------|
| GET | 60/min | Consulta de protocolo - usuário pode recarregar, compartilhar link |
| POST | 20/min | Atualização de status - equipe legítima, mas protege contra abuso |

---

## 🔍 Busca por Protocolo UUID

```python
denuncia = Denuncia.objects.filter(protocolo=protocolo).first()
```

- **`filter().first()`** vs **`get()`**:
  - `get()` levanta `DoesNotExist` / `MultipleObjectsReturned` (exceções).
  - `filter().first()` retorna `None` se não achar (sem exceção).
  - Template trata `denuncia` como `None` graciosamente.

---

## 🔍 Lógica de Atualização (POST)

```python
if request.method == 'POST':
    close = CloseDenunciaForm(request.POST, instance=denuncia)

    if close.is_valid():
        # Toggle situacao
        if denuncia.situacao:
            denuncia.situacao = False  # Aberta → Fechada
        else:
            denuncia.situacao = True   # Fechada → Reaberta

        close = close.save(commit=False)
        close.save()  # Salva resposta + situacao
```

**`CloseDenunciaForm`** (core/forms.py):
```python
class CloseDenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ('resposta',)
        widgets = {
            "resposta": forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'style': 'resize:none;',
                'placeholder': "Resposta da situação da denúncia"
            })
        }
```
- Só expõe campo `resposta`.
- `situacao` é togglada na view (não no form).

---

## 🔍 Template Base Dinâmico

```python
usuario_autenticado = request.user.is_authenticated
base_template = 'core/base.html'

if usuario_autenticado:
    base_template = 'dashboard/base.html'
```

| Usuário | Template Base | Navbar |
|---------|---------------|--------|
| Anônimo | `core/base.html` | Pública (Nova Denúncia, Acompanhar) |
| Autenticado (Staff) | `dashboard/base.html` | Admin (Dashboard, Logout) |

---

## 🔗 Fluxo Completo

```
GET /protocolo/550e8400-e29b-41d4-a716-446655440000/
    │
    ├─ Rate Limit: 60/min (Redis INCR)
    ├─ Busca Denuncia por UUID
    ├─ Busca Evidencias (FK denuncia)
    ├─ Verifica request.user.is_authenticated
    ├─ Escolhe base_template
    └─ Render protocolo.html

POST /protocolo/.../  (Equipe responde)
    │
    ├─ Rate Limit: 20/min
    ├─ CloseDenunciaForm(instance=denuncia)
    ├─ Valida resposta
    ├─ Toggle situacao (True ↔ False)
    ├─ Salva resposta + situacao
    └─ Re-render com dados atualizados
```

---

## 📚 Referências
- [Django Forms with Instance](https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/#modelform)
- [UUID URL Pattern](https://docs.djangoproject.com/en/5.2/ref/urls/#uuid)