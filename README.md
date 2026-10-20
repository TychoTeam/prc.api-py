`prc.api` is an asynchronous Python wrapper for the Police Roleplay Community (PRC) API / ERLC API.  
It provides a convenient way to interact with PRC APIs, including the [private server APIs](https://apidocs.erlc.gg/) for ER:LC (aka. ERLC API), Discord webhook handlers, ER:LC webhook events (payload types) and more.

### 📖 [Documentation](https://github.com/TychoTeam/prc.api-py/wiki) | [PyPI](https://pypi.org/project/prc.api) | [GitHub](https://github.com/TychoTeam/prc.api-py)

## Features

- 🧩 **Developer Friendly**  
  Functions and responses are fully wrapped for ease of use.
- 💫 **Full Coverage**  
  Supports ALL features from both API v1 and v2 as of _October 2026_.
- 🛡️ **Maintained**  
  One of the most actively maintained and fully open source PRC API libraries.
- 💪 **Robust**  
  Well tested against errors and handles all known edge-cases. The package is used by large communities with high reliability.

### And more...

- **Rate Limits** & **Caching**  
  By default, the package handles and queues requests to ensure **near-zero** chances of rate limits. It also caches frequent requests and reusable data as well as blocking invalid secrets/keys (within a process' lifetime).
- **Better Models** & **Types**  
  The package is strictly typed and all API data is transformed for ease of use. 🎊 **Types for vehicle names, command names AND street names are all included.**
- **Utilities**  
  Useful utilities and helper methods are spread across the package to make your life easier.
- **Webhook Events**  
  Included are also models and types for all the _[undocumented]_ ER:LC Webhook Event payloads.
- **By Humans**  
  While many slop ER:LC libraries keep popping up, prc.api is made and maintained by humans. You can even [talk to us](https://discord.tycho.team).

#### Check out the documentation for details.

## Install Latest Release (`pip`)

```sh
pip install prc.api
```

The package only supports Python version `v3.8+` (and above). It may not work on older versions.
