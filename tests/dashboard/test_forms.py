"""Testes para os formulários do aplicativo dashboard."""
import pytest
from django.contrib.auth.models import User
from dashboard.forms import LoginForm

@pytest.fixture
def user(db):
    """Fixture para criar um usuário padrão para os testes de login."""
    return User.objects.create_user(username='testuser', password='testpass123')

@pytest.mark.django_db
def test_login_form_valido(user):
    """Testa se o formulário de login é válido com credenciais corretas."""
    form_data = {'username': 'testuser', 'password': 'testpass123'}
    form = LoginForm(data=form_data)
    assert form.is_valid()

@pytest.mark.django_db
@pytest.mark.parametrize("username, password", [
    ('usuario_errado', 'testpass123'),  # Usuário incorreto
    ('testuser', 'senha_errada'),      # Senha incorreta
])
def test_login_form_invalido(user, username, password):
    """Testa se o formulário de login é inválido para várias credenciais incorretas."""
    form_data = {'username': username, 'password': password}
    form = LoginForm(data=form_data)
    assert not form.is_valid()

@pytest.mark.django_db
def test_login_form_vazio():
    """Testa se o formulário de login é inválido quando enviado vazio."""
    form = LoginForm(data={})
    assert not form.is_valid()
    assert 'username' in form.errors
    assert 'password' in form.errors
