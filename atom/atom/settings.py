"""Настройки проекта."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Флаг для отслеживания первой загрузки
if not os.environ.get("SETTINGS_LOADED"):
    # Проверяем CI окружение
    if os.getenv("DJANGO_ENV") == "ci":
        env_file = BASE_DIR / ".env.ci"
        print("Используются настройки CI")
    else:
        # Пробуем загрузить .env.dev, если не найден - используем .env.prod
        env_dev = BASE_DIR / ".env.dev"
        env_prod = BASE_DIR / ".env.prod"

        if env_dev.exists():
            env_file = env_dev
            print("Используются настройки разработки (.env.dev)")
        elif env_prod.exists():
            env_file = env_prod
            print("Используются производственные настройки (.env.prod)")
        else:
            raise FileNotFoundError(
                "Не найдены файлы настроек. Необходим .env.dev или .env.prod. "
                "Пожалуйста, создайте один из файлов на основе .env.example"
            )

    # Загружаем переменные окружения из выбранного файла
    load_dotenv(env_file)

    # Устанавливаем флаг, что настройки уже загружены
    os.environ["SETTINGS_LOADED"] = "True"

# Проверяем обязательные переменные окружения
required_env_vars = [
    "SECRET_KEY",
    "DEBUG",
    "ALLOWED_HOSTS",
    "DB_ENGINE",
    "DB_NAME",
]

missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_env_vars:
    raise ValueError(
        f"Отсутствуют обязательные переменные окружения: {', '.join(missing_env_vars)}"
    )

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Приложения
    "user.apps.UserConfig",
    "balance.apps.BalanceConfig",
    "order.apps.OrderConfig",
    "status.apps.StatusConfig",
    "package.apps.PackageConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Пользовательская модель
AUTH_USER_MODEL = "user.User"

ROOT_URLCONF = "atom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "atom.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = os.getenv("STATIC_URL", "static/")
MEDIA_URL = os.getenv("MEDIA_URL", "media/")

STATIC_ROOT = os.getenv("STATIC_ROOT", BASE_DIR / "static")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", BASE_DIR / "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# API settings
API_VERSION = os.getenv("API_VERSION", "v1")

# Security settings
if not DEBUG:
    # Настройки безопасности только для продакшена
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True") == "True"
    )
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True") == "True"

    # Настройки сессий и CSRF для продакшена
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True") == "True"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True") == "True"
else:
    # Настройки для разработки и тестов
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Общие настройки CSRF (для всех окружений)
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_USE_SESSIONS = os.getenv("CSRF_USE_SESSIONS", "False") == "True"
CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "False") == "True"

# Настройки для whitenoise
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
