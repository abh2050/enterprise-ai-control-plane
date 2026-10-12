#!/usr/bin/env bash
# Deploy the Enterprise AI Control Plane to GCP (Section 10).
#
#   scripts/deploy_gcp.sh PROJECT_ID [REGION] [OWNER_EMAIL]
#
# Order: APIs, Firestore, service accounts, IAM, Artifact Registry, bucket, BigQuery,
# image build, Cloud Run service behind IAP, seed data, Cloud Run jobs, Scheduler, smoke
# checks. Every step is idempotent. No principal is granted project Editor.
set -euo pipefail

PROJECT="${1:?usage: deploy_gcp.sh PROJECT_ID [REGION] [OWNER_EMAIL]}"
REGION="${2:-us-central1}"
OWNER="${3:-$(gcloud config get-value account 2>/dev/null)}"
SERVICE="control-plane"
REPO="control-plane"
BUCKET="${PROJECT}-control-plane"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%s)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/control-plane:${TAG}"
NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
AUDIENCE="/projects/${NUMBER}/locations/${REGION}/services/${SERVICE}"
SA_CONSOLE="cp-console@${PROJECT}.iam.gserviceaccount.com"
SA_JOBS="cp-jobs@${PROJECT}.iam.gserviceaccount.com"
SA_SCHEDULER="cp-scheduler@${PROJECT}.iam.gserviceaccount.com"
SMOKE=(cp-smoke-admin cp-smoke-owner cp-smoke-exec)
G="gcloud --project=${PROJECT} --quiet"

log() { printf '\n== %s\n' "$*"; }

log "1. Enable APIs"
$G services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  firestore.googleapis.com bigquery.googleapis.com storage.googleapis.com iap.googleapis.com \
  cloudscheduler.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com

log "2. Firestore (Native mode)"
if ! $G firestore databases describe --database='(default)' >/dev/null 2>&1; then
  # A just-enabled API can take a few minutes to propagate.
  for attempt in 1 2 3 4 5 6 7 8; do
    $G firestore databases create --location="$REGION" --type=firestore-native && break
    [ "$attempt" = 8 ] && exit 1
    echo "Firestore API not ready yet; retrying in 30 s ($attempt/8)"; sleep 30
  done
fi

log "3. Service accounts"
for sa in cp-console cp-jobs cp-scheduler "${SMOKE[@]}"; do
  $G iam service-accounts describe "${sa}@${PROJECT}.iam.gserviceaccount.com" >/dev/null 2>&1 \
    || $G iam service-accounts create "$sa" --display-name="control plane ${sa#cp-}"
done

log "4. Project-level IAM (least privilege)"
bind() { $G projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$1" --role="$2" \
  --condition=None >/dev/null; }
bind "$SA_CONSOLE" roles/datastore.user
bind "$SA_JOBS" roles/datastore.user
bind "$SA_JOBS" roles/aiplatform.user
bind "$SA_JOBS" roles/bigquery.jobUser
bind "$SA_CONSOLE" roles/bigquery.jobUser
# Cloud Build runs as the Compute Engine default service account in new projects.
BUILD_SA="${NUMBER}-compute@developer.gserviceaccount.com"
bind "$BUILD_SA" roles/artifactregistry.writer
bind "$BUILD_SA" roles/logging.logWriter
bind "$BUILD_SA" roles/storage.objectViewer
# The deployer signs smoke-test JWTs as the smoke service accounts.
for sa in "${SMOKE[@]}"; do
  $G iam service-accounts add-iam-policy-binding "${sa}@${PROJECT}.iam.gserviceaccount.com" \
    --member="user:${OWNER}" --role=roles/iam.serviceAccountTokenCreator >/dev/null
done

log "5. Artifact Registry"
$G artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 \
  || $G artifacts repositories create "$REPO" --location="$REGION" --repository-format=docker

log "6. Cloud Storage bucket (exports and the frozen classifier binary)"
gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://${BUCKET}" --project="$PROJECT" --location=US \
       --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_JOBS}" --role=roles/storage.objectAdmin >/dev/null
if [ -f artifacts/models/classifier_v1.pkl ]; then
  gcloud storage cp artifacts/models/classifier_v1.pkl "gs://${BUCKET}/models/" --project="$PROJECT"
fi

log "7. BigQuery dataset and tables (US)"
bq --project_id="$PROJECT" query --use_legacy_sql=false < infra/bigquery.sql >/dev/null
# Dataset-scoped grants through BigQuery DCL (bq add-iam-policy-binding needs allowlisting).
bq --project_id="$PROJECT" query --use_legacy_sql=false \
  "GRANT \`roles/bigquery.dataEditor\` ON SCHEMA \`${PROJECT}.control_plane\` TO \"serviceAccount:${SA_JOBS}\"" >/dev/null
bq --project_id="$PROJECT" query --use_legacy_sql=false \
  "GRANT \`roles/bigquery.dataViewer\` ON SCHEMA \`${PROJECT}.control_plane\` TO \"serviceAccount:${SA_CONSOLE}\"" >/dev/null

