# View Search com Rate Limiting (core/views.py)

## 📍 Arquivo: `core/views.py` - função `pesquisar`

## 🎯 O que é
View que permite **buscar denúncia por protocolo** via formulário simples. Redireciona para view `protocol` se encontrado.

---

## 💻 Código Completo

```python
from django_ratelimit.decorators import ratelimit

# GET: 60 req/min por IP
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
def pesquisar(request):
    query = request.GET.get('query', '')

    if query:
        return redirect('core:protocol', protocolo=query)

    return render(request, 'core/pesquisar.html', {
        'query': query,
    })
```

---

## 🔍 Rate Limiting

```python
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
```
- **60/min** = generoso (busca por protocolo, usuário pode errar digitação).
- Só **GET** (formulário só envia GET).

---

## 🔍 Lógica Simples

```python
query = request.GET.get('query', '')  # Pega ?query=...

if query:
    return redirect('core:protocol', protocolo=query)
```

- Pega parâmetro `?query=550e8400-e29b-41d4-a716-446655440000`.
- **Redirect 302** para `/protocolo/<uuid>/`.
- **Não valida UUID** - view `protocol` trata `None` se inválido.

---

## 🔗 Fluxo

```
GET /pesquisar/?query=550e8400-e29b-41d4-a716-446655440000
    │
    ├─ Rate Limit: 60/min
    ├─ query = "550e8400-e29b-41d4-a716-446655440000"
    ├─ redirect('core:protocol', protocolo=query)
    └─ 302 → /protocolo/550e8400-e29b-41d4-a716-446655440000/
```

---

## 📝 Template `pesquisar.html`

```html
<form method="GET" action="{% url 'core:pesquisar' %}">
    <input type="text" name="query" placeholder="Digite o protocolo" value="{{ query }}">
    <button type="submit">Buscar</button>
</form>

{% if query and not denuncia %}
    <p class="error">Protocolo não encontrado</p>
{% endif %}
```

---

## 📚 Referências
- [Django Redirect](https://docs.djangoproject.com/en/5.2/topics/http/shortcuts/#redirect)