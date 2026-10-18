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

RULE_SET_VERSION = "2026.10.18-pixsim"

RULE_MODEL_DIR = os.environ.get("RULE_MODEL_DIR", os.path.join(SERVICE_ROOT, "rules", "model"))
# Models trained offline for the cold path (GraphSAGE, HMM); the hot path only reads their thresholds.
WORKER_MODEL_DIR = os.environ.get("WORKER_MODEL_DIR", os.path.join(SERVICE_ROOT, "worker", "model"))

RULE_DESTINATION_MIN_AGE_DAYS = int(os.environ.get("RULE_DESTINATION_MIN_AGE_DAYS", "30"))
RULE_DESTINATION_CRITICAL_AGE_DAYS = int(os.environ.get("RULE_DESTINATION_CRITICAL_AGE_DAYS", "3"))
RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS = int(os.environ.get("RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS", "100000"))
RULE_VELOCITY_WINDOW_MINUTES = int(os.environ.get("RULE_VELOCITY_WINDOW_MINUTES", "10"))
RULE_VELOCITY_2FA_COUNT = int(os.environ.get("RULE_VELOCITY_2FA_COUNT", "5"))
RULE_VELOCITY_REJECT_COUNT = int(os.environ.get("RULE_VELOCITY_REJECT_COUNT", "10"))
RULE_AMOUNT_DAILY_SUM_CENTS = int(os.environ.get("RULE_AMOUNT_DAILY_SUM_CENTS", "4500000"))
RULE_AMOUNT_DAILY_SUM_PJ_CENTS = int(os.environ.get("RULE_AMOUNT_DAILY_SUM_PJ_CENTS", "5000000"))
RULE_NIGHT_START_HOUR = int(os.environ.get("RULE_NIGHT_START_HOUR", "20"))
RULE_NIGHT_END_HOUR = int(os.environ.get("RULE_NIGHT_END_HOUR", "6"))
RULE_LIMIT_NIGHT_AMOUNT_CENTS = int(os.environ.get("RULE_LIMIT_NIGHT_AMOUNT_CENTS", "100000"))
RULE_LIMIT_SINGLE_AMOUNT_CENTS = int(os.environ.get("RULE_LIMIT_SINGLE_AMOUNT_CENTS", "5000000"))
RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS = int(os.environ.get("RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS", "20000000"))
RULE_DEVICE_MAX_SOURCES_24H = int(os.environ.get("RULE_DEVICE_MAX_SOURCES_24H", "3"))
RULE_DESTINATION_MAX_SOURCES_1H = int(os.environ.get("RULE_DESTINATION_MAX_SOURCES_1H", "10"))
RULE_NEW_DEVICE_MIN_AMOUNT_CENTS = int(os.environ.get("RULE_NEW_DEVICE_MIN_AMOUNT_CENTS", "20000"))
RULE_SOURCE_MIN_AGE_DAYS = int(os.environ.get("RULE_SOURCE_MIN_AGE_DAYS", "7"))
RULE_SOURCE_NEW_MAX_AMOUNT_CENTS = int(os.environ.get("RULE_SOURCE_NEW_MAX_AMOUNT_CENTS", "200000"))
RULE_FIRST_TIME_MIN_AMOUNT_CENTS = int(os.environ.get("RULE_FIRST_TIME_MIN_AMOUNT_CENTS", "100000"))
RULE_PROFILE_LOOKBACK_DAYS = int(os.environ.get("RULE_PROFILE_LOOKBACK_DAYS", "30"))
RULE_PROFILE_MIN_HISTORY = int(os.environ.get("RULE_PROFILE_MIN_HISTORY", "5"))
RULE_PROFILE_MIN_SCALE_PERCENT = int(os.environ.get("RULE_PROFILE_MIN_SCALE_PERCENT", "25"))
RULE_PROFILE_Z_2FA_TENTHS = int(os.environ.get("RULE_PROFILE_Z_2FA_TENTHS", "45"))
RULE_POISSON_WINDOW_MINUTES = int(os.environ.get("RULE_POISSON_WINDOW_MINUTES", "60"))
RULE_POISSON_LOOKBACK_DAYS = int(os.environ.get("RULE_POISSON_LOOKBACK_DAYS", "30"))
RULE_POISSON_PRIOR_SHAPE = int(os.environ.get("RULE_POISSON_PRIOR_SHAPE", "1"))
RULE_POISSON_PRIOR_RATE_HOURS = int(os.environ.get("RULE_POISSON_PRIOR_RATE_HOURS", "24"))
RULE_POISSON_TAIL_PPM = int(os.environ.get("RULE_POISSON_TAIL_PPM", "30"))
RULE_POISSON_MIN_EXPOSURE_HOURS = int(os.environ.get("RULE_POISSON_MIN_EXPOSURE_HOURS", "24"))
RULE_GEO_MIN_DISTANCE_KM = int(os.environ.get("RULE_GEO_MIN_DISTANCE_KM", "50"))
RULE_GEO_MAX_SPEED_KMH = int(os.environ.get("RULE_GEO_MAX_SPEED_KMH", "900"))
RULE_ATO_Z_TENTHS = int(os.environ.get("RULE_ATO_Z_TENTHS", "30"))
RULE_MULE_MIN_SOURCES_1H = int(os.environ.get("RULE_MULE_MIN_SOURCES_1H", "5"))
RULE_SPLITTING_MAX_AMOUNT_CENTS = int(os.environ.get("RULE_SPLITTING_MAX_AMOUNT_CENTS", "200000"))
RULE_SPLITTING_MIN_COUNT = int(os.environ.get("RULE_SPLITTING_MIN_COUNT", "6"))
RULE_SPLITTING_MIN_DESTINATIONS = int(os.environ.get("RULE_SPLITTING_MIN_DESTINATIONS", "4"))
RULE_SPLITTING_MIN_SUM_CENTS = int(os.environ.get("RULE_SPLITTING_MIN_SUM_CENTS", "1500000"))
RULE_FLAGGED_WINDOW_DAYS = int(os.environ.get("RULE_FLAGGED_WINDOW_DAYS", "7"))
RULE_GRAPH_RISK_MAX_AGE_MINUTES = int(os.environ.get("RULE_GRAPH_RISK_MAX_AGE_MINUTES", "120"))
RULE_GRAPH_RISK_2FA_PERMILLE = int(os.environ.get("RULE_GRAPH_RISK_2FA_PERMILLE", "600"))
RULE_GRAPH_RISK_REJECT_PERMILLE = int(os.environ.get("RULE_GRAPH_RISK_REJECT_PERMILLE", "900"))

