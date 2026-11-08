# Local SuiteCRM

SuiteCRM 8.10.2 from the official prebuilt distribution, running with PHP 8.3,
Apache 2.4 and MariaDB 11.4. Open http://localhost:8088 and log in as `admin`.
The generated password is `ADMIN_PASSWORD` in `.env` (excluded from Git).
SMTP and external email accounts require your own account settings in SuiteCRM.

From the dots repository:

```sh
docker compose -f suitecrm/compose.yaml up -d
docker compose -f suitecrm/compose.yaml stop
docker compose -f suitecrm/compose.yaml logs --tail=50
```

The containers restart with Docker. Only the loopback interface exposes the
web application; the database has no host port. Application files, uploads,
configuration and database records persist in the `dots-suitecrm_application`
and `dots-suitecrm_database` Docker volumes. Preserve both when backing up.
Do not use `down --volumes` unless you intend to erase the installation.

The scheduler runs every minute; the background worker consumes the
`internal-async` queue and restarts after its one-hour time limit. Admin login,
authenticated GraphQL access and scheduled jobs were verified during installation.

To rebuild, obtain `suitecrm-8.10.2.zip` from the official SuiteCRM download page
and place it in this directory, then run `docker compose -f suitecrm/compose.yaml
build web`. Rebuilding the image does not upgrade an existing application volume;
use SuiteCRM's documented upgrade process for existing installations.
