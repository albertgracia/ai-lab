#!/usr/bin/env bash

ALLOWED_COMMANDS=(
  "docker ps"
  "docker images"
  "docker logs"
  "docker inspect"
  "docker network ls"
  "docker volume ls"
  "docker stats"
)

cmd="$*"

for allowed in "${ALLOWED_COMMANDS[@]}"; do
  if [[ "$cmd" == "$allowed"* ]]; then
    exec $cmd
  fi
done

echo "Command not allowed"
exit 1
