#!/usr/bin/env bash
# Attach a custom OAuth client to IAP for a project without a Google Cloud organization.
#
#   scripts/iap_oauth.sh PROJECT_ID PATH_TO_CLIENT_SECRET_JSON
#
# The JSON is the file the console offers to download when you create a Web application
# OAuth client. The secret is written only to a temporary file readable by you, passed to
# gcloud, and deleted. It is never printed.
set -euo pipefail
PROJECT="${1:?usage: iap_oauth.sh PROJECT_ID CLIENT_JSON}"
JSON="${2:?usage: iap_oauth.sh PROJECT_ID CLIENT_JSON}"
TMP="$(mktemp)"; chmod 600 "$TMP"; trap 'rm -f "$TMP"' EXIT

CLIENT_ID="$(python3 - "$JSON" "$TMP" <<'EOF'
import json, sys
data = json.load(open(sys.argv[1]))
web = data.get("web") or data.get("installed") or data
cid, secret = web["client_id"], web["client_secret"]
with open(sys.argv[2], "w") as fh:
    fh.write("access_settings:\n  oauth_settings:\n")
    fh.write(f"    client_id: {cid}\n    client_secret: {secret}\n")
print(cid)
EOF
)"
gcloud iap settings set "$TMP" --project="$PROJECT" --quiet >/dev/null
echo "IAP now uses OAuth client ${CLIENT_ID}"
echo "Its authorized redirect URI must be:"
echo "  https://iap.googleapis.com/v1/oauth/clientIds/${CLIENT_ID}:handleRedirect"
