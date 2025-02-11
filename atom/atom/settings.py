"""Настройки проекта ATOM.

Этот модуль содержит все настройки Django проекта, включая:
- Базовые настройки Django
- Настройки безопасности
- Настройки базы данных
- Настройки статических файлов
- Настройки кэширования
- Настройки логирования
"""

import os
from pathlib import Path
import sys

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Базовые настройки
# -----------------------------------------------------------------------------

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка переменных окружения
if not os.environ.get("SETTINGS_LOADED"):
    # Проверяем CI окружение
    if os.getenv("DJANGO_ENV") == "ci":
        # В CI используем переменные окружения напрямую
        os.environ["SETTINGS_LOADED"] = "True"
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

# -----------------------------------------------------------------------------
# Проверка обязательных переменных
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Основные настройки Django
# -----------------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

# -----------------------------------------------------------------------------
# Приложения
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Основные настройки URL и шаблонов
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "user.User"
ROOT_URLCONF = "atom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
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

# -----------------------------------------------------------------------------
# База данных
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Валидация паролей
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Интернационализация
# -----------------------------------------------------------------------------

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Статические файлы
# -----------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
MEDIA_URL = os.getenv("MEDIA_URL", "media/")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", BASE_DIR / "media")

# -----------------------------------------------------------------------------
# Прочие настройки Django
# -----------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
API_VERSION = os.getenv("API_VERSION", "v1")

# -----------------------------------------------------------------------------
# Настройки безопасности
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Настройки статических файлов
# -----------------------------------------------------------------------------

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# -----------------------------------------------------------------------------
# Настройки для тестов
# -----------------------------------------------------------------------------

if "pytest" in sys.argv[0]:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# -----------------------------------------------------------------------------
# Настройки логирования
# -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
        "order_format": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "order_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",  # Используем RotatingFileHandler
            "filename": BASE_DIR / "logs" / "order.log",
            "formatter": "order_format",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        },
        "order_error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "order_error.log",
            "formatter": "verbose",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "order": {  # Корневой логгер для приложения order
            "handlers": ["console", "order_file", "order_error_file"],
            "level": "INFO",
            "propagate": False,  # Отключаем propagate для корневого логгера
        },
        "order.models": {
            "handlers": [],  # Убираем хендлеры, т.к. используем родительский
            "level": "INFO",
            "propagate": True,  # Используем propagate для передачи логов родителю
        },
        "order.services": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        "order.admin": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Создаем директорию для логов если её нет
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Создаем описания для лог-файлов
LOG_DESCRIPTIONS = {
    "order.log": """
# Order Application Log File
# -------------------------
# Purpose: Основной лог-файл приложения orders
# Contains:
# - Создание/обновление/удаление заказов и сайтов
# - Изменения статусов заказов
# - Массовые операции с заказами
# - Информация о бизнес-процессах
# Level: INFO и выше
""",
    "order_error.log": """
# Order Error Log File
# -------------------
# Purpose: Лог ошибок приложения orders
# Contains:
# - Критические ошибки
# - Исключения при обработке заказов
# - Ошибки валидации
# - Проблемы с транзакциями
# Level: ERROR и выше
""",
}

# Создаем файлы с описаниями если они не существуют
for log_file, description in LOG_DESCRIPTIONS.items():
    log_path = LOGS_DIR / log_file
    if not log_path.exists() or log_path.stat().st_size == 0:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(description)


DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
