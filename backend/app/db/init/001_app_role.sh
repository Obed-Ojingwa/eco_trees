#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=app_password="$DB_APP_PASSWORD" <<'SQL'
CREATE ROLE ecotrees LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE ecotrees TO ecotrees;
GRANT USAGE ON SCHEMA public TO ecotrees;
ALTER DEFAULT PRIVILEGES FOR ROLE ecotrees_admin IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ecotrees;
SQL
