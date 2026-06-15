# Matrix stack — first-run setup

Self-hosted Matrix homeserver (Synapse) + bridges for Telegram and WhatsApp.
gomuks is the single TUI client for both.

Data lives at `/mnt/data/matrix-data/` (symlinked as `matrix/data`).
Run `vjupdate → matrix` to pull images and create the data dir.

---

## Phase 1 — Synapse init

```bash
# Generate Synapse config
docker run --rm -v /mnt/data/matrix-data/synapse:/data \
  matrixdotorg/synapse generate --server-name localhost

# Start Synapse only (bridges need config first)
cd ~/Projects/dots/matrix && docker compose up -d synapse

# Wait for healthy, then register your user
docker exec -it synapse register_new_matrix_user \
  -c /data/homeserver.yaml -u viridjan -p YOUR_PASSWORD --no-admin \
  http://localhost:8008
```

---

## Phase 2 — Bridge registration

Each bridge generates a `config.yaml` on first run. Edit it to point at Synapse,
then run again to produce `registration.yaml`.

### mautrix-whatsapp

```bash
# Generate default config
docker compose run --rm mautrix-whatsapp

# Edit config — set homeserver address to container name:
#   data/whatsapp/config.yaml → homeserver.address: http://synapse:8008
#                              → homeserver.domain: localhost
#                              → appservice.address: http://mautrix-whatsapp:29318

# Re-run to generate registration.yaml
docker compose run --rm mautrix-whatsapp
```

### mautrix-telegram

```bash
# Generate default config
docker compose run --rm mautrix-telegram

# Edit config:
#   data/telegram/config.yaml → homeserver.address: http://synapse:8008
#                              → homeserver.domain: localhost
#                              → appservice.address: http://mautrix-telegram:29317
#   Also set telegram.api_id and telegram.api_hash
#   (get from https://my.telegram.org → API development tools)

# Re-run to generate registration.yaml
docker compose run --rm mautrix-telegram
```

### Register bridges with Synapse

Add to `data/synapse/homeserver.yaml`:
```yaml
app_service_config_files:
  - /data/whatsapp/registration.yaml
  - /data/telegram/registration.yaml
```

Note: the `/data/` path is inside the Synapse container (mapped from `./data/synapse`).
Copy or symlink the registration files into the synapse data dir:
```bash
cp /mnt/data/matrix-data/whatsapp/registration.yaml /mnt/data/matrix-data/synapse/whatsapp-registration.yaml
cp /mnt/data/matrix-data/telegram/registration.yaml /mnt/data/matrix-data/synapse/telegram-registration.yaml
```
Then reference:
```yaml
app_service_config_files:
  - /data/whatsapp-registration.yaml
  - /data/telegram-registration.yaml
```

---

## Phase 3 — Start and link accounts

```bash
# Start full stack
cd ~/Projects/dots/matrix && docker compose up -d

# Launch gomuks and log in
gomuks
# homeserver: http://localhost:8008
# username: @viridjan:localhost

# In gomuks — link WhatsApp:
#   Start DM with @whatsappbot:localhost → follow QR code instructions

# In gomuks — link Telegram:
#   Start DM with @telegrambot:localhost → enter phone number + auth code
```

---

## Day-to-day usage

```bash
start-matrix          # starts stack + opens gomuks (stack stays running on exit)
docker compose -f ~/Projects/dots/matrix/docker-compose.yml down   # stop stack
docker logs synapse   # check Synapse logs
docker logs mautrix-whatsapp
docker logs mautrix-telegram
```
