"""
linky_alert.py
==============
Surveille la consommation de la veille via Conso API (conso.boris.sh).
Envoie un email d'alerte si la consommation est en-dessous d'un seuil
(disjoncteur sauté ou coupure de courant).

Dépendances : requests (pip install requests)
Hébergement : PythonAnywhere (tâche planifiée quotidienne)
"""

import requests
import smtplib
import logging
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
# ⚙️  CONFIGURATION — À REMPLIR
# ─────────────────────────────────────────────

import os

LINKY_TOKEN   = os.environ.get("LINKY_TOKEN", "xxx.yyy.zzz")
LINKY_PRM     = os.environ.get("LINKY_PRM", "12345678901234")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "mon_mot_de_passe")
SMTP_USER  = os.environ.get("SMTP_USER", "gmail")
ALERT_TO = ["rodolphe.bedel@gmail.com", "rodolphetotal@gmail.com"]



# Conso API (Boris) — https://conso.boris.sh

 
# Seuil d'alerte en Wh
# En-dessous de cette valeur = probable coupure / disjoncteur sauté
SEUIL_WH = 1000000  # 100 Wh ≈ quasi-zéro pour un logement habité
 
# Configuration email (expéditeur)
SMTP_SERVER   = "smtp.gmail.com"      # ou smtp.orange.fr, smtp.free.fr…
SMTP_PORT     = 587
SMTP_USER     = "rodolphe.bedel@gmail.com"

 
# Destinataires de l'alerte (liste)
ALERT_TO = ["rodolphe.bedel@gmail.com", "rodolphetotal@gmail.com"]
 

# ─────────────────────────────────────────────
# 📡  FONCTIONS
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def get_yesterday_consumption() -> float | None:
    """
    Interroge Conso API pour récupérer la consommation de la veille (en Wh).
    Retourne la valeur en Wh, ou None en cas d'erreur / données absentes.
    """
    yesterday = date.today() - timedelta(days=1)
    today     = date.today()

    url = "https://conso.boris.sh/api/daily_consumption"
    params = {
        "prm":   LINKY_PRM,
        "start": yesterday.isoformat(),
        "end":   today.isoformat(),   # end est exclu, donc on récupère uniquement hier
    }
    headers = {
        "Authorization": f"Bearer {LINKY_TOKEN}"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Structure réelle retournée par conso.boris.sh :
        # {"usage_point_id": "...", "interval_reading": [{"value": "14456", "date": "2026-04-14"}, ...]}
        readings = data.get("interval_reading", [])

        if not readings:
            logging.warning("Aucune donnée retournée par l'API pour hier.")
            return None

        # La valeur est en Wh (chaîne de caractères dans la réponse)
        valeur_wh = float(readings[0]["value"])
        logging.info(f"Consommation hier ({yesterday}) : {valeur_wh} Wh")
        return valeur_wh

    except requests.exceptions.HTTPError as e:
        logging.error(f"Erreur HTTP Conso API : {e} — réponse : {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur réseau : {e}")
    except (KeyError, ValueError, IndexError) as e:
        logging.error(f"Erreur de parsing de la réponse API : {e}")

    return None


def send_alert_email(consommation_wh: float | None):
    """
    Envoie un email d'alerte avec la consommation anormalement basse.
    """
    yesterday = date.today() - timedelta(days=1)

    if consommation_wh is None:
        sujet = f"⚠️ Linky — Données indisponibles pour le {yesterday}"
        corps = f"""Bonjour,

Le script de surveillance de votre compteur Linky n'a pas pu récupérer
les données de consommation pour le {yesterday}.

Cela peut indiquer un problème avec l'API ou que les données ne sont pas
encore disponibles. Vérifiez manuellement sur votre espace Enedis.

Cordialement,
Votre script Linky 🔌
"""
    else:
        sujet = f"🚨 Linky — Consommation anormalement basse le {yesterday} ({consommation_wh} Wh)"
        corps = f"""Bonjour,

⚠️ ALERTE : La consommation électrique de la veille est anormalement basse.

📅 Date       : {yesterday}
⚡ Consommation : {consommation_wh} Wh
🔻 Seuil d'alerte : {SEUIL_WH} Wh

Cela peut indiquer :
  • Le disjoncteur principal a sauté
  • Une coupure de courant chez vous
  • Un problème de relevé du compteur Linky

👉 Veuillez vérifier votre installation électrique.

Cordialement,
Votre script Linky 🔌
"""

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(ALERT_TO)
    msg["Subject"] = sujet
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, ALERT_TO, msg.as_string())
        logging.info(f"Email d'alerte envoyé à : {ALERT_TO}")
    except smtplib.SMTPException as e:
        logging.error(f"Erreur envoi email : {e}")


# ─────────────────────────────────────────────
# 🚀  POINT D'ENTRÉE
# ─────────────────────────────────────────────

def main():
    logging.info("=== Début de la vérification Linky ===")

    consommation = get_yesterday_consumption()

    if consommation is None:
        logging.warning("Données indisponibles — envoi d'un email d'avertissement.")
        send_alert_email(None)

    elif consommation <= SEUIL_WH:
        logging.warning(
            f"Consommation {consommation} Wh <= seuil {SEUIL_WH} Wh — envoi d'une alerte."
        )
        send_alert_email(consommation)

    else:
        logging.info(
            f"Consommation normale ({consommation} Wh > {SEUIL_WH} Wh). Aucune alerte."
        )

    logging.info("=== Fin de la vérification Linky ===")


if __name__ == "__main__":
    main()