WORKER_ENABLED = os.environ.get("WORKER_ENABLED", "true").lower() not in ("false", "0", "no")
WORKER_INTERVAL_SECONDS = int(os.environ.get("WORKER_INTERVAL_SECONDS", "30"))
WORKER_LOOKBACK_HOURS = int(os.environ.get("WORKER_LOOKBACK_HOURS", "72"))
WORKER_SEQUENCE_HISTORY_DAYS = int(os.environ.get("WORKER_SEQUENCE_HISTORY_DAYS", "30"))

# Fixed weights of the untrained graph score: logit = BIAS + sum(weight * term). Terms in worker/scoring.py.
GRAPH_RISK_MODEL = "graph_sql"
GRAPHSAGE_MODEL = "graphsage"
HMM_MODEL = "hmm"
GRAPH_RISK_BIAS = -4.0
GRAPH_RISK_W_PAYERS = 1.2
GRAPH_RISK_W_DISPERSION = 1.5
GRAPH_RISK_W_TWO_HOP = 1.0
GRAPH_RISK_W_AMOUNT = 0.3
GRAPH_RISK_W_NEW_ACCOUNT = 1.0
GRAPH_RISK_NEW_ACCOUNT_DAYS = 30
GRAPH_RISK_AMOUNT_UNIT_CENTS = 100000
GRAPH_RISK_DISPERSION_WINDOW_HOURS = 6
GRAPH_RISK_TWO_HOP_WINDOW_DAYS = 7
GRAPH_RISK_INFLOW_WINDOW_HOURS = 24

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
