#!/bin/bash
# Device-flow login. Reads DEVICE_CODE from env (must match the code shown to user).
set -u
INTERVAL=5
for i in $(seq 1 120); do
  sleep "$INTERVAL"
  POLL=$(curl -s -X POST -H "Accept: application/json" \
    -d "client_id=178c6fc778ccc68e1d6a&device_code=${DEVICE_CODE}&grant_type=urn:ietf:params:oauth:grant-type:device_code" \
    https://github.com/login/oauth/access_token)
  case "$POLL" in
    *access_token*)
      TOKEN=$(printf '%s' "$POLL" | sed 's/.*"access_token":"\([^"]*\)".*/\1/')
      if ! echo "$TOKEN" | timeout 20 gh auth login --with-token 2>/dev/null; then
        mkdir -p ~/.config/gh
        LOGIN=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/user | sed 's/.*"login": *"\([^"]*\)".*/\1/')
        printf 'github.com:\n    users:\n        %s:\n            oauth_token: %s\n    git_protocol: https\n    oauth_token: %s\n    user: %s\n' \
          "$LOGIN" "$TOKEN" "$TOKEN" "$LOGIN" > ~/.config/gh/hosts.yml
        chmod 600 ~/.config/gh/hosts.yml
      fi
      gh auth setup-git && echo LOGIN_COMPLETE
      exit 0 ;;
    *authorization_pending*) : ;;
    *slow_down*) INTERVAL=$((INTERVAL + 5)) ;;
    *expired_token*) echo CODE_EXPIRED; exit 1 ;;
    *access_denied*) echo USER_DENIED; exit 1 ;;
    *) echo "UNEXPECTED: $POLL"; exit 1 ;;
  esac
done
echo TIMED_OUT
