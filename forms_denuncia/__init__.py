from .celery import app as celery_app

#garante que o celery inicie junto ao django
__all__ = ('celery_app')