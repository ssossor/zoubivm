# Installation

### 1. Create API Keys File
Create a `rootme_api_keys.json` file in the project root with your RootMe API keys:

```json
[
    "your_first_api_key",
    "your_second_api_key",
    "your_third_api_key"
]
```

**Note**: This file is in `.gitignore` for security. Each key will be used in rotation when rate limits are encountered.

### 2. Fill the .env file

```
DISCORD_TOKEN=
TARGET_CHANNEL_ID=
USERS_LIST_FILE=users.json
```

**Optional**: You can specify a custom path for the API keys file:
```
ROOT_ME_API_KEYS_FILE=/custom/path/to/api_keys.json
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
