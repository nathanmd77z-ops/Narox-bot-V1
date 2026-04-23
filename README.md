# Bot Discord Tickets & Modération

Bot Discord en **Python** avec :

- système de **tickets**
- catégories de tickets séparées
- boutons de gestion
- commandes avec préfixe `!`
- commandes de modération
- logs
- transcript HTML des tickets

---

## Fonctions
TOKEN=ton_token_bot
GUILD_ID=id_du_serveur
LOG_CHANNEL_ID=id_du_salon_logs

SUPPORT_ROLE_ID=id_role_probleme_en_jeux
ACHAT_ROLE_ID=id_role_boutique
PARTENARIAT_ROLE_ID=id_role_rc_staff
AUTRE_ROLE_ID=id_role_bug

SUPPORT_CATEGORY_ID=id_categorie_probleme_en_jeux
ACHAT_CATEGORY_ID=id_categorie_boutique
PARTENARIAT_CATEGORY_ID=id_categorie_rc_staff
AUTRE_CATEGORY_ID=id_categorie_bug

FONDATEUR_ROLE_ID=id_role_fondateur

### Tickets
- ouverture de ticket via menu
- 4 types de tickets :
  - **PROBLEME EN JEUX**
  - **BOUTIQUE**
  - **RC STAFF**
  - **BUG**
- création du ticket dans une **catégorie Discord différente** selon le type
- anti doublon
- transcript HTML lors de la suppression
- logs dans un salon dédié

### Gestion des tickets
Commandes disponibles dans un ticket :

- `!panel` → envoie le panneau des tickets
- `!ticketinfo` → affiche les infos du ticket
- `!claim` → claim le ticket
- `!unclaim` → retire le claim
- `!delete` → supprime le ticket
- `!add @membre` → ajoute un membre au ticket
- `!remove @membre` → retire un membre du ticket
- `!rename nouveau-nom` → renomme le ticket

Les boutons dans les tickets permettent aussi :

- Claim
- Unclaim
- Ajouter membre
- Retirer membre
- Renommer
- Supprimer

### Modération
- `!ban @membre raison`
- `!unban ID raison`
- `!clear 10`
- `!clear all`

**Important :**
- `!clear` est réservé au rôle **Fondateur**
- les messages de commande sont supprimés automatiquement

---

## Fichiers du projet

```text
bot.py
ban_unban.py
clear_commands.py
requirements.txt
Procfile
runtime.txt
README.md
