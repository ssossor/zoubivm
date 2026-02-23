# Installation
Faut remplir le .env comme ça:

```
DISCORD_TOKEN=
ROOT_ME_API_KEY=
TARGET_CHANNEL_ID=
USERS_LIST_FILE=users.json
```

Et activer sur le bot l'option:
`Message Content Intent`
(C'est dans le dev portal de discord)

Ensuite faut faire
```
pip install -r requirements.txt
playwright install
```

# Démarrage
```
python main.py
```
