"""
linky_alert.py
==============
Surveille la consommation de la veille via Conso API (conso.boris.sh).
Envoie un email d'alerte si la consommation est en-dessous d'un seuil
(disjoncteur sauté ou coupure de courant).

Supporte plusieurs comptes Enedis via le secret GitHub LINKY_ACCOUNTS.
Chaque compte peut avoir son propre seuil d'alerte et plusieurs destinataires.

Format du secret LINKY_ACCOUNTS (JSON) :
[
  {
    "name": "Maison principale",
    "token": "xxx.yyy.zzz",
    "prm": "12345678901234",
    "alert_to": ["alice@example.com", "bob@example.com"],
    "seuil_wh": 100
  },
  {
    "name": "Saint Martin",
    "token": "aaa.bbb.ccc",
    "prm": "98765432109876",
    "alert_to": ["charlie@example.com"],
    "seuil_wh": 500
  }
]

Dépendances : requests (pip install requests)
Hébergement : GitHub Actions (tâche planifiée quotidienne)
"""

import requests
import smtplib
import logging
import os
import json
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────

# Identifiants email expéditeur (communs à tous les comptes)
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587

# Seuil d'alerte par défaut en Wh (utilisé si non précisé dans le compte)
SEUIL_WH_DEFAULT = 100

# Liste des comptes à surveiller, chargée depuis le secret LINKY_ACCOUNTS
LINKY_ACCOUNTS = json.loads(os.environ.get("LINKY_ACCOUNTS", "[]"))

# ─────────────────────────────────────────────
# 📋  LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ─────────────────────────────────────────────
# 📡  FONCTIONS
# ─────────────────────────────────────────────

def get_yesterday_consumption(token: str, prm: str) -> float | None:
    """
    Interroge Conso API pour récupérer la consommation de la veille (en Wh).
    Retourne la valeur en Wh, ou None en cas d'erreur / données absentes.
    """
    yesterday = date.today() - timedelta(days=1)
    today     = date.today()

    url = "https://conso.boris.sh/api/daily_consumption"
    params = {
        "prm":   prm,
        "start": yesterday.isoformat(),
        "end":   today.isoformat(),
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Structure retournée par conso.boris.sh :
        # {"usage_point_id": "...", "interval_reading": [{"value": "14456", "date": "2026-04-14"}, ...]}
        readings = data.get("interval_reading", [])

        if not readings:
            logging.warning(f"[{prm}] Aucune donnée retournée par l'API pour hier.")
            return None

        valeur_wh = float(readings[0]["value"])
        logging.info(f"[{prm}] Consommation hier ({yesterday}) : {valeur_wh} Wh")
        return valeur_wh

    except requests.exceptions.HTTPError as e:
        logging.error(f"[{prm}] Erreur HTTP Conso API : {e} — réponse : {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"[{prm}] Erreur réseau : {e}")
    except (KeyError, ValueError, IndexError) as e:
        logging.error(f"[{prm}] Erreur de parsing de la réponse API : {e}")

    return None


def send_alert_email(name: str, prm: str, alert_to: list[str], consommation_wh: float | None, seuil_wh: int):
    """
    Envoie un email d'alerte pour un compte donné vers la liste de destinataires.
    """
    yesterday = date.today() - timedelta(days=1)

    if consommation_wh is None:
        sujet = f"⚠️ Linky [{name}] — Données indisponibles pour le {yesterday}"
        corps = (
            f"Bonjour,\n\n"
            f"Le script de surveillance n'a pas pu récupérer les données de consommation\n"
            f"pour le compteur \"{name}\" (PRM {prm}) le {yesterday}.\n\n"
            f"Cela peut indiquer un problème avec l'API ou que les données ne sont pas\n"
            f"encore disponibles. Vérifiez manuellement sur votre espace Enedis.\n\n"
            f"Cordialement,\n"
            f"Votre script Linky 🔌"
        )
    else:
        sujet = f"🚨 Linky [{name}] — Consommation anormalement basse le {yesterday} ({consommation_wh} Wh)"
        corps = (
            f"Bonjour,\n\n"
            f"⚠️ ALERTE : La consommation électrique de \"{name}\" de la veille est anormalement basse.\n\n"
            f"📅 Date         : {yesterday}\n"
            f"🏠 Compteur     : {name}\n"
            f"🔌 PRM          : {prm}\n"
            f"⚡ Consommation : {consommation_wh} Wh\n"
            f"🔻 Seuil alerte : {seuil_wh} Wh\n\n"
            f"Cela peut indiquer :\n"
            f"• Le disjoncteur principal a sauté\n"
            f"• Une coupure de courant\n"
            f"• Un problème de relevé du compteur Linky\n\n"
            f"👉 Veuillez vérifier votre installation électrique.\n\n"
            f"Cordialement,\n"
            f"Votre script Linky 🔌"
        )

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(alert_to)
    msg["Subject"] = sujet
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, alert_to, msg.as_string())
            logging.info(f"[{name}] Email d'alerte envoyé à : {alert_to}")
    except smtplib.SMTPException as e:
        logging.error(f"[{name}] Erreur envoi email : {e}")


# ─────────────────────────────────────────────
# 🚀  POINT D'ENTRÉE
# ─────────────────────────────────────────────

def main():
    logging.info("=== Début de la vérification Linky ===")

    if not LINKY_ACCOUNTS:
        logging.error("Aucun compte trouvé dans LINKY_ACCOUNTS. Vérifiez le secret GitHub.")
        return

    for account in LINKY_ACCOUNTS:
        token    = account["token"]
        prm      = account["prm"]
        alert_to = account["alert_to"]
        seuil_wh = account.get("seuil_wh", SEUIL_WH_DEFAULT)
        name     = account.get("name", prm)  # Utilise le PRM comme fallback si pas de nom

        logging.info(f"--- Vérification [{name}] PRM {prm} (seuil : {seuil_wh} Wh) ---")
        consommation = get_yesterday_consumption(token, prm)

        if consommation is None:
            logging.warning(f"[{name}] Données indisponibles — envoi d'un avertissement.")
            send_alert_email(name, prm, alert_to, None, seuil_wh)
        elif consommation <= seuil_wh:
            logging.warning(f"[{name}] {consommation} Wh <= seuil {seuil_wh} Wh — alerte envoyée.")
            send_alert_email(name, prm, alert_to, consommation, seuil_wh)
        else:
            logging.info(f"[{name}] Consommation normale ({consommation} Wh > {seuil_wh} Wh). Aucune alerte.")

    logging.info("=== Fin de la vérification Linky ===")


if __name__ == "__main__":
    main()
