# 🔌 LinkyAlert

Surveillance automatique de votre compteur Linky avec alerte email en cas de consommation anormalement basse (disjoncteur sauté, coupure de courant).

---

## 📋 Fonctionnement

Chaque matin, le script interroge l'API [Conso API (Boris)](https://conso.boris.sh) pour récupérer la consommation électrique de la veille. Si la valeur est en dessous d'un seuil configuré, un email d'alerte est envoyé automatiquement.

```
Compteur Linky → Enedis → Conso API (Boris) → Script Python → Email d'alerte
```

---

## ⚙️ Configuration

Toutes les valeurs sensibles sont stockées dans les **GitHub Secrets** (jamais en clair dans le code).

| Secret | Description |
|---|---|
| `LINKY_TOKEN` | Token JWT obtenu sur [conso.boris.sh](https://conso.boris.sh) |
| `LINKY_PRM` | Numéro PRM du compteur (14 chiffres) |
| `SMTP_USER` | Adresse email expéditrice (Gmail) |
| `SMTP_PASSWORD` | Mot de passe d'application Gmail |
| `ALERT_TO` | Destinataires de l'alerte, séparés par une virgule |

Le seuil d'alerte est défini dans `linky_alert.py` :

```python
SEUIL_WH = 100  # en Wh — en dessous = alerte envoyée
```

---

## 🚀 Déclenchement automatique

Le workflow GitHub Actions s'exécute **tous les jours à 8h34 UTC (10h34 heure de Paris)** via la planification cron :

```yaml
on:
  schedule:
    - cron: '34 8 * * *'
  workflow_dispatch:  # lancement manuel possible
```

> 💡 Les données Linky sont disponibles sur l'API vers 8h00. Il est conseillé d'éviter une heure pile pour répartir la charge sur le serveur.

---

## 📦 Prérequis

- Un compteur **Linky** avec un espace client [Enedis](https://espace-client.enedis.fr)
- Un compte sur [conso.boris.sh](https://conso.boris.sh) pour obtenir le token
- Un compte **Gmail** avec la validation en 2 étapes activée et un [mot de passe d'application](https://myaccount.google.com/apppasswords) généré

---

## 📧 Exemple d'email d'alerte

```
Objet : 🚨 Linky — Consommation anormalement basse le 2026-04-17 (42 Wh)

⚠️ ALERTE : La consommation électrique de la veille est anormalement basse.

📅 Date          : 2026-04-17
⚡ Consommation  : 42 Wh
🔻 Seuil d'alerte : 100 Wh

Cela peut indiquer :
  • Le disjoncteur principal a sauté
  • Une coupure de courant chez vous
  • Un problème de relevé du compteur Linky

👉 Veuillez vérifier votre installation électrique.
```

---

## 🛠️ Technologies

- **Python 3.12**
- **[Conso API](https://conso.boris.sh)** — passerelle open-source vers les données Enedis
- **GitHub Actions** — planification et exécution gratuite

---

## 📄 Licence

Usage personnel — projet open-source libre de droits.
