# CI/CD for service code and infrastructure code

DevOps CSK · 2026-11-10, 17:00–19:00

Goal: a change in `service-code` reaches your EKS cluster through two pipelines: build and push the
image, then deploy it with Terraform. No manual `kubectl apply`.

![Sequence: one change through both pipelines](diagram/sequence.svg)

Editable: [`diagram/sequence.excalidraw`](diagram/sequence.excalidraw) (excalidraw.com → Open).

## Repos

| your repo | create it from template |
|---|---|
| `service-code` | https://github.com/kohanyirobert/csk-w10-service-code |
| `infra-code` | https://github.com/kohanyirobert/csk-w10-infra-code (its README has snippets for every file) |

## Prerequisites

- AWS CLI v2 logged in to `devops-csk2`, Terraform, Docker, `kubectl`, `uv`, a GitHub account.
- Prefix every AWS resource with your name: the account is shared.
- Use your region:

| name | region |
|---|---|
| andras | `eu-west-1` |
| atilla | `eu-west-2` |
| csepella | `eu-west-3` |
| daniel | `eu-north-1` |
| richard | `eu-central-1` |
| gergely | `us-east-1` |
| kris | `us-east-2` |
| lorand | `us-west-1` |
| szino | `us-west-2` |
| robi (demo) | `eu-west-1` |

## 0. Repos and state bucket

Result: `<you>/service-code` and `<you>/infra-code` on GitHub, cloned; an S3 bucket for the state;
`terraform init` works in `infra-code`.

1. On both template pages: Use this template → Create a new repository, public, your account.
2. Create the state bucket: `aws s3 mb s3://<name>-csk-w10-tfstate --region <region>`.
3. Replace the `CHANGE-ME`s in `infra-code/main.tf`, run `terraform init`.

## 1. infra-code: EKS, ECR, GitHub roles

Result: an EKS cluster with 2 nodes, an ECR repository, a `hello` namespace, two IAM roles for
GitHub Actions. Applied from your laptop. No Deployment, no workflow yet.

The cluster takes ~15 minutes: start `terraform apply`, do step 2 meanwhile.

- `network.tf`: VPC, 2 public subnets in 2 AZs (EKS needs two), internet gateway, route table.
  `map_public_ip_on_launch = true`: without a NAT gateway, nodes need a public IP to reach EKS and
  ECR.
- `eks.tf`: cluster + node group (2 × `t3.medium`), each with its IAM role. The node role needs
  `AmazonEC2ContainerRegistryReadOnly` to pull your image.
  `bootstrap_cluster_creator_admin_permissions = true`: you, running the first apply, become admin.
- `ecr.tf`: repository `<name>/hello`, `IMMUTABLE` tags: a tag can be pushed only once, so every
  release needs a new version.
- `github-oidc.tf`: two roles GitHub Actions can assume without access keys.
  - The account already has the GitHub OIDC provider: use `data`, not `resource`.
  - The trust policy's `sub` condition says which repo and event may assume the role:

    | role | `sub` | permissions |
    |---|---|---|
    | `<name>-gha-service` | `repo:<you>/service-code:ref:refs/heads/main` | push to your ECR repository |
    | `<name>-gha-infra` | `repo:<you>/infra-code:pull_request`, `repo:<you>/infra-code:ref:refs/heads/main` | `AdministratorAccess` |

  - The infra role also needs an EKS access entry (`AmazonEKSClusterAdminPolicy`), or Terraform
    on the runner can't reach Kubernetes.
- `k8s.tf`: the `kubernetes` provider and the `hello` namespace.
- `outputs.tf`: both role ARNs and the ECR repository URL.

Check:

```bash
aws eks update-kubeconfig --name <cluster> --region <region>
kubectl get nodes
kubectl get ns hello
```

## 2. service-code: Dockerfile and workflows

Result: a `Dockerfile`; `pr.yml` runs the tests and builds the image on PRs; `main.yml` runs the
tests, builds the image, tags it with the version from `pyproject.toml` and pushes it to ECR on
pushes to `main`.

