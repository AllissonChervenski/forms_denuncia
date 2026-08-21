# Configuração de Internacionalização (forms_denuncia/settings.py)

## 📍 Arquivo: `forms_denuncia/settings.py`

## 🎯 O que é
Configurações de **idioma, timezone, formatação** para o Brasil.

---

## 💻 Código

```python
# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
```

---

## 🔍 Linha por Linha

### `LANGUAGE_CODE = 'pt-br'`
- **Idioma padrão:** Português do Brasil.
- Afeta: mensagens de erro Django, admin, formatação de datas/números.
- Requer: `django.middleware.locale.LocaleMiddleware` (se multi-idioma).

### `TIME_ZONE = 'America/Sao_Paulo'`
- **Timezone do Django:** Horário de Brasília (BRT/BRST).
- Afeta: `DateTimeField` (created_at, data_ocorrido), logs, templates `{{ data|date }}`.
- **Diferente de `CELERY_TIMEZONE`** (que é do worker/beat).

### `USE_I18N = True`
- **Ativa internacionalização:** Carrega arquivos `.po`/`mo` de tradução.
- Se `False`: ignora traduções (ligeiramente mais rápido).

### `USE_TZ = True`
- **Timezone-aware datetimes:** Django armazena **UTC no banco**, converte para `TIME_ZONE` na exibição.
- **Crítico para:** Usuários em fusos diferentes, agendamentos Beat, logs consistentes.
- Se `False`: `DateTimeField` salva "naive" (sem timezone) = problemas em DST.

---

## 🔗 Timezone Django vs Celery

| Componente | Setting | Valor |
|------------|---------|-------|
| Django | `TIME_ZONE` | `America/Sao_Paulo` |
| Celery | `CELERY_TIMEZONE` | `America/Sao_Paulo` |
| Beat | Usa `CELERY_TIMEZONE` | `America/Sao_Paulo` |

**Por que ambos?** Django roda no processo Web; Celery roda em processos separados (worker/beat). Cada um precisa saber o timezone local para:
- `auto_now_add=True` → `datetime.now(tz)` correto
- `crontab(hour=3)` → 3h **no timezone configurado**
- Logs com timestamp local

---

## 📚 Referências
- [Django Timezones](https://docs.djangoproject.com/en/5.2/topics/i18n/timezones/)
- [Celery Timezones](https://docs.celeryq.dev/en/stable/userguide/configuration.html#timezone)