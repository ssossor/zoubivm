# Installation

### 1. Create API Keys File
Copy the example file and fill it with your RootMe API keys:

```
cp rootme_api_keys.example.json rootme_api_keys.json
```

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
LOG_CHANNEL_ID=
USERS_LIST_FILE=data/users.json
TOR_PROXY=socks5://tor:9050
```

- `TARGET_CHANNEL_ID`: channel where new validations are announced.
- `LOG_CHANNEL_ID` (optional): channel where the bot reports serious problems (see
  [Log channel](#log-channel)). Leave it empty to disable it.
- `TOR_PROXY` (optional): Tor SOCKS proxy used first when Root-Me can't be reached
  (see [Root-Me rate limits and proxies](#root-me-rate-limits-and-proxies)).
  `socks5://tor:9050` is the Tor container started by Docker Compose. Leave it empty
  to use free proxies only.

The bot keeps its data (`users.json`, `challenges.json`) in the `data/` folder.
If you are upgrading from a version that kept `users.json` at the root, move it:
```
mkdir -p data && mv users.json data/
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
```

# Starting
```
python main.py
```

Or with Docker Compose (`data/`, `.env` and `rootme_api_keys.json` are mounted into the
container):
```
make up      # start
make logs    # follow logs
make down    # stop
```

# Root-Me rate limits and proxies
The bot refreshes every registered user every 5 minutes through the Root-Me API.

- It starts on its own IP, without any proxy.
- On a rate limit (HTTP 429), it switches to the next API key and to proxies (a
  connection failure switches to the proxies too). Proxies are tested against
  Root-Me and the fastest one is used. They come from the first source giving a
  working one:
  1. Tor, when `TOR_PROXY` is set: 5 circuits, each one usually with its own exit IP.
  2. [Geonode](https://geonode.com/free-proxy-list) (uptime >= 90 %).
  3. [stormsia](https://stormsia.github.io/proxy-list) (re-validated every 15 min).
  4. [ProxyScrape](https://proxyscrape.com/free-proxy-list).
  5. [Proxifly](https://github.com/proxifly/free-proxy-list) (largest list, random
     sample).

  Free proxies are European SOCKS5 and HTTP(S) proxies. Through an HTTP proxy, HTTPS
  requests go through a CONNECT tunnel: the proxy never sees the API keys.
- When a proxy fails or is rate limited, it moves to the next one. After 3 failed
  attempts, it gives up on the request, waits 60 s and goes on with the next user.
- When every proxy has been used, a new list is fetched (with Tor: new circuits). If
  no proxy works, the bot stays on its own IP and waits as asked by Root-Me
  (`Retry-After`).

Docker Compose starts a `tor` container next to the bot (`tor/`). Its SOCKS port is
only reachable from the Compose network, it is not published on the host.

See [proxy_manager/README.md](proxy_manager/README.md) to add another proxy provider.

# Log channel
When `LOG_CHANNEL_ID` is set, the bot posts in that channel:

- `⚠️ Refresh failed for all N users`: no user could be refreshed (Root-Me down, rate
  limited even through the proxies...). Posted once, not on every refresh.
- `✅ Refresh works again`: the refresh works again after such a failure.
- `🛑 Refresh task stopped`: the refresh task crashed; restart the bot.

Failures for a few users only are not reported, they are retried at the next refresh.

# Tests
```
pip install -r requirements-dev.txt
pytest
```

Tests never touch the network: Root-Me, the proxy providers and Discord are faked.

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
