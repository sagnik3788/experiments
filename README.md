# PromptSafely - infra

This repository holds the infrastructure manifests and environment variable files used as the deployment manifest for PromptSafely. It is primarily used by our continuous-delivery flow: a Docker Hub webhook updates the image reference (in the staging env file), and the updated manifest is then deployed to the staging VM. Production changes are made via pull request and applied only after review.

## Repository layout

- `infra.tf` - Terraform root (manifests / resources). Currently a placeholder for the project infra.
- `manifests/staging.tfvars` - Staging environment variables. The Docker Hub webhook/agent replaces the `image` value here when new images are pushed.
- `manifests/production.tfvars` - Production environment variables (apply changes via PR + review).
- `README.md` - This file.

## CD workflow (high level)

1. Build and push a Docker image to Docker Hub (for example: `sagnik3788/promptsafely:TAG`).
2. Docker Hub webhook notifies our bot/agent which updates the `image` variable line in `manifests/staging.tfvars` to the new image reference.
3. The updated manifest is deployed to the staging VM (either automatically by CI or manually by an operator) using Terraform with the staging var-file.
4. If staging looks good, update `manifests/production.tfvars` and create a Pull Request. After review and merge, apply the production manifest to production hosts (manual or CI-driven as configured).

## How to update the image (manual)

If you need to change the image manually (for example to test a specific tag), edit `manifests/staging.tfvars` and update the `image` line. Example:

```h
image = "sagnik3788/promptsafely:latest"
```

Then deploy to the staging VM. Typical commands (run on the deployment host or CI job):

```bash
cd /path/to/PromptSafely-infra
terraform init
terraform plan -var-file=manifests/staging.tfvars
terraform apply -var-file=manifests/staging.tfvars -auto-approve
```

Replace `manifests/staging.tfvars` with `manifests/production.tfvars` for production deployments (production changes should go through a PR and review process before applying).

## Important variables (examples)

- `image` - Docker image reference deployed by the manifest (e.g. `sagnik3788/promptsafely:latest`).
- `replica_count` - Number of replicas for the service (staging example: `2`).
- `service_port` - Port the service listens on (staging example: `8080`).
- `environment` - Logical environment name (`staging` / `production`).

These variables live in the `manifests/*.tfvars` files. Keep sensitive secrets out of this repository — use a secrets manager if needed.

## Production flow

- Make desired changes to `manifests/production.tfvars` or other manifests.
- Open a Pull Request, request review and run your CI checks.
- After approval and merge, apply the infrastructure change to production hosts (via CI or an operator-run `terraform apply`).

## Troubleshooting

- If Terraform complains about missing providers or modules, run `terraform init` first.
- If the webhook did not update `manifests/staging.tfvars`, check the webhook/agent logs and repository permissions.
- If a deployment fails, check the target VM logs and the Terraform plan output to identify resource or IAM issues.

## Notes

- This README documents the minimal workflow used today. As the infra grows, consider adding automated CI jobs that both update var-files and run `terraform plan`/`apply` behind protected branches and approvals.

## Contact

For questions about the deployment flow, reach out to the team or the repository owner.

---

Quick reference: the staging image is currently stored in `manifests/staging.tfvars` (the `image` variable).
