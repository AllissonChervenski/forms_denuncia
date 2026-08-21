from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from core import models
from django.http import HttpResponse, HttpResponseNotAllowed

# Create your views here.

@login_required
def index(request):
    lista = models.Denuncia.objects.all().order_by('-created_at')
    paginator = Paginator(lista, 10)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/index.html',  { 
        'lista': lista,
        'page_obj': page_obj,
    })

def protocolo(request, protocolo):
    lista = models.Denuncia.objects.all()
    if request.method == 'GET':
  # Extrai o UUID da URL, se for uma URL completa
        match = request.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', query)
        if match:
            protocolo_uuid = match.group(1)
            return redirect('core:protocolo', protocolo=protocolo_uuid)
            # Se não for uma URL, assume que a query já é o protocolo (ou vai dar 404, o que é ok)
        return redirect('core:protocolo',protocolo=protocolo)
    else:
        return render(request, 'dashboard/index.html', {
        })
    