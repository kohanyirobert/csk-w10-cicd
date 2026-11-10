"""Writes sequence.json, the Excalidraw skeleton of ../sequence.svg.

python3 src/sequence.py && ~/.agents/skills/diagrams/scripts/export -o . src/sequence.json
"""

import json
from pathlib import Path

PAL = {
    "blue": ("#a5d8ff", "#4a9eed"), "purple": ("#d0bfff", "#8b5cf6"), "orange": ("#ffd8a8", "#f59e0b"),
    "teal": ("#c3fae8", "#06b6d4"), "green": ("#b2f2bb", "#22c55e"), "red": ("#ffc9c9", "#ef4444"),
    "note": ("#fff3bf", "#f59e0b"), "grey": ("#e9ecef", "#868e96"),
}
COLS = [
    ("you", "You\n(laptop)", "grey"),
    ("svc", "GitHub\nservice-code", "blue"),
    ("rs", "runner\nservice-code", "blue"),
    ("iam", "AWS IAM\n(OIDC, STS)", "red"),
    ("ecr", "ECR\n<name>/hello", "teal"),
    ("inf", "GitHub\ninfra-code", "purple"),
    ("ri", "runner\ninfra-code", "purple"),
    ("s3", "S3\nstate", "teal"),
    ("eks", "EKS\nyour cluster", "green"),
]
STEP, X0, TOP = 200, 120, 90
X = {k: X0 + i * STEP for i, (k, _, _) in enumerate(COLS)}
WIDTH = X0 * 2 + STEP * (len(COLS) - 1)

# (kind, ...) rows, top to bottom. "phase" starts a band.
ROWS = [
    ("phase", "1  service-code: pull request", "blue"),
    ("msg", "you", "svc", "push, open PR"),
    ("msg", "svc", "rs", "pr.yml"),
    ("note", "rs", "unittest, docker build"),
    ("msg", "rs", "svc", "check ✓", True),
    ("msg", "you", "svc", "merge"),
    ("phase", "2  service-code: push to main", "blue"),
    ("msg", "svc", "rs", "main.yml"),
    ("note", "rs", "unittest, version 1.1.0,\ndocker build"),
    ("msg", "rs", "iam", "assume role (OIDC)"),
    ("msg", "iam", "rs", "1 h credentials", True),
    ("msg", "rs", "ecr", "push :1.1.0"),
    ("phase", "3  infra-code: pull request", "purple"),
    ("msg", "you", "inf", "branch: tag 1.0.0 → 1.1.0, open PR"),
    ("msg", "inf", "ri", "pr.yml"),
    ("msg", "ri", "iam", "assume role (OIDC)"),
    ("msg", "iam", "ri", "credentials", True),
    ("msg", "ri", "s3", "read state"),
    ("msg", "ri", "eks", "read objects"),
    ("note", "ri", "fmt, validate, plan:\n1 to change"),
    ("msg", "ri", "inf", "check ✓", True),
    ("msg", "you", "inf", "merge"),
    ("phase", "4  infra-code: push to main", "purple"),
    ("msg", "inf", "ri", "main.yml"),
    ("msg", "ri", "iam", "assume role (OIDC)"),
    ("msg", "iam", "ri", "credentials", True),
    ("msg", "ri", "s3", "lock, read state"),
    ("msg", "ri", "eks", "apply: image :1.1.0"),
    ("msg", "ri", "s3", "write state, unlock"),
    ("phase", "5  rollout", "green"),
    ("msg", "eks", "ecr", "nodes pull :1.1.0"),
    ("note", "eks", "new Pod ready,\nold Pod goes; × 3"),
    ("msg", "eks", "you", "kubectl get pods -w", True),
]

E = []


def rect(i, x, y, w, h, color, text=None, fs=17, opacity=None, stroke_width=None):
    f, s = PAL[color]
    e = {"type": "rectangle", "id": i, "x": x, "y": y, "width": w, "height": h, "roundness": {"type": 3},
         "backgroundColor": f, "fillStyle": "solid", "strokeColor": s}
    if text:
        e["label"] = {"text": text, "fontSize": fs}
    if opacity:
        e["opacity"] = opacity
    if stroke_width:
        e["strokeWidth"] = stroke_width
    E.append(e)


# Layout pass: y of every row, phase bands.
y = TOP + 90
placed, bands = [], []
for row in ROWS:
    if row[0] == "phase":
        if bands:
            bands[-1][3] = y - 6
        y += 12
        bands.append([row[1], row[2], y, None])
        y += 34
        continue
    h = 64 if row[0] == "note" else 46
    placed.append((row, y, h))
    y += h
bands[-1][3] = y + 6
BOTTOM = y + 30

E.append({"type": "text", "id": "title", "x": 20, "y": 10, "fontSize": 26,
          "text": "One change, two pipelines: who talks to whom, in what order"})
E.append({"type": "text", "id": "sub", "x": 20, "y": 48, "fontSize": 17, "strokeColor": "#757575",
          "text": "solid: request or action  ·  dashed: response  ·  yellow: work on the runner or in the cluster"})

for k, (title, color, y1, y2) in enumerate(bands):
    rect(f"band{k}", 20, y1, WIDTH - 40, y2 - y1, color, opacity=25, stroke_width=1)
    E.append({"type": "text", "id": f"band{k}t", "x": 32, "y": y1 + 6, "text": title, "fontSize": 18})

for k, label, color in COLS:
    rect(f"h-{k}", X[k] - 85, TOP, 170, 64, color, label)
    E.append({"type": "line", "id": f"life-{k}", "x": X[k], "y": TOP + 64, "width": 0,
              "height": BOTTOM - TOP - 64, "points": [[0, 0], [0, BOTTOM - TOP - 64]],
              "strokeColor": "#868e96", "strokeStyle": "dashed", "strokeWidth": 1})

for n, (row, y, h) in enumerate(placed):
    if row[0] == "note":
        _, who, text = row
        rect(f"note{n}", min(X[who] - 95, WIDTH - 40 - 200), y + 4, 190, h - 8, "note", text, fs=16)
        continue
    _, a, b, text, *rest = row
    dashed = bool(rest and rest[0])
    dx = X[b] - X[a]
    e = {"type": "arrow", "id": f"msg{n}", "x": X[a], "y": y + h / 2, "width": abs(dx), "height": 0,
         "points": [[0, 0], [dx, 0]], "endArrowhead": "arrow", "label": {"text": text, "fontSize": 16}}
    if dashed:
        e["strokeStyle"] = "dashed"
    E.append(e)

Path(__file__).with_name("sequence.json").write_text(json.dumps(E, indent=1, ensure_ascii=False))
