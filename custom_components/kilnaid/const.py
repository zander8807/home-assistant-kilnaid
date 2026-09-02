"""Constants for the KilnAid integration."""

from datetime import timedelta

DOMAIN = "kilnaid"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=45)

LOGIN_URL = "https://bartinst-user-service-prod.herokuapp.com/login"
API_URL = "https://kiln.bartinst.com"

CLIENT_HEADERS = {
    "Content-Type": "application/json",
    "kaid-version": "kaid-plus",
    "x-app-name-token": "kiln-aid",
}
