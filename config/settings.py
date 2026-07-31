"""
Django settings for the "Meu Artigo" project.

Configuração carregada de variáveis de ambiente (.env). Ver .env.example.
Docs: https://docs.djangoproject.com/en/5.2/topics/settings/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis do arquivo .env (chaves de API, banco, etc.)
load_dotenv(BASE_DIR / ".env")


def env(key: str, default=None):
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Segurança / básico
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]


# ---------------------------------------------------------------------------
# Aplicações
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.articles",
    "apps.llm",
    "apps.memory",
    "apps.workspace",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve estáticos em produção
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Banco de dados — PostgreSQL + pgvector
# ---------------------------------------------------------------------------
# Produção (Railway etc.) fornece DATABASE_URL; local usa POSTGRES_*.
if env("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(env("DATABASE_URL"), conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "meu_artigo"),
            "USER": env("POSTGRES_USER", ""),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }


# ---------------------------------------------------------------------------
# Validação de senha
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("DJANGO_TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Arquivos estáticos
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Armazenamento híbrido — pastas físicas dos artigos
# ---------------------------------------------------------------------------
# Cada artigo vive em artigos/<area-slug>/<assunto-slug>/ (ver PROJETO.md §6).
ARTIGOS_ROOT = Path(env("ARTIGOS_ROOT", BASE_DIR / "artigos"))


# ---------------------------------------------------------------------------
# LLMs / embeddings — chaves lidas do .env, consumidas via apps.llm.providers
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", "claude-opus-5")
# Roteamento de modelo por papel (mockup: Arquiteto=Opus, Redator=Sonnet, Editor=Opus).
MODELO_ARQUITETO = env("MODELO_ARQUITETO", "claude-opus-5")
MODELO_REDATOR = env("MODELO_REDATOR", "claude-sonnet-5")
MODELO_EDITOR = env("MODELO_EDITOR", "claude-opus-5")
MODELO_REVISOR = env("MODELO_REVISOR", "claude-haiku-4-5")  # avisos de estilo/margem
# Câmbio para exibir custo em R$ (aprox.; ajuste conforme necessário).
USD_BRL = float(env("USD_BRL", "5.40"))
PERPLEXITY_API_KEY = env("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = env("PERPLEXITY_MODEL", "sonar")  # sonar | sonar-pro | sonar-reasoning

# Embeddings — Voyage AI (parceiro recomendado pela Anthropic). Ver PROJETO.md §5/§11.
VOYAGE_API_KEY = env("VOYAGE_API_KEY", "")
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", "voyage")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "voyage-3.5")
EMBEDDING_DIMENSIONS = int(env("EMBEDDING_DIMENSIONS", "1024"))


# ---------------------------------------------------------------------------
# Segurança em produção — aplicada só quando DEBUG=False
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
    ]
