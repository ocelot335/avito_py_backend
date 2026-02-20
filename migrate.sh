#!/bin/bash

set -a
source .env
set +a

pgmigrate \
  -c "host=localhost port=${POSTGRES_PORT} dbname=${POSTGRES_DB} \
  user=${POSTGRES_USER} password=${POSTGRES_PASSWORD}" \
  -d . migrate -t latest