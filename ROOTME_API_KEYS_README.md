# RootMe API Keys Rotation System

## Overview

This system allows the ZoubiVM bot to rotate through multiple RootMe API keys when rate limits (HTTP 429) are encountered. This helps distribute API requests and avoid being blocked by RootMe's rate limiting.

## Setup

### Option 1: Using a JSON File (Recommended)

Create a file named `rootme_api_keys.json` in the project root with your API keys:

```json
[
    "your_first_rootme_api_key",
    "your_second_rootme_api_key",
    "your_third_rootme_api_key"
]
```

The bot will automatically load keys from this file if it exists.

### Option 2: Using Environment Variable (Backward Compatible)

You can still use a single API key via the `.env` file:

```
ROOT_ME_API_KEY=your_single_api_key
```

### Option 3: Custom JSON File Path

You can specify a custom path for the API keys file in your `.env`:

```
ROOT_ME_API_KEYS_FILE=/path/to/your/custom_api_keys.json
```

## Priority Order

The bot will try to load API keys in the following order:

1. **Single key from environment** (`ROOT_ME_API_KEY` in `.env`)
2. **Custom JSON file path** (`ROOT_ME_API_KEYS_FILE` in `.env`)
3. **Default JSON file** (`rootme_api_keys.json` in project root)

If none of these are available, the bot will raise an error on startup.

## How It Works

1. When a rate limit (HTTP 429) is detected, the client will:
   - Rotate to the next available API key
   - Reinitialize the HTTP client with the new key
   - Continue with the request

2. The rotation is circular: after the last key, it goes back to the first one.

3. If only one API key is provided (backward compatibility mode), no rotation occurs.

## Logging

The system logs API key rotations with the following format:

```
Rotated API key (2/3) for: Rate limit (429)
```

Where `2/3` indicates the current key index out of the total number of keys.

## Security

The `rootme_api_keys.json` file is automatically added to `.gitignore` to prevent accidental commitment of API keys to version control.

## Code Usage

### Manual API Key Rotation

```python
from clients import RootMeClient

# Create client with multiple keys
client = await RootMeClient.create(api_key=["key1", "key2", "key3"])

# Manually rotate API key
await client.rotate_api_key("Manual rotation")
```

### Loading from File

```python
# Load keys from default file
client = await RootMeClient.create_from_file()

# Load keys from custom file
client = await RootMeClient.create_from_file("/path/to/keys.json")
```

### Loading Static Method

```python
# Load keys without creating a client
keys = RootMeClient.load_api_keys_from_file("/path/to/keys.json")
```

## Integration with Proxy Rotation

The system works alongside the existing proxy rotation mechanism. When an error occurs:

1. If multiple API keys are available, the API key is rotated first
2. The proxy is always rotated (existing behavior)

This provides two layers of protection against rate limiting:
- API key rotation at the RootMe API level
- Proxy rotation at the network level
