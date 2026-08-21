import os
import logging
from celery import shared_task
from PIL import Image, ImageOps
from .models import Evidencia

logger = logging.getLogger(__name__)

# Dimensão máxima recomendada (largura ou altura) para exibição nítida e leve
MAX_IMAGE_DIMENSION = 1920
# Qualidade de compressão JPEG padrão (ótimo balanço entre nitidez e tamanho reduzido)
JPEG_QUALITY = 82

@shared_task
def limpar_exif_imagem(evidencia_id):
    """
    Recebe o ID de uma evidência recém-salva, abre a imagem em background:
    1. Corrige orientação baseada em EXIF (se existir) antes de descartar metadados.
    2. Remove 100% dos metadados (EXIF/GPS/Pessoais) gerando nova imagem limpa.
    3. Redimensiona proporcionalmente caso a imagem exceda 1920px (LANCZOS).
    4. Aplica compressão otimizada (JPEG quality=82 / PNG optimize=True) para economizar disco e banda.
    """
    try:
        evidencia = Evidencia.objects.get(id=evidencia_id)
        caminho_imagem = evidencia.imagem.path

        if not os.path.exists(caminho_imagem):
            return f"Erro: Arquivo {caminho_imagem} não encontrado no disco."

        tamanho_original = os.path.getsize(caminho_imagem)

        with Image.open(caminho_imagem) as img:
            # Corrige rotação física com base na tag de orientação EXIF antes de removê-la
            img = ImageOps.exif_transpose(img) or img

            # Identifica o formato pelo arquivo ou pelo cabeçalho
            ext = os.path.splitext(caminho_imagem)[1].lower()
            if ext in ('.jpg', '.jpeg'):
                formato = 'JPEG'
            elif ext == '.png':
                formato = 'PNG'
            elif ext == '.webp':
                formato = 'WEBP'
            else:
                formato = (img.format or 'JPEG').upper()

            # Redimensionamento proporcional se ultrapassar a dimensão máxima
            if max(img.width, img.height) > MAX_IMAGE_DIMENSION:
                resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
                img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), resample_filter)

            # Garante modo de cor compatível
            modo = img.mode
            if formato in ('JPEG', 'JPG'):
                if modo not in ('RGB', 'L'):
                    img = img.convert('RGB')
                    modo = 'RGB'
            elif formato == 'PNG':
                if modo not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
                    img = img.convert('RGBA')
                    modo = 'RGBA'

            # Cria nova imagem pura para eliminar metadados e bytes extras
            imagem_limpa = Image.new(modo, img.size)
            imagem_limpa.paste(img)

            # Salva aplicando compressão otimizada de acordo com o formato
            if formato in ('JPEG', 'JPG'):
                imagem_limpa.save(
                    caminho_imagem,
                    format='JPEG',
                    quality=JPEG_QUALITY,
                    optimize=True,
                    progressive=True
                )
            elif formato == 'PNG':
                imagem_limpa.save(
                    caminho_imagem,
                    format='PNG',
                    optimize=True
                )
            elif formato == 'WEBP':
                imagem_limpa.save(
                    caminho_imagem,
                    format='WEBP',
                    quality=JPEG_QUALITY,
                    method=6
                )
            else:
                imagem_limpa.save(caminho_imagem, format=formato, optimize=True)

        tamanho_final = os.path.getsize(caminho_imagem)
        economia = ((tamanho_original - tamanho_final) / tamanho_original * 100) if tamanho_original > 0 else 0

        msg = (
            f"SUCESSO: EXIF limpo e imagem comprimida para evidência #{evidencia_id} "
            f"({tamanho_original / 1024:.1f} KB -> {tamanho_final / 1024:.1f} KB, economia: {economia:.1f}%)"
        )
        logger.info(msg)
        return msg

    except Evidencia.DoesNotExist:
        return f"Erro: Evidência #{evidencia_id} não encontrada."
    except Exception as e:
        logger.error(f"Erro ao processar imagem para evidência #{evidencia_id}: {e}")
        return f"Erro ao processar imagem: {str(e)}"

# Alias semântico para a mesma tarefa
limpar_e_comprimir_imagem = limpar_exif_imagem
