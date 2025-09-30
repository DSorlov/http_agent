# HTTP Agent

A comprehensive Home Assistant integration for making HTTP requests with template support and automatic sensor polling.

## Features

- **HTTP Services**: Make HTTP requests (GET, POST, PUT, DELETE, PATCH, HEAD) with full template support
- **HTTP Sensors**: Automatically poll HTTP endpoints at configurable intervals
- **Template Support**: Use Home Assistant templates in URLs, payloads, query parameters, and headers
- **GUI Configuration**: Full GUI-based setup and management of sensors
- **Multi-language Support**: Available in English, Swedish, Danish, Finnish, Norwegian, German, Spanish, and French

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "HTTP Agent"
5. Install the integration
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/httpagent` folder to your `custom_components` directory
2. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to **Configuration** → **Integrations**
2. Click **+ Add Integration**
3. Search for "HTTP Agent"
4. Follow the setup wizard to configure your integration

### Services

The integration provides the following services:

#### `httpagent.http_request`
Make a generic HTTP request with full control over method, payload, headers, etc.

#### `httpagent.http_get`
Make a HTTP GET request.

#### `httpagent.http_post`
Make a HTTP POST request with payload.

#### `httpagent.http_put`
Make a HTTP PUT request with payload.

#### `httpagent.http_delete`
Make a HTTP DELETE request.

### Service Parameters

All services support the following parameters:

- `url` (required): The URL to make the request to (supports templates)
- `method`: HTTP method (for generic http_request service)
- `payload`: Request body content (supports templates)
- `headers`: HTTP headers as a dictionary
- `querystring`: URL query parameters (supports templates)
- `timeout`: Request timeout in seconds (default: 10)
- `ssl_verify`: Whether to verify SSL certificates (default: true)

### Sensors

HTTP sensors automatically poll endpoints at regular intervals and store:

- **State**: HTTP status code or connection state
- **Dynamic Icons**: Visual status indicators
  - 🟢 `mdi:web-check` - Success (HTTP 2xx)
  - 🔴 `mdi:web-remove` - Error (HTTP 4xx/5xx)
  - 🟡 `mdi:web-clock` - Timeout
  - ⚫ `mdi:web-off` - Disabled
  - 🔵 `mdi:web` - Unknown/Pending
- **Attributes**:
  - `response`: Parsed response (JSON if possible, otherwise text)
  - `response_text`: Raw response text
  - `headers`: Response headers
  - `status_code`: HTTP status code
  - `url`: Actual URL requested (after template rendering)
  - `method`: HTTP method used
  - `last_updated`: Timestamp of last update

### Template Support

You can use Home Assistant templates in:
- URLs: `http://{{ states('sensor.server_ip') }}:8080/api`
- Payloads: `{\"value\": {{ states('sensor.temperature') }}}`
- Query strings: `id={{ states('sensor.device_id') }}&token=abc123`
- Headers: Values in the headers dictionary

### Examples

#### Service Call Example

```yaml
service: httpagent.http_post
data:
  url: "http://192.168.1.100:8080/api/update"
  payload: |
    {
      \"temperature\": {{ states('sensor.outside_temperature') }},
      \"humidity\": {{ states('sensor.outside_humidity') }},
      \"timestamp\": \"{{ now().isoformat() }}\"
    }
  headers:
    Authorization: "Bearer {{ states('input_text.api_token') }}"
    Content-Type: "application/json"
  ssl_verify: false
```

#### Automation Example

```yaml
automation:
  - alias: "Send temperature update"
    trigger:
      - platform: state
        entity_id: sensor.outside_temperature
    action:
      - service: httpagent.http_post
        data:
          url: "http://{{ states('sensor.weather_server') }}/temperature"
          payload: |
            {
              \"location\": \"outside\",
              \"temperature\": {{ states('sensor.outside_temperature') }},
              \"unit\": \"°C\"
            }
          headers:
            Content-Type: "application/json"
```

#### Sensor Configuration

Sensors are configured through the GUI when setting up the integration. Each sensor can have:

- Custom update intervals (5-86400 seconds)
- Different HTTP methods
- Custom payloads and query parameters
- Individual SSL verification settings
- Enable/disable toggle

## Troubleshooting

### Debug Logging

Add this to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  logs:
    custom_components.httpagent: debug
```

### Common Issues

1. **SSL Certificate Errors**: Set `ssl_verify: false` if you're using self-signed certificates
2. **Template Errors**: Check your template syntax in the Home Assistant template editor
3. **Timeout Issues**: Increase the timeout value for slow endpoints
4. **Authentication**: Make sure to include proper headers for authenticated endpoints

## Version History

### 1.0.0
- Initial release
- HTTP services with template support
- HTTP sensors with configurable polling
- GUI configuration
- Multi-language support
- HACS compatibility

## Contributing

Please report issues and feature requests on the [GitHub repository](https://github.com/dsorlov/httpAgent).

## License

This project is licensed under the MIT License.