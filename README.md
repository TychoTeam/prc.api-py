`prc.api` is an asynchronous Python wrapper for the Police Roleplay Community (PRC) API / ERLC API.  
It provides a convenient way to interact with PRC APIs, including the [private server APIs](https://apidocs.erlc.gg/) for ER:LC (aka. ERLC API), Discord webhook handlers, ER:LC webhook events (payload types) and more.

### 📖 [Documentation](https://github.com/TychoTeam/prc.api-py/wiki) | [PyPI](https://pypi.org/project/prc.api)

## Features

- 🧩 **Developer Friendly**  
  Functions and responses are wrapped and categorized for ease of use.
- 💫 **Full Coverage**  
  Supports ALL features from both API v1 and v2 as of _October 2026_.
- 🛡️ **Maintained**  
  One of the only actively maintained and fully open source (OSS) PRC API libraries.
- 💪 **Robust**  
  Well tested against errors and handles all known edge-cases. The package is used by large communities with high reliability.

### And more...

- **Rate Limits** & **Caching**  
  By default, the package handles and queues requests to ensure **near-zero** chances of rate limits. It also caches frequent requests and reusable data.
- **Better Models**  
  The package is strictly typed and all API data is transformed for ease of use. 🎊 **Vehicle names, command names AND street names (_yes, the new map_) are all included.**
- **Utilities**  
  Useful utilities and helper methods spread across the package to make your life easier.
- **Prevents Bans**  
  Along with rate limit parsing and handling, you never have to worry about invalid secrets resulting in IP bans (within a process' lifetime).
- **Webhook Events**  
  Included are also types for all the [undocumented] ER:LC Webhook Event payloads.
- **By Humans**  
  While many slop ER:LC libraries keep popping up, prc.api is made and maintained by humans. You can even [talk to us](https://discord.tycho.team)!

#### Check out the documentation for all details.

## Install Latest Release (`pip`)

```sh
pip install prc.api
```

The package is implemented and has been tested in Python `v3.8` and above. It may not work on older versions.
