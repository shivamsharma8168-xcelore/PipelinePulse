import os


def required_env(name):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"{name} environment variable is required.")
    return value


def optional_env(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value


def env_bool(name, default):
    value = optional_env(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    return int(optional_env(name, default))


def env_list(name):
    raw_value = os.environ.get(name)
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


class Config:
    SQLALCHEMY_DATABASE_URI = required_env("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = required_env("SECRET_KEY")
    REDIS_URL = (os.environ.get("REDIS_URL") or str()).strip()

    FRONTEND_ORIGINS = env_list("FRONTEND_ORIGINS")
    PRICING_CACHE_TTL_SECONDS = env_int("PRICING_CACHE_TTL_SECONDS", "21600")
    CARBON_CACHE_TTL_SECONDS = env_int("CARBON_CACHE_TTL_SECONDS", "86400")
    ENABLE_LIVE_PRICING = env_bool("ENABLE_LIVE_PRICING", "false")
    AWS_PRICING_BASE_URL = optional_env("AWS_PRICING_BASE_URL", "")
    AZURE_RETAIL_PRICES_URL = optional_env("AZURE_RETAIL_PRICES_URL", "")
    AUTO_CREATE_TABLES = env_bool("AUTO_CREATE_TABLES", "true")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", "false")
    SESSION_COOKIE_SAMESITE = optional_env("SESSION_COOKIE_SAMESITE", "Lax")
    PREFERRED_URL_SCHEME = optional_env("PREFERRED_URL_SCHEME", "http")


if Config.ENABLE_LIVE_PRICING:
    Config.AWS_PRICING_BASE_URL = required_env("AWS_PRICING_BASE_URL")
    Config.AZURE_RETAIL_PRICES_URL = required_env("AZURE_RETAIL_PRICES_URL")