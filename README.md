# 🔌 LinkyAlert

Surveillance automatique de vos compteurs Linky avec alerte email en cas de consommation anormalement basse (disjoncteur sauté, coupure de courant).

Supporte **plusieurs comptes Enedis** avec un seuil d'alerte et des destinataires personnalisés par compteur.

---

## 📋 Fonctionnement

Chaque matin, le script interroge l'API [Conso API (Boris)](https://conso.boris.sh) pour récupérer la consommation électrique de la veille de chaque compteur configuré. Si la valeur est en dessous du seuil configuré, un email d'alerte est envoyé automatiquement aux destinataires du compte concerné.

```
Compteur Linky → Enedis → Conso API (Boris) → Script Python → Email d'alerte
```

---

## ⚙️ Configuration

Toutes les valeurs sensibles sont stockées dans les **GitHub Secrets** (jamais en clair dans le code).

| Secret | Description |
|---|---|
| `LINKY_ACCOUNTS` | JSON listant tous les comptes à surveiller (voir format ci-dessous) |
| `SMTP_USER` | Adresse email expéditrice (Gmail) |
| `SMTP_PASSWORD` | Mot de passe d'application Gmail |

### Format du secret `LINKY_ACCOUNTS`

Le secret contient un tableau JSON, **sur une seule ligne**, avec un objet par compteur :

```json
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
```

| Champ | Obligatoire | Description |
|---|---|---|
| `name` | Non | Nom du compteur affiché dans l'email (ex: "Saint Martin"). Si absent, le PRM est utilisé. |
| `token` | Oui | Token JWT obtenu sur [conso.boris.sh](https://conso.boris.sh) |
| `prm` | Oui | Numéro PRM du compteur (14 chiffres, affiché sur le compteur en appuyant sur +) |
| `alert_to` | Oui | Liste d'adresses email destinataires de l'alerte |
| `seuil_wh` | Non | Seuil en Wh en dessous duquel l'alerte est déclenchée (défaut : 100 Wh) |

---

## 🚀 Déclenchement automatique

Le workflow GitHub Actions s'exécute **tous les jours à 8h34 UTC (10h34 heure de Paris)** via la planification cron :

```yaml
on:
  schedule:
    - cron: '34 8 * * *'
  workflow_dispatch: # lancement manuel possible
```

> 💡 Les données Linky sont disponibles sur l'API vers 8h00. Il est conseillé d'éviter une heure pile pour répartir la charge sur le serveur.

---

## 📦 Prérequis

- Un (ou plusieurs) compteur(s) Linky avec un espace client Enedis
- Un compte sur [conso.boris.sh](https://conso.boris.sh) par compteur pour obtenir le token JWT
- Un compte Gmail avec la validation en 2 étapes activée et un mot de passe d'application généré

---

## 📧 Exemple d'email d'alerte

**Objet :** `🚨 Linky [Saint Martin] — Consommation anormalement basse le 2026-04-17 (42 Wh)`

```
⚠️ ALERTE : La consommation électrique de "Saint Martin" de la veille est anormalement basse.

📅 Date         : 2026-04-17
🏠 Compteur     : Saint Martin
🔌 PRM          : 98765432109876
⚡ Consommation : 42 Wh
🔻 Seuil alerte : 500 Wh

Cela peut indiquer :
• Le disjoncteur principal a sauté
• Une coupure de courant chez vous
• Un problème de relevé du compteur Linky

👉 Veuillez vérifier votre installation électrique.
```

---

## 🛠️ Technologies

- Python 3.12
- [Conso API](https://conso.boris.sh) — passerelle open-source vers les données Enedis
- GitHub Actions — planification et exécution gratuite

---

## 📄 Licence

Usage personnel — projet open-source libre de droits.
