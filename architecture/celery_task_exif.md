# Task Assíncrona: limpar_exif_imagem (core/tasks.py)

## 📍 Arquivo: `core/tasks.py`

## 🎯 O que é
Task Celery que **remove metadados EXIF/GPS** de imagens anexadas a denúncias. Roda em background após upload, garantindo privacidade do denunciante.

---

## 💻 Código Completo

```python
from celery import shared_task
from PIL import Image
from .models import Evidencia
import logging

logger = logging.getLogger(__name__)

@shared_task
def limpar_exif_imagem(evidencia_id):
    """
    Recebe o ID de uma evidencia já salva no banco, abre a imagem em background,
    remove os metadados (EXIF/GPS) e sobrescreve o arquivo limpo.
    """
    try:
        # 1. Busca evidência no banco
        evidencia = Evidencia.objects.get(id=evidencia_id)
        caminho_imagem = evidencia.imagem.path

        # 2. Abre imagem original
        img = Image.open(caminho_imagem)

        # 3. Extrai APENAS pixels (descarta EXIF, GPS, thumbnail, ICC profile)
        dados_pixel = list(img.getdata())

        # 4. Cria nova imagem "limpa" mesmo modo/tamanho
        imagem_limpa = Image.new(img.mode, img.size)
        imagem_limpa.putdata(dados_pixel)

        # 5. Sobrescreve arquivo original
        imagem_limpa.save(caminho_imagem)

        msg = f"SUCESSO: EXIF limpo para evidência #{evidencia_id}"
        logger.info(msg)
        return msg

    except Evidencia.DoesNotExist:
        return f"Erro: Evidência #{evidencia_id} não encontrada."
    except Exception as e:
        return f"Erro ao processar imagem: {str(e)}"
```

---

## 🔍 Linha por Linha

### `@shared_task`
**O que faz:** Decorator que registra a função como **task Celery** no registry global.

**Diferença `@app.task` vs `@shared_task`:**
| Aspecto | `@app.task` | `@shared_task` |
|---------|-------------|----------------|
| Precisa da instância `app` | Sim | Não |
| Import circular | Risco (importa `app` de celery.py) | **Seguro** (registry global) |
| Uso recomendado | Dentro do mesmo módulo do app | **Em apps Django (core/tasks.py)** |

**Por que aqui?** `core/tasks.py` não tem acesso direto à instância `app` (está em `forms_denuncia/celery.py`). `shared_task` resolve isso.

---

### `def limpar_exif_imagem(evidencia_id):`

**Assinatura:** Recebe **apenas o ID** (inteiro), não o objeto.

**Por que ID e não objeto?**
- Tasks serializam argumentos para JSON.
- Objetos Django **não são JSON-serializáveis** nativamente.
- ID é leve, seguro, e worker re-busca do banco (dados frescos).

---

### Bloco Try/Except - Estrutura de Resiliência

```python
try:
    # ... lógica principal ...
    return msg_sucesso
except Evidencia.DoesNotExist:
    return f"Erro: Evidência #{evidencia_id} não encontrada."
except Exception as e:
    return f"Erro ao processar imagem: {str(e)}"
```

**Por que retornar string e não raise?**
- **Celery guarda o retorno** no Result Backend.
- Se der `raise`, task fica status `FAILURE` com traceback.
- Retornando string: status `SUCCESS` com mensagem de erro legível.
- Flower mostra "Sucesso" com mensagem de erro (monitoramento não alerta falso).
- **Trade-off:** Perde stack trace automático. Loga com `logger.error()` se precisar.

---

### `evidencia = Evidencia.objects.get(id=evidencia_id)`

**O que faz:** Busca registro no **PostgreSQL** usando PK.

**Por que `get` e não `filter().first()`?**
- `get` levanta `DoesNotExist` se não achar → capturamos no `except`.
- `filter().first()` retorna `None` → teria que checar `if not evidencia:`.

---

### `caminho_imagem = evidencia.imagem.path`

**O que faz:** Resolve caminho **físico no disco** do arquivo.

**Como funciona:**
- `Evidencia.imagem = ImageField(upload_to='denuncia_images')`
- `.path` = `MEDIA_ROOT + 'denuncia_images/' + nome_arquivo`
- Ex: `/app/media/denuncia_images/foto_abc123.jpg`

**Volume Docker:** `media_volume:/app/media` garante que worker e web veem **mesmo arquivo**.

---

### Processamento com Pillow (PIL)

```python
img = Image.open(caminho_imagem)
dados_pixel = list(img.getdata())
imagem_limpa = Image.new(img.mode, img.size)
imagem_limpa.putdata(dados_pixel)
imagem_limpa.save(caminho_imagem)
```

