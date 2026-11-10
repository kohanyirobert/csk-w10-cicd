"""Writes pipeline.json, the Excalidraw skeleton of ../pipeline.svg.

python3 pipeline.py && ~/.agents/skills/diagrams/scripts/export -o .. pipeline.json
"""

import json
from pathlib import Path

P = {
    "blue": ("#a5d8ff", "#4a9eed"), "green": ("#b2f2bb", "#22c55e"), "orange": ("#ffd8a8", "#f59e0b"),
    "purple": ("#d0bfff", "#8b5cf6"), "red": ("#ffc9c9", "#ef4444"), "note": ("#fff3bf", "#f59e0b"),
    "grey": ("#e9ecef", "#868e96"), "teal": ("#c3fae8", "#06b6d4"),
}
E = []


def box(i, x, y, w, h, t, c, fs=18):
    f, s = P[c]
    E.append({"type": "rectangle", "id": i, "x": x, "y": y, "width": w, "height": h, "roundness": {"type": 3},
              "backgroundColor": f, "fillStyle": "solid", "strokeColor": s, "label": {"text": t, "fontSize": fs}})


def zone(i, x, y, w, h, c, title):
    f, s = P[c]
    E.append({"type": "rectangle", "id": i, "x": x, "y": y, "width": w, "height": h, "roundness": {"type": 3},
              "backgroundColor": f, "fillStyle": "solid", "strokeColor": s, "strokeWidth": 1, "opacity": 30})
    E.append({"type": "text", "id": i + "t", "x": x + 16, "y": y + 10, "text": title, "fontSize": 20})


def text(i, x, y, t, fs=17, col=None):
    e = {"type": "text", "id": i, "x": x, "y": y, "text": t, "fontSize": fs}
    if col:
        e["strokeColor"] = col
    E.append(e)


def arrow(i, a, b, x, y, pts, fa, fb, label=None, dashed=False):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    e = {"type": "arrow", "id": i, "x": x, "y": y, "width": max(xs) - min(xs), "height": max(ys) - min(ys),
         "points": pts, "endArrowhead": "arrow",
         "startBinding": {"elementId": a, "fixedPoint": list(fa)},
         "endBinding": {"elementId": b, "fixedPoint": list(fb)}}
    if label:
        e["label"] = {"text": label, "fontSize": 16}
    if dashed:
        e["strokeStyle"] = "dashed"
    E.append(e)


def h_arrow(i, a, b, x1, x2, y, ya, yb, label=None, dashed=False):
    """Horizontal arrow at height y, from a's right side to b's left side; ya/yb: y as a fraction of each box."""
    arrow(i, a, b, x1, y, [[0, 0], [x2 - x1, 0]], (1, ya), (0, yb), label, dashed)


def badge(n, x, y, d=40):
    """A callout: a dark circle with the step number, centred on (x, y)."""
    E.append({"type": "ellipse", "id": f"badge{n}-{x}-{y}", "x": x - d / 2, "y": y - d / 2, "width": d, "height": d,
              "backgroundColor": "#1e1e1e", "fillStyle": "solid", "strokeColor": "#1e1e1e",
              "label": {"text": str(n), "fontSize": 20, "strokeColor": "#ffffff"}})


text("title", 20, 10, 'From "Hello" to "Bye": a code change and an infra change, each through its own pipeline', 26)
text("sub", 20, 50, "<name> = your short name (robi)  ·  <gh> = your GitHub user  ·  steps below", 17, "#757575")

# GitHub: service-code
H, Y = 110, 160
zone("zs", 20, 90, 1150, 220, "blue", "GitHub: <gh>/service-code")
box("s1", 40, Y, 250, H, "branch say-bye\napp.py, test_app.py\npyproject.toml", "note")
box("s2", 330, Y, 250, H, "pull request\npr.yml", "blue")
box("s2m", 620, Y + 15, 120, 80, "merge", "grey")
box("s3", 780, Y, 370, H, "main\nmain.yml", "blue")
h_arrow("s1-s2", "s1", "s2", 290, 330, Y + 55, .5, .5)
h_arrow("s2-s2m", "s2", "s2m", 580, 620, Y + 55, .5, .5)
h_arrow("s2m-s3", "s2m", "s3", 740, 780, Y + 55, .5, .5)

