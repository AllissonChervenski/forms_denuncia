from django.conf import settings
from django.conf.urls.static import static
from django import forms
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name="index"),
    path('protocolo/<uuid:protocolo>/', views.protocolo, name="protocolo"),
    path('cidades-autocomplete/', views.CidadesAutocomplete.as_view(), name='cidades-autocomplete'),
    path('pesquisar/', views.pesquisar, name='pesquisar')
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
 
 