import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

# Onde moram os arquivos de schema — os .json que descrevem o formato
# que cada requisicao precisa ter. Quem le essa pasta e o
# src/utils/schema_handler.py.
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

# A API de boletos: o serviço de fora que este projeto chama pra emitir
# uma cobrança (veja src/connectors/). O endereço vem do ambiente, como
# tudo aqui — na sua máquina ele aponta pro mock server do sábado 4; em
# produção, apontaria pro serviço de verdade. O código não sabe a
# diferença, e esse é o ponto.
BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_INTERNAL_TOKEN = os.environ.get("BANKSLIP_API_INTERNAL_TOKEN", "default_token")

# Quantos segundos esperar pelo serviço de boletos antes de desistir.
# Todo connector TEM um timeout — o porquê está em
# src/connectors/rest_connector.py.
BANKSLIP_API_TIMEOUT = int(os.environ.get("BANKSLIP_API_TIMEOUT", "5"))

# Rotas públicas: não exigem o header INTERNAL-TOKEN. São as duas que
# precisam responder pra quem ainda não tem token nenhum: a raiz, que
# diz quem é este serviço, e o health check, que o Docker consulta pra
# saber se a API já está de pé.
BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

RULE_SET_VERSION = "2026.10.17-f2"

RULE_DESTINATION_MIN_AGE_DAYS = int(os.environ.get("RULE_DESTINATION_MIN_AGE_DAYS", "30"))
RULE_DESTINATION_CRITICAL_AGE_DAYS = int(os.environ.get("RULE_DESTINATION_CRITICAL_AGE_DAYS", "3"))
RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS = int(os.environ.get("RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS", "100000"))
RULE_VELOCITY_WINDOW_MINUTES = int(os.environ.get("RULE_VELOCITY_WINDOW_MINUTES", "10"))
RULE_VELOCITY_2FA_COUNT = int(os.environ.get("RULE_VELOCITY_2FA_COUNT", "5"))
RULE_VELOCITY_REJECT_COUNT = int(os.environ.get("RULE_VELOCITY_REJECT_COUNT", "10"))
RULE_AMOUNT_DAILY_SUM_CENTS = int(os.environ.get("RULE_AMOUNT_DAILY_SUM_CENTS", "1000000"))
RULE_AMOUNT_DAILY_SUM_PJ_CENTS = int(os.environ.get("RULE_AMOUNT_DAILY_SUM_PJ_CENTS", "5000000"))
RULE_NIGHT_START_HOUR = int(os.environ.get("RULE_NIGHT_START_HOUR", "20"))
RULE_NIGHT_END_HOUR = int(os.environ.get("RULE_NIGHT_END_HOUR", "6"))
RULE_LIMIT_NIGHT_AMOUNT_CENTS = int(os.environ.get("RULE_LIMIT_NIGHT_AMOUNT_CENTS", "100000"))
RULE_LIMIT_SINGLE_AMOUNT_CENTS = int(os.environ.get("RULE_LIMIT_SINGLE_AMOUNT_CENTS", "5000000"))
RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS = int(os.environ.get("RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS", "20000000"))
RULE_DEVICE_MAX_SOURCES_24H = int(os.environ.get("RULE_DEVICE_MAX_SOURCES_24H", "3"))
RULE_DESTINATION_MAX_SOURCES_1H = int(os.environ.get("RULE_DESTINATION_MAX_SOURCES_1H", "10"))
RULE_NEW_DEVICE_MIN_AMOUNT_CENTS = int(os.environ.get("RULE_NEW_DEVICE_MIN_AMOUNT_CENTS", "50000"))
RULE_SOURCE_MIN_AGE_DAYS = int(os.environ.get("RULE_SOURCE_MIN_AGE_DAYS", "7"))
RULE_SOURCE_NEW_MAX_AMOUNT_CENTS = int(os.environ.get("RULE_SOURCE_NEW_MAX_AMOUNT_CENTS", "200000"))
RULE_FIRST_TIME_MIN_AMOUNT_CENTS = int(os.environ.get("RULE_FIRST_TIME_MIN_AMOUNT_CENTS", "300000"))

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}. "
            "Rodando com 'docker compose up' elas já vêm preenchidas. "
            "Fora do Docker, copie o .env.example para .env."
        )
