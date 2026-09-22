"""Constantes de l'intégration Aldes InspirAIR Top (Modbus TCP)."""

DOMAIN = "aldes_inspirair"

CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_HOST = "192.168.0.213"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 2
DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600

# Code installateur : sans lui, une partie des registres renvoie -1.
UNLOCK_REGISTER = 16
UNLOCK_CODE = 34102

# Blocs lus à chaque rafraîchissement (adresse de départ, nombre de registres).
READ_BLOCKS = ((12, 1), (256, 44), (320, 39), (378, 7))

REG_SOFTWARE = 12
REG_SPEED = 257
REG_BYPASS_MODE = 259
REG_FILTER_MONTHS = 267
REG_BALANCE = 278
REG_MOTOR_CMD_1 = 320
REG_MOTOR_CMD_2 = 321
REG_FILTER_STATE = 346
REG_FILTER_DAYS = 347
REG_BYPASS_POSITION = 348
REG_T_OUTDOOR = 350
REG_T_EXTRACT = 351
REG_T_EXHAUST = 352
REG_T_SUPPLY = 353
REG_MOTOR_RPM_1 = 354
REG_MOTOR_RPM_2 = 355
REG_FLOW_EXTRACT = 356
REG_FLOW_SUPPLY = 357
REG_ERROR = 384

# Les valeurs sont des clés de traduction (strings.json).
SPEEDS = {0: "vacances", 1: "quotidien", 2: "cuisine", 3: "boost"}

BYPASS_MODES = {
    0: "desactive",
    1: "automatique",
    2: "optimisation_hiver",
    3: "optimisation_ete",
    4: "ouvert",
}

BYPASS_POSITIONS = {
    0: "ferme",
    1: "ouvert",
    2: "fermeture",
    3: "ouverture",
    4: "court_circuit",
    5: "circuit_ouvert",
    6: "sous_alimentation",
}

# Codes de la notice d'installation InspirAIR Top, §7.4 (libellés dans strings.json).
ERROR_CODES = (0, 49, 50, 53, 70, 72, 74, 76, 81, 83, 84, 85, 90, 91, 92, 182, 183, 239, 240, 241, 243, 251)
ERROR_UNKNOWN = "inconnue"


def error_key(code: int) -> str:
    """Clé de traduction d'un code erreur."""
    if code == 0:
        return "aucune"
    return f"e{code}" if code in ERROR_CODES else ERROR_UNKNOWN
