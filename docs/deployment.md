# Deployment

This guide installs the project at `/opt/weather-morning-report` and runs it
daily at 08:30 in the `Asia/Shanghai` timezone using a systemd timer.

The deployment is independent from any existing weather scripts or cron jobs.

## 1. Prepare the service account

Run as root:

```bash
useradd --system --no-create-home --home-dir /opt/weather-morning-report \
  --shell /usr/sbin/nologin weather-report
install -d -o weather-report -g weather-report -m 750 \
  /opt/weather-morning-report
```

Clone or copy the repository into `/opt/weather-morning-report`, then set
ownership:

```bash
chown -R weather-report:weather-report /opt/weather-morning-report
```

## 2. Install the application

When Python 3.12 is already installed:

```bash
sudo -u weather-report python3.12 -m venv /opt/weather-morning-report/.venv
sudo -u weather-report /opt/weather-morning-report/.venv/bin/pip install \
  /opt/weather-morning-report
```

On systems such as Ubuntu 22.04 without Python 3.12, install an isolated
project runtime with `uv` instead of replacing the system Python:

```bash
sudo -u weather-report env HOME=/opt/weather-morning-report \
  sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u weather-report env HOME=/opt/weather-morning-report \
  XDG_CONFIG_HOME=/opt/weather-morning-report/.config \
  /opt/weather-morning-report/.local/bin/uv --no-config venv --python 3.12 \
  /opt/weather-morning-report/.venv
sudo -u weather-report env HOME=/opt/weather-morning-report \
  XDG_CONFIG_HOME=/opt/weather-morning-report/.config \
  /opt/weather-morning-report/.local/bin/uv --no-config pip install \
  --python /opt/weather-morning-report/.venv/bin/python \
  /opt/weather-morning-report
```

Create the runtime data directory:

```bash
install -d -o weather-report -g weather-report -m 700 \
  /opt/weather-morning-report/var
```

## 3. Configure secrets and delivery

Create `/opt/weather-morning-report/.env` from `.env.example`. Keep at least:

```dotenv
TIMEZONE=Asia/Shanghai
LOCATION_NAME=Changning District, Shanghai
LOCATION_QUERY=Changning,Shanghai
CACHE_PATH=/opt/weather-morning-report/var/weather_snapshot.json
SETTINGS_PATH=/opt/weather-morning-report/var/settings.json
```

Restrict the file:

```bash
chown weather-report:weather-report /opt/weather-morning-report/.env
chmod 600 /opt/weather-morning-report/.env
```

Delivery settings can live in `.env`, or in
`/opt/weather-morning-report/var/settings.json` created by the local settings
UI. Keep either file readable only by the service account.

## 4. Validate the installation

```bash
sudo -u weather-report bash -c 'cd /opt/weather-morning-report && \
  .venv/bin/weather-report preview'
```

This verifies the installed application and public weather-provider access
without loading SMTP credentials or sending email. The next step validates the
production `EnvironmentFile` and performs a real send.

## 5. Install the systemd timer

```bash
install -m 644 deploy/systemd/weather-morning-report.service \
  /etc/systemd/system/weather-morning-report.service
install -m 644 deploy/systemd/weather-morning-report.timer \
  /etc/systemd/system/weather-morning-report.timer
systemctl daemon-reload
systemd-run --wait --pipe --collect \
  --uid=weather-report \
  --working-directory=/opt/weather-morning-report \
  --property=EnvironmentFile=/opt/weather-morning-report/.env \
  /opt/weather-morning-report/.venv/bin/weather-report validate-config
systemctl start weather-morning-report.service
journalctl -u weather-morning-report.service -n 100 --no-pager
```

Confirm the manual service run sent the expected report before enabling the
timer.

```bash
systemctl enable --now weather-morning-report.timer
```

Verify that systemd parsed the Shanghai schedule:

```bash
systemctl list-timers weather-morning-report.timer
systemctl status weather-morning-report.timer
```

`Persistent=true` causes a missed run to execute after the VPS starts again.
It does not replace or modify existing cron jobs.

## 6. Operations

Trigger one run and inspect logs:

```bash
systemctl start weather-morning-report.service
journalctl -u weather-morning-report.service -n 100 --no-pager
```

After an application update:

```bash
sudo -u weather-report /opt/weather-morning-report/.venv/bin/pip install \
  /opt/weather-morning-report
systemctl restart weather-morning-report.timer
```

Disable only this project's schedule:

```bash
systemctl disable --now weather-morning-report.timer
```
