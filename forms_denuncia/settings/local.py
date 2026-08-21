from .base import *

# Development settings
DEBUG = config('DEBUG', default=True, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())
