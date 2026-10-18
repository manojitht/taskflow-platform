# TaskFlow: a hands-on full-stack + DevOps learning project

FastAPI + Jinja2 + PostgreSQL, packaged with Docker, deployed to Kubernetes (EKS) on AWS,
provisioned with Terraform, shipped by GitHub Actions.

Do the steps in order. Each one ends with a "prove it" check, and an exercise that makes you
change something yourself. That is where the learning happens.

## Step 1: Run it locally without Docker (understand the app)
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    docker run -d --name pg -e POSTGRES_USER=taskflow -e POSTGRES_PASSWORD=taskflow \
      -e POSTGRES_DB=taskflow -p 5432:5432 postgres:16-alpine
    export DATABASE_URL=postgresql+psycopg://taskflow:taskflow@localhost:5432/taskflow
    export SECRET_KEY=dev-secret
    uvicorn app.main:app --reload
Prove it: open http://localhost:8000, sign up, add tasks, move them, log out and in.
Read in this order: `models.py` > `security.py` > `deps.py` > `routers/auth.py` > `routers/tasks.py` > templates.
Exercises: (a) open `/docs`, note that these HTML routes are not JSON APIs; add a `GET /api/tasks`
JSON endpoint using the same `current_user` dependency. (b) Try to delete another user's task by id
and confirm you get a 404 (see `_own_task`).

## Step 2: Tests and Git
    pytest -q
    git init && git add . && git commit -m "TaskFlow v1"
Create a GitHub repo and push. Exercise: add a test that signs up, logs in and creates a task
(use a SQLite or a throwaway Postgres DB via a pytest fixture).

## Step 3: Real migrations with Alembic (production habit)
    pip install alembic && alembic init migrations
Point `migrations/env.py` at `app.models.Base.metadata` and `settings.database_url`, run
`alembic revision --autogenerate -m "init"`, then `alembic upgrade head`. Remove `create_all`
from `main.py`. Exercise: add a `due_date` column to Task via a new migration.
In Kubernetes you run `alembic upgrade head` as a Job or init step before the Deployment rolls out.

## Step 4: Docker + Compose
    cp .env.example .env
    docker compose up --build
Prove it: http://localhost:8000 works; `docker compose down && docker compose up` keeps your data
(named volume). Exercise: run `docker exec` into the web container, check `whoami` (non-root), and
shrink the image by trying `python:3.12-slim` vs `alpine`, comparing with `docker images`.

## Step 5: Terraform your AWS infrastructure
Prereqs: AWS account, AWS CLI configured, Terraform >= 1.6.
    cd terraform && terraform init && terraform plan && terraform apply
Creates: VPC (public/private/DB subnets), EKS cluster, ECR repo, private RDS Postgres reachable
only from the cluster nodes. EKS + NAT + RDS cost money (roughly $5/day), so run
`terraform destroy` when you finish a session.
Exercises: move state to S3 + DynamoDB lock (commented block in `main.tf`); put the DB password in
AWS Secrets Manager instead of only in state.

## Step 6: Connect to the cluster and create the app secret
    aws eks update-kubeconfig --name taskflow --region ap-south-1
    kubectl create namespace taskflow
    kubectl -n taskflow create secret generic taskflow-secrets \
      --from-literal=DATABASE_URL="$(cd terraform && terraform output -raw database_url)" \
      --from-literal=SECRET_KEY="$(openssl rand -hex 32)"
Never commit secrets. Exercise: replace this with External Secrets Operator + Secrets Manager.

## Step 7: Install the AWS Load Balancer Controller
Needed so the `Ingress` in `k8s/app.yaml` creates an ALB. Follow the official AWS guide
(IAM policy, IRSA service account, Helm install `aws-load-balancer-controller` into `kube-system`).
This is the fiddliest step; budget time for it.

## Step 8: First manual deploy (before automating)
    aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ecr_url_host>
    docker build -t <ecr_url>:v1 . && docker push <ecr_url>:v1
    sed "s|IMAGE_PLACEHOLDER|<ecr_url>:v1|" k8s/app.yaml | kubectl apply -f -
    kubectl -n taskflow get pods,ingress
Prove it: open the ALB DNS name from `get ingress`. Exercises: `kubectl delete pod` and watch it
self-heal; break `DATABASE_URL` and watch `/readyz` fail so the pod gets no traffic; scale with
`kubectl scale`; read `kubectl describe hpa`.

## Step 9: Automate with GitHub Actions
1. In AWS IAM create an OIDC provider for `token.actions.githubusercontent.com` and a role that
   trusts your repo, with ECR push + `eks:DescribeCluster` permissions.
2. Map that role into the cluster (EKS access entry) with edit rights on namespace `taskflow`.
3. Add repo secret `AWS_DEPLOY_ROLE_ARN`.
4. Push to `main`: tests > build > push to ECR > `kubectl apply` > wait for rollout.
Exercise: push a change that fails a test and watch the deploy get blocked.

## Step 10: Harden (what separates a demo from production)
HTTPS via ACM certificate on the ALB and `COOKIE_SECURE=true` (already set in k8s); CSRF tokens on
forms; login rate limiting; structured JSON logs; metrics (Prometheus) and alerts; RDS Multi-AZ and
`skip_final_snapshot=false`; run migrations as a Job; image scanning in CI; Terraform in its own pipeline.

## Cleanup
    kubectl delete -f k8s/app.yaml   # removes the ALB first
    cd terraform && terraform destroy
