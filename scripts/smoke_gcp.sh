#!/usr/bin/env bash
# Smoke checks against the deployed control plane (Section 10, item 7).
#
#   scripts/smoke_gcp.sh PROJECT REGION SERVICE_URL IAP_AUDIENCE
#
# Callers authenticate through IAP as service accounts with self-signed JWTs (IAP's
# programmatic access for the Google-managed OAuth client). Their roles come from
# Firestore like any user's.
set -euo pipefail
PROJECT="$1" REGION="$2" URL="$3"
G="gcloud --project=${PROJECT} --quiet"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok() { echo "PASS  $*"; pass=$((pass + 1)); }
bad() { echo "FAIL  $*"; fail=$((fail + 1)); }

token() {  # self-signed JWT for a smoke service account, audience = service URL
  local sa="$1@${PROJECT}.iam.gserviceaccount.com" now; now=$(date +%s)
  printf '{"iss":"%s","sub":"%s","aud":"%s/*","iat":%s,"exp":%s}' \
    "$sa" "$sa" "$URL" "$now" "$((now + 900))" > "$TMP/claim.json"
  gcloud iam service-accounts sign-jwt --iam-account="$sa" "$TMP/claim.json" "$TMP/jwt" \
    --project="$PROJECT" --quiet 2>/dev/null
  cat "$TMP/jwt"
}
code() { curl -s -o "$TMP/body" -w '%{http_code}' "$@"; }

# 1. An unauthenticated request is rejected.
c=$(code "$URL/api/me")
[[ "$c" =~ ^(401|403|302)$ ]] && ok "unauthenticated request rejected ($c)" || bad "unauthenticated got $c"

# 2. A forged IAP header is rejected, at IAP and inside the deployed backend.
c=$(code -H "x-goog-iap-jwt-assertion: eyJhbGciOiJFUzI1NiJ9.eyJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIn0.c2ln" "$URL/api/me")
[[ "$c" =~ ^(401|403|302)$ ]] && ok "forged IAP header rejected at the edge ($c)" || bad "forged header got $c"
if $G run jobs execute cp-evaluate --region="$REGION" --wait --args="-c,cp smoke auth" >/dev/null 2>&1; then
  ok "deployed backend rejects forged, missing, and fixture assertions (cp smoke auth)"
else
  bad "cp smoke auth job failed"
fi

EXEC=$(token cp-smoke-exec); ADMIN=$(token cp-smoke-admin)

# Authenticated reads work, which proves the IAP path and role lookup.
c=$(code -H "Authorization: Bearer $EXEC" "$URL/api/me")
[[ "$c" == 200 ]] && grep -q executive_viewer "$TMP/body" && ok "executive viewer authenticated through IAP" || bad "exec /api/me got $c $(cat "$TMP/body")"

# 3. An executive_viewer cannot write.
c=$(code -X POST -H "Authorization: Bearer $EXEC" -H "Content-Type: application/json" \
  -d '{"to_stage":"retired","expected_version":1,"reason":"smoke"}' "$URL/api/apps/meeting-notes/move")
[[ "$c" == 403 ]] && ok "executive viewer cannot write (403)" || bad "exec write got $c"

# 4. A submitter cannot approve their own gate.
v=$(curl -s -H "Authorization: Bearer $ADMIN" "$URL/api/apps/policy-qa" | python3 -c 'import json,sys; print(json.load(sys.stdin)["app"]["version"])')
c=$(code -X POST -H "Authorization: Bearer $ADMIN" -H "Content-Type: application/json" \
  -d "{\"to_stage\":\"review_gates\",\"expected_version\":${v},\"source\":\"api\"}" "$URL/api/apps/policy-qa/move")
[[ "$c" == 200 ]] || bad "admin submit got $c $(cat "$TMP/body")"
c=$(code -X POST -H "Authorization: Bearer $ADMIN" -H "Content-Type: application/json" \
  -d '{"decision":"approve","reason":"smoke"}' "$URL/api/apps/policy-qa/gates/governance")
[[ "$c" == 403 ]] && grep -q "different person" "$TMP/body" && ok "submitter cannot approve own gate (403)" || bad "self-approve got $c $(cat "$TMP/body")"

# 5. A live triage call settles its cost (job runs cp smoke triage through the ledger).
if $G run jobs execute cp-evaluate --region="$REGION" --wait >/dev/null 2>&1; then
  ok "live triage call settled its cost (cp smoke triage)"
else
  bad "live triage job failed"
fi

# Export idempotency: run export twice; BigQuery totals must not change.
total() {
  bq --project_id="$PROJECT" query --use_legacy_sql=false --format=csv \
    'SELECT (SELECT COUNT(*) FROM control_plane.app_events) + (SELECT COUNT(*) FROM control_plane.experiment_results) + (SELECT COUNT(*) FROM control_plane.shadow_results) + (SELECT COUNT(*) FROM control_plane.attempts) + (SELECT COUNT(*) FROM control_plane.incidents) + (SELECT COUNT(*) FROM control_plane.app_snapshots)' | tail -1
}
$G run jobs execute cp-export --region="$REGION" --wait >/dev/null; first=$(total)
$G run jobs execute cp-export --region="$REGION" --wait >/dev/null; second=$(total)
[[ "$first" == "$second" && "$first" -gt 0 ]] && ok "export is idempotent (${first} rows after each run)" || bad "export totals ${first} then ${second}"

echo; echo "${pass} passed, ${fail} failed"
[[ "$fail" == 0 ]]
