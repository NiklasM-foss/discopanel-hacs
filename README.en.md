# DiscoPanel for Home Assistant

*[Deutsch](README.md) · English*

A custom Home Assistant integration (HACS compatible) for
[DiscoPanel](https://github.com/nickheyer/discopanel), a management panel for
modded Minecraft servers (Fabric, Forge, NeoForge, Paper, Vanilla and more).

The integration adds every Minecraft server managed by DiscoPanel as its own
device in Home Assistant. From there you can start, stop and restart your
servers, send console commands, and monitor all the important runtime values
(player count, TPS, CPU, RAM, disk, world size, status, latency, MOTD) as
sensors and use them in automations.

## What it does

DiscoPanel is a manager for modded Minecraft servers. This integration talks to
DiscoPanel's local ConnectRPC API and creates a dedicated Home Assistant device
for each server. Data is polled locally (`iot_class: local_polling`), there is
no cloud communication.

## Features

The following entities are created per Minecraft server:

- **Switch** (on/off): server power switch. On = server running. Turning it on
  starts the server, turning it off stops it.
- **Button** (restart): restarts the server.
- **Sensors:**
  - Status (text, e.g. Running, Stopped, Starting; the raw enum value is
    available as an attribute)
  - Players online (with attributes for the maximum player count and the player
    list)
  - TPS (ticks per second)
  - CPU usage (percent)
  - Memory usage (MB, displayed as GB) and configured memory (diagnostic)
  - Disk usage and disk total (bytes)
  - World size (bytes)
  - Latency (Server List Ping, milliseconds, diagnostic)
  - Minecraft version, MOTD (diagnostic)
  - Diagnostic details: max players, port, proxy port (with hostname as an
    attribute), Java version, Docker image, container ID (with data path),
    last started and created (timestamps), server version, protocol and SLP
    values
- **Binary sensors:**
  - Running (device_class RUNNING, on when the server is running)
  - Reachable (device_class CONNECTIVITY, on when the server answers a Server
    List Ping)
  - Auto start and Detached (diagnostic)

Additionally, on the shared DiscoPanel hub device:

- **Sensor** Total players online (sum across all servers, with a per-server
  breakdown and the number of running servers as attributes)

## Installation

### Via HACS (custom repository)

1. Open HACS in Home Assistant.
2. Click the three-dot menu in the top right and choose **Custom
   repositories**.
3. Enter the following repository URL:
   `https://github.com/niklasm-foss/discopanel-hacs`
4. Select the **Integration** category and click **Add**.
5. Then search for **DiscoPanel** in the HACS store and install it.
6. Restart Home Assistant.

### Manual installation

1. Copy the `custom_components/discopanel` folder from this repository into your
   Home Assistant configuration directory so that the path
   `config/custom_components/discopanel/` exists.
2. Restart Home Assistant.

## Setup / Configuration

After installation, add the integration via
**Settings -> Devices & Services -> Add Integration** and search for
**DiscoPanel**. The dialog asks for:

- **Host:** IP address or hostname of your DiscoPanel instance.
- **Port:** default `8080`.
- **SSL:** enable if DiscoPanel is served over HTTPS.
- **Verify SSL certificate:** only relevant when SSL is enabled. Disable this
  for self-signed certificates.
- **API token:** a DiscoPanel API token (see below).

### Creating an API token

The integration authenticates with an API token that starts with the prefix
`dp_`. To create one:

1. Open the DiscoPanel web interface in your browser.
2. Go to your profile page and the **API Tokens** section.
3. Create a new token and copy the full value (it starts with `dp_`). The value
   is shown only once.
4. Paste that value into the **API token** field in the integration setup
   dialog.

The token is used unchanged as a bearer token. If it ever expires or is
revoked, Home Assistant will prompt you for a new one through the GUI
(reauthentication dialog).

### Options

Use **Configure** on the set-up integration to change the polling interval
(**scan_interval**). The default is 30 seconds, the minimum is 10 seconds.

## Service: send_command

The integration registers the service `discopanel.send_command`, which sends a
console command to a server and returns the command output.

Fields:

- `server_id` (required): the id of the target server (as assigned by
  DiscoPanel).
- `command` (required): the console command to send.
- `silent` (optional, default `true`): if `true`, the command is executed
  silently.

Example:

```yaml
service: discopanel.send_command
data:
  server_id: "abc123"
  command: "say Hello from Home Assistant"
  silent: true
```

## Notes

- The integration polls the DiscoPanel API locally (`local_polling`). There is
  no cloud dependency.
- Runtime values such as CPU, RAM or player count are usually only available
  while the server is running. For a stopped server these sensors may be empty
  or unknown.
- Each Minecraft server appears as its own device, and all servers are linked to
  a shared DiscoPanel hub device.

## Links

- Repository and issues:
  https://github.com/niklasm-foss/discopanel-hacs
