# HTTP Agent

[![hacs][hacs-badge]][hacs]
[![release][release-badge]][release]
[![ci][ci-badge]][ci]
[![license][license-badge]][license]

Turn any HTTP endpoint into Home Assistant entities. Point HTTP Agent at a URL,
let it call the endpoint once, and pick the values you want from a list — no
hand-written JSON paths or XPath expressions required.

<p align="center">
  <img src="brands/custom_integrations/http_agent/logo.png" alt="HTTP Agent" width="320">
</p>

## Features

- **Guided setup.** URL, method, authentication — then a live test request.
- **Visual value picker.** The response is flattened into a searchable list of
  `path = value` pairs. Tick the ones you want; entity type, device class, unit
  and state class are guessed for you.
- **JSON, XML, HTML and plain text** are detected automatically.
- **Authentication presets** for bearer tokens, API keys and HTTP basic auth,
  plus free-form headers when you need something else.
- **One entity per subentry**, so entities can be added, edited and deleted
  individually straight from the integration page.
- **Use it in automations** with the `http_agent.request` action, which returns
  the data normalised the same way as the sensors.
- **Templates** are supported in the URL, headers and request body.
- **Configurable retries** so a flaky endpoint does not mark everything
  unavailable.
- Automatic re-authentication, reconfiguration and redacted diagnostics.
- Fully translated into 24 languages.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-repo]

1. Add `https://github.com/DSorlov/http_agent` as a custom repository of type
   **Integration**.
2. Install **HTTP Agent** and restart Home Assistant.

### Manual

Copy `custom_components/http_agent` into your `config/custom_components/`
directory and restart Home Assistant.

Home Assistant 2026.4.4 or newer is required.

## Setup

**Settings → Devices & services → Add integration → HTTP Agent**

### 1. The endpoint

| Field          | Description                                        |
| -------------- | -------------------------------------------------- |
| URL            | Full endpoint URL. Templates are supported.        |
| Method         | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` or `HEAD`. |
| Authentication | `none`, `bearer`, `api_key` or `basic`.            |
| Name           | Optional. Defaults to the hostname.                |

Everything else lives under **Advanced settings**: update interval, timeout,
retries, extra headers, forced response format, SSL verification and redirect
handling.

Extra headers are written one per line:

```
Accept: application/json
X-Client-Id: home-assistant
X-Signature: {{ states('input_text.signature') }}
```

### 2. Authentication

Only shown when you pick a preset:

| Preset    | Sends                                            |
| --------- | ------------------------------------------------ |
| `bearer`  | `Authorization: Bearer <token>`                  |
| `api_key` | A header of your choice, e.g. `X-API-Key: <key>` |
| `basic`   | HTTP basic authentication                        |

Credentials are stored in the config entry and are redacted from logs and
diagnostics.

### 3. Request body

Only shown for methods that carry a body. Pick a content type and enter the
payload; templates are supported.

### 4. Pick your values

HTTP Agent calls the endpoint and shows you what came back:

> The endpoint answered with HTTP 200 and was read as **JSON**. 12 values were
> found.

The picker lists every addressable value together with the value it currently
has, so you can recognise what you are looking at:

```
current.temp_c     = 21.5
current.humidity   = 48
current.is_raining = false
location.name      = Stockholm
```

Select what you want and HTTP Agent creates the entities, guessing the entity
type, device class, unit and state class from the key name and value. Anything
guessed wrong can be corrected afterwards.

You can also skip this step and add entities later.

## Adding entities later

On the integration page each endpoint has **Add sensor**, **Add binary sensor**
and **Add device tracker** buttons. Every entity is its own subentry, so it can
be reconfigured or deleted on its own. The value picker in these dialogs is
populated from the most recent response, and you can always type a path
manually.

## Path syntax

The picker fills these in for you, but they can be written by hand too.

| Format | Syntax             | Examples                                              |
| ------ | ------------------ | ----------------------------------------------------- |
| JSON   | Dot / bracket path | `current.temp_c`, `items[0].id`, `$.data.value`        |
| XML    | ElementTree XPath  | `./current/temperature`, `./sensor[2]`, `./@id`        |
| XML    | Attribute suffix   | `./current/temperature/@unit`                          |
| HTML   | CSS selector       | `#temp`, `.reading .value`, `table tr:nth-of-type(2)`  |
| HTML   | Attribute suffix   | `#link::attr(href)`                                    |
| Text   | Regular expression | `temperature=([\d.]+)`, or `.` for the whole body      |

For text bodies the first capture group is used, or the whole match when the
expression has no groups.

## Entity types

| Type           | Reads                                           | Notes                                                       |
| -------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| Sensor         | One value                                       | Device class, unit and state class configurable             |
| Binary sensor  | One value                                       | `true/1/on/yes/open/…` auto-detected, or set exact payloads |
| Device tracker | Latitude and longitude, optionally GPS accuracy | Source type configurable                                    |

