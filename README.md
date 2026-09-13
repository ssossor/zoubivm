# Installation
Fill the .env file as follows:

```
DISCORD_TOKEN=
ROOT_ME_API_KEY=
TARGET_CHANNEL_ID=
USERS_LIST_FILE=users.json
```

**Alternative for multiple API keys**: Instead of `ROOT_ME_API_KEY`, you can create a `rootme_api_keys.json` file with an array of API keys:
```json
[
    "your_first_api_key",
    "your_second_api_key",
    "your_third_api_key"
]
```
See [ROOTME_API_KEYS_README.md](ROOTME_API_KEYS_README.md) for more details on API key rotation.

And enable the following option for the bot:
`Message Content Intent`
(Found in the Discord developer portal)

Then run:
```
pip install -r requirements.txt
playwright install
```

# Starting
```
python main.py
```

# Commands
`/register <profile_name>`: Register a Root-me account. The parameter is the profile name from your Root-me URL.

>Example:<br>
>https://www.root-me.org/Aube-643003 -> Aube-643003

`/remove <user_id>`: Remove a registered Root-me account from the database. The parameter is the user's ID.

>Example:<br>
>Aube-643003 -> 643003<br>
>Ssor -> 822479

`/leaderboard`: Display the leaderboard.

`/profile <username>`: Display the profile of a registered user from the database.

>Example:<br>
>Aube-643003: `/profile Aube`

`/ping`: Test the bot.

`/list`: Display all registered users from the database.

`!sync`: Sync Discord slash commands.
