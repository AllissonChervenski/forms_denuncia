from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.postgres.search import TrigramSimilarity
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from django_ratelimit.core import get_usage
from .models import Denuncia, Cidades, Evidencia
from .forms import NewDenunciaForm, CloseDenunciaForm, UploadEvidencias
from dal import autocomplete
from django.utils.html import format_html
from .tasks import limpar_exif_imagem
from django.db.models.functions import Cast
from django.db.models import TextField
from django.contrib.postgres.lookups import Unaccent
from django.db.models import Value, Q

# Custom rate limited error view
@require_http_methods(["GET", "POST"])
def ratelimited_error(request, exception=None):
    """View shown when rate limit is exceeded"""
    return HttpResponse(
        'Muitas requisições. Por favor, aguarde um momento e tente novamente.',
        status=429,
        content_type='text/plain; charset=utf-8'
    )


class CidadesAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        qs = Cidades.objects.select_related('estado').all().order_by('nome')
        if self.q:
            q_clean = self.q.strip()
            if q_clean:
                try:
                    qs_trgm = qs.annotate(
                        similarity=TrigramSimilarity(Unaccent('nome'), Unaccent(Value(q_clean)))
                    ).filter(similarity__gt=0.2).order_by('-similarity')
                    
                    if qs_trgm.exists():
                        return qs_trgm
                except Exception:
                    pass

                return qs.filter(
                    Q(nome__icontains=q_clean) |
                    Q(estado__uf__iexact=q_clean)
                ).order_by('nome')

        return qs

    def get_result_label(self, item):
        return f"{item.nome}, {item.estado}"


import logging
logger = logging.getLogger(__name__)

# Rate limit: 30 requests per minute per IP for GET, 10 submissions per minute for POST
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
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
                try:
                    limpar_exif_imagem.delay(evidencia.id)
                except Exception as exc:
                    logger.warning(f"Celery broker indisponivel, executando compressao de imagem de forma sincrona: {exc}")
                    try:
                        limpar_exif_imagem(evidencia.id)
                    except Exception as inner_exc:
                        logger.error(f"Erro ao processar imagem da evidencia {evidencia.id}: {inner_exc}")

            return redirect('core:protocolo', protocolo=denuncia.protocolo)
    else:
        form = NewDenunciaForm()
        files = UploadEvidencias()
    return render(request, 'core/index.html', {
        'form': form,
        'files': files,
        'title': 'Nova Denuncia',
    })


# Rate limit: 60 requests per minute per IP for protocol view
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def protocolo(request, protocolo):
    denuncia = Denuncia.objects.filter(protocolo=protocolo).first()
    usuario_autenticado = request.user.is_authenticated
    base_template = 'core/base.html'
    evidencia = Evidencia.objects.filter(denuncia=denuncia)

    if request.method == 'POST':
        if not usuario_autenticado:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)

        form = CloseDenunciaForm(request.POST, instance=denuncia)
        action = request.POST.get('action')

        if action == 'reopen':
            denuncia.situacao = True
            denuncia.save()
            return redirect('core:protocolo', protocolo=denuncia.protocolo)

        if form.is_valid():
            # Salva a resposta (se houver) para as ações 'save' e 'close'
            if action in ['save', 'close']:
                form.save()

            # Fecha a denúncia apenas se o botão "Fechar" foi clicado
            if action == 'close':
                denuncia.situacao = False
                denuncia.save()
            
            # Redireciona para a mesma página para ver a atualização
            return redirect('core:protocolo', protocolo=denuncia.protocolo)

    else:
        form = CloseDenunciaForm(instance=denuncia)

    if usuario_autenticado:
        base_template = 'dashboard/base.html'
    return render(request, 'core/protocolo.html', {
        'denuncia': denuncia,
        'evidencia': evidencia,
        'base': base_template,
        'closeForm': form
    })


import re

# Rate limit: 60 requests per minute per IP for search
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
def pesquisar(request):
    query = request.GET.get('query', '')

    if query:
        # Extrai o UUID da URL, se for uma URL completa
        match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', query, re.IGNORECASE)
        if match:
            protocolo_uuid = match.group(1)
            return redirect('core:protocolo', protocolo=protocolo_uuid)

    return render(request, 'core/pesquisar.html', {
        'query': query,
    })