**O que cada linha faz:**

| Linha | Ação | Remove |
|-------|------|--------|
| `Image.open()` | Lê arquivo, decodifica | - |
| `img.getdata()` | Extrai **sequência de pixels** (R,G,B ou R,G,B,A) | EXIF, GPS, ICC, Thumbnail, Comentários, MakerNotes |
| `Image.new(mode, size)` | Cria imagem **nova, vazia** | Tudo (metadados zerados) |
| `putdata(pixels)` | Preenche com pixels originais | - |
| `save()` | Sobrescreve arquivo | Metadados não vão no novo arquivo |

**Por que não `img.save(..., exif=b'')`?**
- Pillow `save(exif=b'')` **funciona só para JPEG**.
- PNG, WebP, TIFF têm estruturas diferentes.
- **Recriar imagem** (`Image.new`) é **formato-agnóstico** - funciona para qualquer formato que Pillow leia.

**Modo preservado:** `img.mode` mantém `RGB`, `RGBA`, `L` (grayscale), `CMYK`, etc.

---

### Logging

```python
logger = logging.getLogger(__name__)  # 'core.tasks'

# Sucesso
logger.info(msg)

# Erro (poderia adicionar no except)
logger.error(f"Erro processando evidencia {evidencia_id}: {e}", exc_info=True)
```

**Por que `logging` e não `print`?**
- `print` vai para stdout (logs Docker) - **não estruturado**.
- `logging`:
  - Níveis (DEBUG, INFO, WARNING, ERROR)
  - Formato configurável (JSON, syslog, file)
  - Integra com ELK/Loki/Datadog
  - `exc_info=True` inclui stack trace

---

## 🔗 Como é Chamada (core/views.py)

```python
# core/views.py
from .tasks import limpar_exif_imagem

def index(request):
    if request.method == 'POST':
        # ... salva denuncia ...
        for f in request.FILES.getlist('imagem'):
            evidencia = Evidencia(denuncia=denuncia, imagem=f)
            evidencia.save()
            # ENQUEUE ASYNC - não bloqueia response
            limpar_exif_imagem.delay(evidencia.id)
```

**`delay()` vs `apply_async()`:**
| Método | Uso |
|--------|-----|
| `.delay(arg1, arg2)` | Simples, args posicionais |
| `.apply_async(args=[], kwargs={}, countdown=60, queue='images')` | Controle total |

**O que acontece:**
```
View (Web)                           Redis Broker                    Worker
    │                                    │                              │
    ├─ limpar_exif_imagem.delay(42) ────▶│                              │
    │   (serializa: {"args":[42]})      │                              │
    │                                    ├─ LPUSH 'celery' ────────────▶│
    │                                    │                              ├─ BRPOP
    │                                    │                              ├─ Deserializa
    │                                    │                              ├─ Executa task
    │                                    │                              ├─ SET result
    │                                    │◀─────────────────────────────┤
    │                                    │                              │
    │   Retorna HTTP 302 (protocolo)    │                              │
    │   (NÃO ESPERA task terminar)      │                              │
```

---

## ⚙️ Configurações de Task (Opcional)

```python
@shared_task(
    bind=True,                    # self = Task instance (retry, request)
    autoretry_for=(Exception,),  # Retry automático em exceção
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,           # Exponential backoff: 1s, 2s, 4s...
    retry_backoff_max=600,        # Max 10 min
    retry_jitter=True,            # Aleatoriza para não thundering herd
    acks_late=True,               # Override global
    reject_on_worker_lost=True,   # Override global
)
def limpar_exif_imagem(self, evidencia_id):
    ...
```

**Quando usar retry:**
- Falha transitória (Redis caiu momentaneamente, disco cheio temporário).
- **Não usar** para `DoesNotExist` (não vai resolver sozinho).

---

## 📊 Monitoramento no Flower

```
Task: core.tasks.limpar_exif_imagem
├─ Args: [42]
├─ Status: SUCCESS
├─ Result: "SUCESSO: EXIF limpo para evidência #42"
├─ Started: 2026-07-28 10:30:15.123
├─ Succeeded: 2026-07-28 10:30:15.456
├─ Runtime: 0.333s
├─ Worker: celery@worker1
└─ Queue: celery
```

---

## 📚 Referências
- [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [shared_task](https://docs.celeryq.dev/en/stable/userguide/tasks.html#shared-tasks)
- [Pillow Image Module](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [EXIF Security](https://owasp.org/www-community/vulnerabilities/EXIF_Data_Leakage)