log "8. Build the image with Cloud Build"
if $G artifacts docker images describe "$IMAGE" >/dev/null 2>&1; then
  echo "Image ${IMAGE} already exists; skipping the build."
else
  $G builds submit --region="$REGION" --tag "$IMAGE" .
fi

ENV_COMMON="STORE_BACKEND=firestore,GCP_PROJECT=${PROJECT},PROVIDER_MODE=vertex,VERTEX_LOCATION=global,ANALYTICS_BACKEND=bigquery,EXPORT_BUCKET=${BUCKET},MODEL_BUCKET=${BUCKET},IAP_AUDIENCE=${AUDIENCE},BUDGET_APP_DAILY_USD=6,BUDGET_EXPERIMENT_USD=10,BUDGET_EXPERIMENT_TOTAL_USD=10"

log "9. Cloud Run service behind IAP"
$G run deploy "$SERVICE" --region="$REGION" --image="$IMAGE" --service-account="$SA_CONSOLE" \
  --no-allow-unauthenticated --iap --min-instances=0 --max-instances=2 --memory=1Gi \
  --set-env-vars="IDENTITY_MODE=iap,${ENV_COMMON}" || {
  echo "If IAP failed to enable: this project has no organization, so the first IAP"
  echo "enablement must be done once in the console (Cloud Run > ${SERVICE} > Security >"
  echo "Identity-Aware Proxy), which also configures the OAuth consent screen. Then re-run."
  exit 1
}
$G run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
  --member="serviceAccount:service-${NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role=roles/run.invoker >/dev/null
for member in "user:${OWNER}" $(printf 'serviceAccount:%s@'"${PROJECT}"'.iam.gserviceaccount.com ' "${SMOKE[@]}"); do
  $G iap web add-iam-policy-binding --resource-type=cloud-run --service="$SERVICE" \
    --region="$REGION" --member="$member" --role=roles/iap.httpsResourceAccessor >/dev/null
done

log "10. Seed Firestore: SYNTHETIC registry, measured evidence, and users"
STORE_BACKEND=firestore GCP_PROJECT="$PROJECT" uv run cp seed-registry
STORE_BACKEND=firestore GCP_PROJECT="$PROJECT" uv run cp users set-role "$OWNER" governance_admin
STORE_BACKEND=firestore GCP_PROJECT="$PROJECT" uv run cp users set-role \
  "cp-smoke-admin@${PROJECT}.iam.gserviceaccount.com" governance_admin
STORE_BACKEND=firestore GCP_PROJECT="$PROJECT" uv run cp users set-role \
  "cp-smoke-owner@${PROJECT}.iam.gserviceaccount.com" app_owner
STORE_BACKEND=firestore GCP_PROJECT="$PROJECT" uv run cp users set-role \
  "cp-smoke-exec@${PROJECT}.iam.gserviceaccount.com" executive_viewer

log "11. Cloud Run jobs (evaluate, shadow, monitor, export)"
job() {
  local name="$1"; shift
  $G run jobs deploy "$name" --region="$REGION" --image="$IMAGE" --service-account="$SA_JOBS" \
    --memory=2Gi --task-timeout=3600 --max-retries=0 \
    --set-env-vars="IDENTITY_MODE=iap,${ENV_COMMON}" --command=sh --args="-c,$*" >/dev/null
}
job cp-evaluate "cp smoke triage"
job cp-shadow "cp data fetch && cp model fetch && cp shadow llm_high_capability_v1"
job cp-monitor "cp monitor nightly"
job cp-export "cp export"
for j in cp-evaluate cp-shadow cp-monitor cp-export; do
  $G run jobs add-iam-policy-binding "$j" --region="$REGION" \
    --member="serviceAccount:${SA_CONSOLE}" --role=roles/run.invoker >/dev/null
done
for j in cp-monitor cp-export; do
  $G run jobs add-iam-policy-binding "$j" --region="$REGION" \
    --member="serviceAccount:${SA_SCHEDULER}" --role=roles/run.invoker >/dev/null
done

log "12. Cloud Scheduler (nightly monitor and export)"
for spec in "cp-monitor-nightly cp-monitor 0 2 * * *" "cp-export-nightly cp-export 30 2 * * *"; do
  read -r sched target m h dom mon dow <<<"$spec"
  uri="https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/${target}:run"
  if $G scheduler jobs describe "$sched" --location="$REGION" >/dev/null 2>&1; then
    $G scheduler jobs update http "$sched" --location="$REGION" --schedule="$m $h $dom $mon $dow" \
      --uri="$uri" --http-method=POST --oauth-service-account-email="$SA_SCHEDULER" >/dev/null
  else
    $G scheduler jobs create http "$sched" --location="$REGION" --schedule="$m $h $dom $mon $dow" \
      --time-zone=UTC --uri="$uri" --http-method=POST \
      --oauth-service-account-email="$SA_SCHEDULER" >/dev/null
  fi
done

log "13. Smoke checks"
URL="$($G run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
scripts/smoke_gcp.sh "$PROJECT" "$REGION" "$URL" "$AUDIENCE"
echo "Deployed ${URL}"