# GitHub: infra-code
Y2 = 420
zone("zi", 20, 350, 1150, 220, "purple", "GitHub: <gh>/infra-code")
box("i4", 40, Y2, 250, H, "branch hello-1.1.0\nk8s/deployment.yaml", "note")
box("i5", 330, Y2, 250, H, "pull request\npr.yml", "purple")
box("i5m", 620, Y2 + 15, 120, 80, "merge", "grey")
box("i6", 780, Y2, 370, H, "main\nmain.yml", "purple")
h_arrow("i4-i5", "i4", "i5", 290, 330, Y2 + 55, .5, .5)
h_arrow("i5-i5m", "i5", "i5m", 580, 620, Y2 + 55, .5, .5)
h_arrow("i5m-i6", "i5m", "i6", 740, 780, Y2 + 55, .5, .5)
arrow("s3-i4", "s3", "i4", 965, 270, [[0, 0], [0, 50], [-680, 50], [-680, 150]], (.5, 1), (.98, 0),
      "new tag: 1.1.0", dashed=True)

# Your laptop
zone("zl", 20, 610, 1150, 200, "green", "Your laptop")
box("l0", 40, 670, 540, 110, "bootstrap/  (once, by hand)\nterraform apply", "grey")
box("l7", 620, 670, 530, 110, "terminal\nkubectl get pods -l app=hello -w", "green")

# AWS
AX = 1300
zone("za", AX - 30, 90, 500, 720, "orange", "AWS account (eu-central-1)")
box("role", AX, 140, 440, 80, "IAM role <name>-gha\n(GitHub OIDC, no keys)", "red")
box("ecr", AX, 250, 440, 80, "ECR <name>/hello\n1.0.0, 1.1.0 (immutable)", "teal")
box("s3b", AX, 400, 440, 80, "S3 <name>-infra-code-tfstate-…", "teal")
box("eks", AX, 500, 440, 150, "EKS: your cluster\nDeployment hello (3 Pods)\nService hello", "green")
h_arrow("assume", "s3", "role", 1150, AX, 180, 20 / H, .5, "OIDC", dashed=True)
h_arrow("push", "s3", "ecr", 1150, AX, 255, 95 / H, .0625, "push")
arrow("pull", "ecr", "eks", AX + 440, 290, [[0, 0], [30, 0], [30, 285], [0, 285]], (1, .5), (1, .5), "pull")
h_arrow("state", "i6", "s3b", 1150, AX, 440, 20 / H, .5, "state", dashed=True)
h_arrow("apply", "i6", "eks", 1150, AX, 515, 95 / H, 15 / 150, "apply")
arrow("watch", "l7", "eks", 1150, 725, [[0, 0], [75, 0], [75, -95], [150, -95]], (1, .5), (0, 130 / 150), "watch")

# Callouts on the drawing
badge(-1, 40, 670)
badge(0, 620, 670)
badge(7, 1150, 670)
badge(1, 40, Y)
badge(2, 330, Y)
badge(3, 780, Y)
badge(4, 40, Y2)
badge(5, 330, Y2)
badge(6, 780, Y2)

# Steps, under the drawing
STEPS = [
    (-1, "Once, by hand: terraform apply in bootstrap/ (ECR, S3 bucket, IAM role),\n"
         "docker push :1.0.0, terraform apply in infra-code/, set the repo variables"),
    (0, "Terminal: kubectl get pods -l app=hello -w, leave it open"),
    (1, "service-code, new branch: Hello → Bye in app.py and test_app.py,\n"
        "uv version --bump minor (1.0.0 → 1.1.0)"),
    (2, "Pull request: pr.yml runs unittest and docker build (no push).\nGreen: you merge"),
    (3, "Push to main: main.yml runs unittest, reads the version (uv version --short),\n"
        "assumes the role via OIDC, builds and pushes hello:1.1.0 to ECR"),
    (4, "infra-code, new branch: image tag 1.0.0 → 1.1.0 in k8s/deployment.yaml"),
    (5, "Pull request: pr.yml runs fmt -check, init, validate, plan.\nThe plan shows one change: the image. You merge"),
    (6, "Push to main: main.yml runs the same, then apply, no approval.\nThe state lives in S3"),
    (7, "Terminal: a new Pod with 1.1.0, ready, an old one goes; three times.\ncurl says Bye"),
]
SY = 850
text("stepst", 20, SY, "Steps", 24)
for k, (n, t) in enumerate(STEPS):
    col, row = divmod(k, 5)
    x, y = 40 + col * 870, SY + 50 + row * 70
    badge(n, x + 20, y + 20)
    text(f"step{n}", x + 56, y + 2, t)

Path(__file__).with_name("pipeline.json").write_text(json.dumps(E, indent=1, ensure_ascii=False))
