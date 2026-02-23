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

# Commandes
`/register <profile_name>`: Permet de register un compte Root-me, le paramètre est le nom du profil dans l'url Root-me.

>Exemple:<br>
>https://www.root-me.org/Aube-643003 -> Aube-643003

`/remove <user_id>`: Permet de supprimer un compte Root-me enregistré dans la base de donnée, le paramètre est l'id de l'utilisateur.

>Exemple:<br>
>Aube-643003 -> 643003<br>
>Ssor -> 822479

`/leaderboard`: Permet d'afficher le leaderboard.

`/profile <username>`: Permet d'afficher le profil d'un utiliateur enregistré dans la base de donnée.

>Exemple:<br>
>Aube-643003: `/profile Aube` (parce que en ft mon nom rootme c'est Aube officiellement)

`/ping`: Permet de tester le bot.

`/list`: Permet d'afficher les utilisateurs enregistrés dans la base de donnée.

`!sync`: Permet de synchroniser les commandes / de discord avec Discord.
