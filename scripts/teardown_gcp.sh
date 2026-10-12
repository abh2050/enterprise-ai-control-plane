#!/usr/bin/env bash
# Remove every billed resource the deploy created, then list anything left (Section 10).
#
#   scripts/teardown_gcp.sh PROJECT_ID [REGION]
set -uo pipefail
PROJECT="${1:?usage: teardown_gcp.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
BUCKET="${PROJECT}-control-plane"
G="gcloud --project=${PROJECT} --quiet"

echo "== Scheduler jobs";  for j in cp-monitor-nightly cp-export-nightly; do $G scheduler jobs delete "$j" --location="$REGION" 2>/dev/null; done
echo "== Cloud Run jobs";  for j in cp-evaluate cp-shadow cp-monitor cp-export; do $G run jobs delete "$j" --region="$REGION" 2>/dev/null; done
echo "== Cloud Run service"; $G run services delete control-plane --region="$REGION" 2>/dev/null
echo "== Artifact Registry"; $G artifacts repositories delete control-plane --location="$REGION" 2>/dev/null
echo "== Cloud Storage";  gcloud storage rm -r "gs://${BUCKET}" --project="$PROJECT" --quiet 2>/dev/null
echo "== BigQuery dataset"; bq --project_id="$PROJECT" rm -r -f -d control_plane 2>/dev/null
echo "== Firestore database"; $G firestore databases delete --database='(default)' 2>/dev/null
echo "== Service accounts"
for sa in cp-console cp-jobs cp-scheduler cp-smoke-admin cp-smoke-owner cp-smoke-exec; do
  $G iam service-accounts delete "${sa}@${PROJECT}.iam.gserviceaccount.com" 2>/dev/null
done

echo; echo "== Anything left (should all be empty)"
$G scheduler jobs list --location="$REGION" --format='value(name)' 2>/dev/null | grep -E 'cp-' || true
$G run services list --region="$REGION" --format='value(metadata.name)' 2>/dev/null | grep control-plane || true
$G run jobs list --region="$REGION" --format='value(metadata.name)' 2>/dev/null | grep -E '^cp-' || true
$G artifacts repositories list --location="$REGION" --format='value(name)' 2>/dev/null | grep control-plane || true
gcloud storage ls --project="$PROJECT" 2>/dev/null | grep "$BUCKET" || true
bq --project_id="$PROJECT" ls 2>/dev/null | grep control_plane || true
$G firestore databases list --format='value(name)' 2>/dev/null || true
$G iam service-accounts list --format='value(email)' 2>/dev/null | grep -E '^cp-' || true
echo "Cloud Build source uploads in gs://${PROJECT}_cloudbuild are not removed automatically:"
gcloud storage ls "gs://${PROJECT}_cloudbuild" --project="$PROJECT" 2>/dev/null | head -3 || true
echo "(Enabled APIs are left on; they do not bill on their own.)"
