`prc.api` is an asynchronous Python wrapper for the Police Roleplay Community (PRC) API.  
It provides a convenient way to interact with PRC APIs, including the [private server APIs](https://apidocs.policeroleplay.community) for ER:LC.

### 📖 [Documentation](https://github.com/TychoTeam/prc.api-py/wiki) | [PyPI](https://pypi.org/project/prc.api)

## Features

- 🧩 **Developer Friendly**  
  Functions and responses are wrapped and categorized for ease of use.
- 💫 **Full Coverage**  
  Supports all features from the API as of _November 2025_.
- 🛡️ **Maintained**  
  Actively maintained and fully open source for any contributions.
- 💪 **Robust**  
  Well tested against errors and handles all known edge-cases.

### And more...

- **Rate Limits** & **Caching**  
  By default, the package handles and queues requests to ensure **near-zero** chances of rate limits. It also caches frequent requests and reusable data.
- **Better Types**  
  The package is strictly typed and all API data is transformed for ease of use. 🎊 **Vehicles and command names are included!**
- **Utilities**  
  Extremely useful utilities and helpers spread across the package to make your life easier.
- **Prevents Bans**  
  Along with rate limit parsing and handling, you never have to worry about invalid secrets resulting in IP bans!

#### Check out the documentation for all details.

## Install Latest Release (`pip`)

```sh
pip install prc.api
```

The package has been tested for Python `v3.8+`. It may not work on older versions.
