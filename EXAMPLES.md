# Example usage of HTTP Agent

## Services Examples

### Basic HTTP GET request
```yaml
service: httpagent.http_get
data:
  url: "http://192.168.1.100:8080/api/status"
```

### HTTP POST with JSON payload and templates
```yaml
service: httpagent.http_post
data:
  url: "http://{{ states('sensor.server_ip') }}:8080/api/data"
  payload: |
    {
      "temperature": {{ states('sensor.temperature') }},
      "humidity": {{ states('sensor.humidity') }},
      "timestamp": "{{ now().isoformat() }}"
    }
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer {{ states('input_text.api_token') }}"
```

### HTTP request with query parameters
```yaml
service: httpagent.http_get
data:
  url: "http://api.example.com/data"
  querystring: "device_id={{ states('sensor.device_id') }}&format=json&limit=10"
  headers:
    Accept: "application/json"
```

### HTTP request with SSL disabled
```yaml
service: httpagent.http_post
data:
  url: "https://192.168.1.100:8443/api/update"
  payload: '{"status": "online"}'
  ssl_verify: false
  timeout: 30
```

## Automation Examples

### Send notification when sensor changes
```yaml
automation:
  - alias: "Notify external system of temperature change"
    trigger:
      - platform: state
        entity_id: sensor.living_room_temperature
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != trigger.from_state.state }}"
    action:
      - service: httpagent.http_post
        data:
          url: "http://monitoring.local/api/sensors"
          payload: |
            {
              "sensor_id": "living_room_temp",
              "value": {{ states('sensor.living_room_temperature') }},
              "unit": "°C",
              "timestamp": "{{ now().isoformat() }}",
              "previous_value": {{ trigger.from_state.state }}
            }
          headers:
            Content-Type: "application/json"
            X-Source: "home-assistant"
```

### Periodic status update
```yaml
automation:
  - alias: "Send hourly status update"
    trigger:
      - platform: time_pattern
        minutes: 0
    action:
      - service: httpagent.http_put
        data:
          url: "http://status-server.local/api/home-status"
          payload: |
            {
              "home_status": "{{ states('alarm_control_panel.home_alarm') }}",
              "occupancy": {{ is_state('binary_sensor.occupancy', 'on') | lower }},
              "temperature": {{ states('sensor.average_temperature') }},
              "energy_usage": {{ states('sensor.current_power') }},
              "last_updated": "{{ now().isoformat() }}"
            }
          headers:
            Content-Type: "application/json"
            Authorization: "Bearer abc123"
```

## Sensor Configuration Examples

When setting up sensors through the GUI, here are some example configurations:

### Weather API Sensor
- **Name**: Weather API Status
- **URL**: `http://api.weather.com/status`
- **Method**: GET
- **Interval**: 300 (5 minutes)
- **Timeout**: 15
- **SSL Verify**: true
- **Enabled**: true

### Device Status with Authentication
- **Name**: Security Camera Status
- **URL**: `https://{{ states('sensor.camera_ip') }}/api/status`
- **Method**: GET
- **Interval**: 60 (1 minute)
- **Timeout**: 10
- **SSL Verify**: false
- **Query String**: `token={{ states('input_text.camera_token') }}`
- **Enabled**: true

### POST Request Sensor
- **Name**: Log Entry Sender
- **URL**: `http://logging-server.local/api/logs`
- **Method**: POST
- **Interval**: 3600 (1 hour)
- **Timeout**: 30
- **SSL Verify**: true
- **Payload**: `{"source": "home-assistant", "level": "info", "message": "Heartbeat from {{ states('sensor.hostname') }}"}`
- **Enabled**: true

## Template Examples

### Dynamic URL based on time of day
```
http://api.example.com/{{ 'day' if now().hour > 6 and now().hour < 18 else 'night' }}/data
```

### Conditional payload
```json
{
  "status": "{{ 'home' if is_state('device_tracker.phone', 'home') else 'away' }}",
  "lights_on": {{ state_attr('light.all_lights', 'brightness') | int > 0 | lower }},
  "security_armed": {{ is_state('alarm_control_panel.home', 'armed_away') | lower }}
}
```

### Query string with multiple sensors
```
mode={{ states('input_select.mode') }}&temp={{ states('sensor.temperature') }}&time={{ now().strftime('%H:%M') }}
```

## Icon Status Reference

Your HTTP sensors will automatically display different icons based on their status:

| Icon | Status | Description |
|------|--------|-------------|
| 🟢 `mdi:web-check` | Success | HTTP 200-299 response |
| 🔴 `mdi:web-remove` | Error | HTTP 400+ error or connection failure |
| 🟡 `mdi:web-clock` | Timeout | Request timed out |
| ⚫ `mdi:web-off` | Disabled | Sensor is disabled |
| 🔵 `mdi:web` | Unknown | Initial state or pending request |

This provides immediate visual feedback about the health of your HTTP endpoints directly in the Home Assistant UI.