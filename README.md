# CI/CD for the code and for the infrastructure

**DevOps Career Starter Kit** · Tuesday, 2026-11-10, 17:00–19:00

On 11-03 a new image reached the cluster because someone edited a YAML and ran `kubectl apply` by
hand. Today you build it end to end, from scratch: two repositories, each with its own pull-request
checks and its own pipeline on `main`. At the end you change one word in the code and watch it
roll out to your EKS cluster, and nobody types `kubectl apply`.

| repo | template | what's in it |
|---|---|---|
| `service-code` | [kohanyirobert/csk-w10-service-code](https://github.com/kohanyirobert/csk-w10-service-code) | a Flask app with tests, two workflows that do nothing yet |
| `infra-code` | [kohanyirobert/csk-w10-infra-code](https://github.com/kohanyirobert/csk-w10-infra-code) | `main.tf` with providers and an S3 backend, two workflows that do nothing yet |

The steps say **what has to exist when**. How you build it is up to you: the hints are folded,
open them when you're stuck.

## Before you start

- AWS CLI v2 logged in to the `devops-csk2` account, Terraform ≥ 1.10, Docker, `kubectl`, `uv`,
  a GitHub account.
- **Your region and your name.** Everyone works in their own region (a region allows only 5 VPCs).
  Prefix everything you create with your name: the account is shared and IAM names are global.

  | name | region | name | region |
  |---|---|---|---|
  | andras | `eu-west-2` | kris | `us-west-2` |
  | atilla | `eu-west-3` | lorand | `ca-central-1` |
  | csepella | `eu-north-1` | richard | `us-west-1` |
  | daniel | `sa-east-1` | szino | `ap-south-1` |
  | gergely | `us-east-2` | robi (demo) | `eu-west-1` |

## 0. Your two repos and a state bucket

**Have at the end:** `<you>/service-code` and `<you>/infra-code` on GitHub, cloned; an S3 bucket
for the Terraform state; `terraform init` works in infra-code.

- On both template pages: **Use this template → Create a new repository**, public, under your own
  account. (Not a fork: in a fork Actions start disabled.)
- Create the bucket by hand. It can't be in the Terraform that stores its state in it.
- Fill in the `CHANGE-ME`s in `infra-code/main.tf`, `terraform init`.

<details>
<summary>Hints</summary>

```bash
aws s3api create-bucket --bucket <name>-csk-w10-tfstate --region <region> \
  --create-bucket-configuration LocationConstraint=<region>
aws s3api put-bucket-versioning --bucket <name>-csk-w10-tfstate \
  --versioning-configuration Status=Enabled
```

Versioning: a broken state can be rolled back. `use_lockfile = true` in the backend: two `apply`s at
once (you and the runner) can't both write.
</details>

## 1. infra-code: EKS, ECR and the GitHub roles (no Deployment yet)

**Have at the end:** a running EKS cluster with 2 nodes, an ECR repository, a `hello` namespace,
and two IAM roles GitHub Actions can assume. Applied from your laptop. No workflow yet.

EKS takes about 15 minutes: `apply` early, do step 2 while it runs.

<details>
<summary>Hints: network and cluster</summary>

- A VPC with two public subnets in two AZs (EKS wants at least two), an internet gateway, a route
  table with `0.0.0.0/0` to it, `map_public_ip_on_launch = true`. Nodes in public subnets: no NAT
  gateway needed. Take the AZs from `data "aws_availability_zones"`.
- `aws_eks_cluster` needs a role with `AmazonEKSClusterPolicy`. Set
  `access_config { authentication_mode = "API", bootstrap_cluster_creator_admin_permissions = true }`:
  you, who run the apply, become cluster admin.
- `aws_eks_node_group`: 2 × `t3.medium`, a role with `AmazonEKSWorkerNodePolicy`,
  `AmazonEKS_CNI_Policy` and **`AmazonEC2ContainerRegistryReadOnly`** (or the nodes can't pull
  your image).
- Load balancers, Ingress, add-ons: not today.
</details>

<details>
<summary>Hints: ECR</summary>

`aws_ecr_repository` named `<name>/hello`, `image_tag_mutability = "IMMUTABLE"`: a tag can be
pushed once, so `1.0.0` always means the same image. `force_delete = true` lets `destroy` remove it
with the images in it.
</details>

<details>
<summary>Hints: GitHub → AWS without access keys (OIDC)</summary>

- GitHub gives every workflow run a signed token. AWS checks it against an **OIDC provider** and
  hands out short-lived credentials for a role whose **trust policy** accepts that token.
- The provider exists once per account and `devops-csk2` already has it: use
  `data "aws_iam_openid_connect_provider"` with `url = "https://token.actions.githubusercontent.com"`.
  A `resource` fails with *EntityAlreadyExists*.
- Trust policy: `sts:AssumeRoleWithWebIdentity`, condition on
  `token.actions.githubusercontent.com:aud = sts.amazonaws.com` and on `...:sub`, which says which
  repo and which branch or event:

  | role | allowed `sub` | permissions |
  |---|---|---|
  | `<name>-gha-service` | `repo:<you>/service-code:ref:refs/heads/main` | push to your ECR repo (and `ecr:GetAuthorizationToken` on `*`) |
  | `<name>-gha-infra` | `repo:<you>/infra-code:pull_request`, `repo:<you>/infra-code:ref:refs/heads/main` | `AdministratorAccess`: it applies this same code, VPC, EKS, IAM and all |

- The infra role must also get into **Kubernetes**: `aws_eks_access_entry` +
  `aws_eks_access_policy_association` with `AmazonEKSClusterAdminPolicy`. Without it, the runner's
  plan says *Unauthorized*.
</details>

<details>
<summary>Hints: the namespace from Terraform</summary>

The `kubernetes` provider logs in the same way `kubectl` does:

```hcl
provider "kubernetes" {
  host                   = aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.this.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.this.name, "--region", "<region>"]
  }
}
```

Then `kubernetes_namespace_v1` named `hello`. Outputs worth having: both role ARNs, the ECR URL.
</details>

**Check:**
`aws eks update-kubeconfig --name <cluster> --region <region>`, `kubectl get nodes` (2 Ready),
`kubectl get ns hello`.

## 2. service-code: the workflows (while EKS is being created)

**Have at the end:** a `Dockerfile`; `pr.yml` runs the tests and builds the image on every PR;
`main.yml` runs the tests, then builds the image and pushes it to ECR, tagged with the version
from `pyproject.toml`.

Work on a branch, open a PR: the PR checks run on the PR that adds them. Merge it. `main.yml` will
fail at the AWS login: the role doesn't exist yet. That's expected, step 3 fixes it.

<details>
<summary>Hints: the Dockerfile</summary>

- `FROM python:3.13-slim`, copy `uv` in: `COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/`.
- Copy `pyproject.toml` and `uv.lock` first, `uv sync --locked --no-install-project`, then
  `app.py`. Change only `app.py` and rebuild: which layers are cached?
- Port 8080. `STOPSIGNAL SIGINT`: Python as PID 1 ignores `SIGTERM`, so without it every old Pod
  hangs 30 seconds in `Terminating`.
- ARM Mac building by hand: `--platform linux/amd64`, the nodes are x86.
</details>

<details>
<summary>Hints: the tests on the runner</summary>

`actions/checkout@v7`, `astral-sh/setup-uv@v10`, then `uv run python -m unittest -v`.
</details>

<details>
<summary>Hints: AWS login, ECR, the version</summary>

```yaml
permissions:
  contents: read
  id-token: write          # without this GitHub gives the job no OIDC token
steps:
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: ${{ vars.AWS_ROLE_ARN }}
      aws-region: ${{ vars.AWS_REGION }}
  - uses: aws-actions/amazon-ecr-login@v2
```

- Repo **variables**, not secrets (Settings → Secrets and variables → Actions → Variables):
  `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_REPOSITORY_URL`. None of them is secret: without the trust
  policy the role ARN is useless.
- The version, from one step to the next:
  ```yaml
  - id: version
    run: echo "version=$(uv version --short)" >> "$GITHUB_OUTPUT"
  - run: echo "${{ steps.version.outputs.version }}"
  ```
- The tag is the version: `<ECR_REPOSITORY_URL>:1.0.0`. Never `latest`.
</details>

## 3. service-code → ECR

**Have at the end:** `hello:1.0.0` in your ECR repository, pushed by GitHub Actions.

- When step 1's apply is done: set the repo variables from its outputs, then **Re-run failed jobs**
  on the failed `main.yml` run.

**Check:** `aws ecr list-images --repository-name <name>/hello --region <region>`.

<details>
<summary>Hints: it still fails</summary>

- *Not authorized to perform sts:AssumeRoleWithWebIdentity*: the `sub` in the trust policy doesn't
  match. Repo name, owner, branch: exactly. Missing `id-token: write`?
- *tag invalid … already exists*: immutable tags; bump the version.
</details>

## 4. infra-code: the Deployment, applied by hand

**Have at the end:** a Deployment `hello` in namespace `hello`, managed by Terraform, running the
image tag that's in ECR. Applied from your laptop.

- Write the Deployment as YAML in `k8s/deployment.yaml` (3 replicas, image
  `<ECR_REPOSITORY_URL>:1.0.0`, port 8080), and let Terraform read it.

<details>
<summary>Hints</summary>

```hcl
resource "kubernetes_manifest" "deployment" {
  manifest   = yamldecode(file("${path.module}/k8s/deployment.yaml"))
  depends_on = [kubernetes_namespace_v1.hello]
}
```

- A `readinessProbe` on `/` port 8080: a Pod gets traffic, and the rollout moves on, only when the
  app answers.
- `strategy.rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }`: one new Pod at a time; you'll see it
  in step 6.
- Pods in `ImagePullBackOff`: the node role lacks `AmazonEC2ContainerRegistryReadOnly`, or the tag
  isn't in ECR.
- `kubernetes_manifest` asks the cluster's API already at **plan** time. That's why it comes only
  now, when the cluster exists: in step 1's first plan it would fail.
</details>

**Check:**

```bash
kubectl -n hello get deploy,pods
kubectl -n hello exec deploy/hello -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8080').read())"
kubectl -n hello port-forward deploy/hello 8080:8080   # then, elsewhere: curl localhost:8080
```

The image has no `curl`; it has Python.

## 5. infra-code: the workflows

**Have at the end:** `pr.yml` runs `terraform fmt -check`, `init`, `validate`, `plan` on every PR;
`main.yml` does the same and then `apply`, without asking.

- Add the workflows on a branch, PR, merge. The first `main.yml` run should change nothing.
- Then test with a real change: `replicas: 3` → `5` in `k8s/deployment.yaml`, on a branch, PR. Read
  the plan in the PR's check. Merge. Watch the Pods appear.

<details>
<summary>Hints</summary>

- Repo variables: `AWS_REGION`, `AWS_ROLE_ARN` (the **infra** role).
- Same AWS login as in service-code, then `hashicorp/setup-terraform@v4`. The AWS CLI is already on
  `ubuntu-latest`; the kubernetes provider needs it for `aws eks get-token`.
- `-input=false` everywhere: nobody is there to answer.
- `terraform plan -out=tfplan`, then `terraform apply tfplan`: applies exactly what was planned, and
  doesn't ask, because a saved plan is already approved.
- Two merges close together: `concurrency: { group: apply, cancel-in-progress: false }` makes the
  second run wait.
- The state is in S3, so your laptop and the runner see the same thing. Don't apply from the laptop
  any more: from now on `main` is the truth.
- Plan says *Unauthorized* from Kubernetes: the infra role has no EKS access entry.
</details>

## 6. The whole loop

**Have at the end:** "Bye" in the cluster, and nothing done by hand except commits and merges.

0. Terminal, keep it open:
   ```bash
   kubectl -n hello get pods -w -o custom-columns='POD:.metadata.name,IMAGE:.spec.containers[0].image,READY:.status.containerStatuses[0].ready'
   ```
1. **service-code**, branch: `Hello` → `Bye` in `app.py`. The PR check goes red: fix the test too.
   Bump the version: `uv version --bump minor` (1.0.0 → 1.1.0). PR, green, merge.
2. Wait for `main.yml`: `hello:1.1.0` in ECR.
3. **infra-code**, branch: image tag `1.0.0` → `1.1.0` in `k8s/deployment.yaml`. PR: the plan shows
   one change, the image. Merge.
4. Wait for `main.yml`. In the terminal: a new Pod with `1.1.0`, ready, an old one goes; again and
   again. `curl` says Bye.

**Try next:** a tag that was never pushed (`9.9.9`). What does the plan say, what does apply say,
what does the terminal show? Is the app down? Fix it with another PR.

## Clean up

Today. A cluster with two nodes is about $0.20 an hour.

```bash
cd infra-code && terraform destroy
```

Then the bucket: S3 console → the bucket → **Empty** (it deletes the old versions too; `aws s3 rb
--force` doesn't, and fails on a versioned bucket) → **Delete**.