Add them on a branch, open a PR, merge. `main.yml` fails at the AWS login until step 1 is done.

- `Dockerfile`: `FROM python:3.13-slim`, copy `uv` in
  (`COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/`), copy the code, `uv sync --locked`, run
  `app.py` on port 8080. On an ARM Mac: `docker build --platform linux/amd64`.
- Tests: `actions/checkout@v7`, `astral-sh/setup-uv@v10`, `uv run python -m unittest -v`.
- AWS login and ECR:
  ```yaml
  permissions:
    contents: read
    id-token: write   # lets the job get an OIDC token
  steps:
    - uses: aws-actions/configure-aws-credentials@v6
      with:
        role-to-assume: ${{ vars.AWS_ROLE_ARN }}
        aws-region: ${{ vars.AWS_REGION }}
    - uses: aws-actions/amazon-ecr-login@v2
  ```
- Repo variables (Settings → Secrets and variables → Actions → Variables): `AWS_REGION`,
  `AWS_ROLE_ARN` (service role), `ECR_REPOSITORY_URL`.
- The version:
  ```yaml
  - id: version
    run: echo "version=$(uv version --short)" >> "$GITHUB_OUTPUT"
  ```
  Image: `${{ vars.ECR_REPOSITORY_URL }}:${{ steps.version.outputs.version }}`.

## 3. service-code → ECR

Result: `hello:1.0.0` in your ECR repository, pushed by GitHub Actions.

1. Set the service-code repo variables from step 1's outputs.
2. Actions → the failed `main.yml` run → Re-run failed jobs.

Check: `aws ecr list-images --repository-name <name>/hello --region <region>`.

`Not authorized to perform sts:AssumeRoleWithWebIdentity`: the `sub` in the trust policy doesn't
match the repo or branch.

## 4. infra-code: Deployment, applied by hand

Result: Deployment `hello` in namespace `hello`, managed by Terraform, running `hello:1.0.0` from
ECR. Applied from your laptop.

- `k8s/deployment.yaml`: 3 replicas, image `<ECR_REPOSITORY_URL>:1.0.0`, port 8080.
- `k8s.tf`: a `kubernetes_manifest` that reads the YAML with `yamldecode(file(...))`. It only works
  once the cluster exists: that's why it comes now.

Check (the image has Python, no `curl`):

```bash
kubectl -n hello get pods
kubectl -n hello exec deploy/hello -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8080').read())"
```

## 5. infra-code: workflows

Result: `pr.yml` runs `terraform fmt -check`, `init`, `validate`, `plan` on PRs; `main.yml` runs the
same plus `apply -auto-approve` on pushes to `main`.

1. Set the repo variables: `AWS_REGION`, `AWS_ROLE_ARN` (the infra role).
2. Add the workflows on a branch, PR, merge. The first `main.yml` run changes nothing.
3. Test: `replicas: 3` → `5` in `k8s/deployment.yaml`, on a branch, PR, read the plan, merge.

- Same AWS login as in service-code, then `hashicorp/setup-terraform@v4`.
- From now on apply only through `main`, not from your laptop.

## 6. The loop

Result: the new code runs in the cluster; nothing done by hand except commits and merges.

1. Terminal: `kubectl -n hello get pods -w`.
2. service-code, branch: `Hello` → `Bye` in `app.py` and `test_app.py`, `uv version --bump minor`
   (1.0.0 → 1.1.0). PR, merge. Wait for `main.yml`.
3. infra-code, branch: `1.0.0` → `1.1.0` in `k8s/deployment.yaml`. PR, merge. Wait for `main.yml`.
4. Terminal: new Pods replace the old ones. Check that the app now answers `Bye`.

## Clean up

```bash
terraform destroy                                  # in infra-code
aws s3 rb s3://<name>-csk-w10-tfstate --force      # the state bucket
```