Every entity can also expose extra state attributes, written one per line:

```
humidity: current.humidity
station: location.name
```

## Templates

Home Assistant templates are rendered on every poll in the URL, header values
and request body:

```
https://api.example.com/weather?city={{ states('input_text.city') }}
```

## Using it in automations

The `http_agent.request` action calls an endpoint on demand and returns the
answer, so a later step can use it. It is a normal action, so it works in
automations, scripts and scenes, and is scheduled the same way as anything else
in Home Assistant.

### Reading data mid-automation

```yaml
actions:
  - action: http_agent.request
    data:
      config_entry_id: 01JABCDEF0123456789ABCDEFG
      select:
        temperature: current.temp_c
        condition: current.condition.text
    response_variable: weather

  - condition: template
    value_template: "{{ weather.values.temperature < 5 }}"

  - action: notify.persistent_notification
    data:
      message: "It is {{ weather.values.temperature }} degrees and {{ weather.values.condition }}"
```

### Sending data from other entities

```yaml
actions:
  - action: http_agent.request
    data:
      config_entry_id: 01JABCDEF0123456789ABCDEFG
      method: POST
      url: /api/v1/readings
      payload: >
        {
          "temperature": {{ states('sensor.living_room_temperature') }},
          "humidity": {{ states('sensor.living_room_humidity') }},
          "at": "{{ now().isoformat() }}"
        }
```

`config_entry_id` is optional and only supplies defaults. Without it, give a
full `url` instead.

### What the action accepts

| Field             | Description                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------ |
| `config_entry_id` | An existing endpoint to inherit URL, authentication, headers and connection settings from   |
| `url`             | Full URL, or a `/path` resolved against the endpoint host                                   |
| `method`          | Defaults to `GET`                                                                            |
| `payload`         | Request body; templates are rendered by Home Assistant before the call                      |
| `headers`         | Extra headers, merged on top of the endpoint headers                                        |
| `select`          | Mapping of result name to path, using the same syntax as the sensors                        |

Advanced fields: `content_type`, `response_format`, `timeout`, `retries` and
`verify_ssl`. All of them fall back to the endpoint when one is referenced.

### What the action returns

```yaml
status: 200
format: json
headers: { content-type: application/json }
values:
  temperature: 21.5
  condition: Partly cloudy
content: { ... }
```

`values` holds what you asked for in `select`, extracted exactly like a sensor
would. `content` is the decoded JSON, or the raw text for other formats.
Credential headers are redacted. The endpoint's own `method` and body are never
inherited, so an endpoint that polls with `GET` can still be sent a `POST`.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.http_agent: debug
```

Then use **Download diagnostics** on the integration page. The URL, headers and
credentials are redacted, so the file is safe to attach to an issue.

| Symptom                   | Likely cause                                                     |
| ------------------------- | ---------------------------------------------------------------- |
| `cannot_connect`          | Wrong URL, DNS, firewall, or the timeout is too short            |
| `invalid_auth`            | The endpoint answered 401/403 — check the preset and credentials |
| `bad_status`              | The endpoint answered 4xx/5xx                                    |
| `no_values`               | The response body was empty                                      |
| Entity state is `unknown` | The configured path no longer resolves — reconfigure the entity  |

For endpoints that fail occasionally, raise **Retries on error** under advanced
settings. Each retry waits one second, and the poll only fails once every
attempt has been used.

## Upgrading from 1.x

Existing config entries are migrated automatically on first start:

- Headers move from a list to a dictionary.
- Each configured sensor becomes its own subentry.
- Read-only `number` entities become sensors; the `number` platform is gone.
- The `sensor_color` field becomes an extra state attribute named `color`.

Entity IDs change because entities now follow the `has_entity_name` convention.
Check automations and dashboards after upgrading.

## Security

- XML is parsed with `defusedxml`, so XXE and entity-expansion payloads are
  rejected.
- Credentials are redacted from logs and diagnostics.
- Disabling SSL verification is possible, but hidden under advanced settings.

Report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

.venv/bin/ruff check custom_components tests
.venv/bin/ruff format custom_components tests
.venv/bin/pytest
python script/validate_assets.py
```

Brand assets live in [`brands/`](brands/README.md) and mirror what is published
in [home-assistant/brands][brands].

## License

[MIT](LICENSE)

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=DSorlov&repository=http_agent&category=integration
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[release]: https://github.com/DSorlov/http_agent/releases
[release-badge]: https://img.shields.io/github/v/release/DSorlov/http_agent
[ci]: https://github.com/DSorlov/http_agent/actions/workflows/ci.yaml
[ci-badge]: https://github.com/DSorlov/http_agent/actions/workflows/ci.yaml/badge.svg
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/DSorlov/http_agent
[brands]: https://github.com/home-assistant/brands/tree/master/custom_integrations/http_agent
