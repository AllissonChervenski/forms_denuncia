"""Configurações globais e fixtures para pytest."""
import unicodedata
import pytest
from django.db.backends.signals import connection_created
from django.dispatch import receiver


def unaccent_func(text):
    """Remove acentuação para simular a extensão unaccent do PostgreSQL no SQLite."""
    if text is None:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    )


def _trigrams(text):
    """Gera o conjunto de trigramas com padding conforme o pg_trgm do PostgreSQL."""
    if not text:
        return set()
    s = f"  {text} "
    return set(s[i:i+3] for i in range(len(s) - 2))


def similarity_func(text1, text2):
    """Calcula a similaridade trigram entre dois textos (0.0 a 1.0)."""
    if text1 is None or text2 is None:
        return 0.0
    t1 = _trigrams(str(text1).lower())
    t2 = _trigrams(str(text2).lower())
    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0
    intersection = len(t1.intersection(t2))
    union = len(t1.union(t2))
    return float(intersection) / float(union) if union else 0.0


@receiver(connection_created)
def extend_sqlite_functions(sender, connection, **kwargs):
    """Registra funções customizadas UNACCENT e SIMILARITY para SQLite."""
    if connection.vendor == 'sqlite':
        connection.connection.create_function('UNACCENT', 1, unaccent_func)
        connection.connection.create_function('SIMILARITY', 2, similarity_func)
