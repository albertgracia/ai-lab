#!/usr/bin/env bash

ALLOWED=(
  "ls"
  "cat"
  "grep"
  "find"
  "tail"
  "head"
  "pwd"
  "whoami"
  "df"
  "free"
  "docker ps"
  "docker logs"
  "docker inspect"
  "git status"
  "git diff"
  "git log"
)

cmd="$*"

for allowed in "${ALLOWED[@]}"; do
  if [[ "$cmd" == "$allowed"* ]]; then
    exec $cmd
  fi
done

echo "Command not allowed"
exit 1
