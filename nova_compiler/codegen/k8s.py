"""
Générateur Kubernetes : un chart Helm minimal (Deployments, Services, HPA,
IngressRoute Traefik) pour le backend et le frontend générés.

Aligné sur la feuille de route NOVA Phase 2 (K8s, Helm, Traefik, HPA).
"""

from __future__ import annotations

from ..ast_nodes import NovaProgram
from .utils import to_ascii_identifier, to_snake_case


def _release_name(program: NovaProgram) -> str:
    if program.app:
        return to_snake_case(to_ascii_identifier(program.app.name)).replace("_", "-") or "nova-app"
    return "nova-app"


def _chart_yaml(name: str) -> str:
    return f"""\
apiVersion: v2
name: {name}
description: Chart Helm généré par NOVA pour {name} (backend FastAPI + frontend Reflex)
type: application
version: 0.1.0
appVersion: "0.1.0"
"""


def _values_yaml(name: str) -> str:
    return f"""\
# Valeurs par défaut du chart Helm généré par NOVA.
# Surchargez avec `helm install {name} ./helm/{name} -f my-values.yaml`.

backend:
  image:
    repository: {name}-backend
    tag: latest
    pullPolicy: IfNotPresent
  replicaCount: 2
  service:
    port: 8000
  resources:
    requests: {{ cpu: 100m, memory: 128Mi }}
    limits: {{ cpu: 500m, memory: 512Mi }}
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 6
    targetCPUUtilizationPercentage: 70

frontend:
  image:
    repository: {name}-frontend
    tag: latest
    pullPolicy: IfNotPresent
  replicaCount: 2
  service:
    port: 3000
  resources:
    requests: {{ cpu: 100m, memory: 128Mi }}
    limits: {{ cpu: 500m, memory: 512Mi }}
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 6
    targetCPUUtilizationPercentage: 70

ingress:
  enabled: true
  className: traefik
  host: {name}.example.com
"""


def _deployment(name: str, component: str) -> str:
    return f"""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}-{component}
  labels:
    app: {name}
    component: {component}
spec:
  replicas: {{{{ .Values.{component}.replicaCount }}}}
  selector:
    matchLabels:
      app: {name}
      component: {component}
  template:
    metadata:
      labels:
        app: {name}
        component: {component}
    spec:
      containers:
        - name: {component}
          image: "{{{{ .Values.{component}.image.repository }}}}:{{{{ .Values.{component}.image.tag }}}}"
          imagePullPolicy: {{{{ .Values.{component}.image.pullPolicy }}}}
          ports:
            - containerPort: {{{{ .Values.{component}.service.port }}}}
          resources:
            {{{{- toYaml .Values.{component}.resources | nindent 12 }}}}
"""


def _service(name: str, component: str) -> str:
    return f"""\
apiVersion: v1
kind: Service
metadata:
  name: {name}-{component}
  labels:
    app: {name}
    component: {component}
spec:
  selector:
    app: {name}
    component: {component}
  ports:
    - port: {{{{ .Values.{component}.service.port }}}}
      targetPort: {{{{ .Values.{component}.service.port }}}}
"""


def _hpa(name: str, component: str) -> str:
    return f"""\
{{{{- if .Values.{component}.autoscaling.enabled }}}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}-{component}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}-{component}
  minReplicas: {{{{ .Values.{component}.autoscaling.minReplicas }}}}
  maxReplicas: {{{{ .Values.{component}.autoscaling.maxReplicas }}}}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{{{ .Values.{component}.autoscaling.targetCPUUtilizationPercentage }}}}
{{{{- end }}}}
"""


def _ingressroute(name: str) -> str:
    # IngressRoute Traefik (CRD) plutôt qu'un Ingress générique, conformément
    # au choix de reverse-proxy retenu dans la feuille de route NOVA.
    return f"""\
{{{{- if .Values.ingress.enabled }}}}
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: {name}
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`{{{{ .Values.ingress.host }}}}`) && PathPrefix(`/api`)
      kind: Rule
      services:
        - name: {name}-backend
          port: {{{{ .Values.backend.service.port }}}}
    - match: Host(`{{{{ .Values.ingress.host }}}}`)
      kind: Rule
      services:
        - name: {name}-frontend
          port: {{{{ .Values.frontend.service.port }}}}
{{{{- end }}}}
"""


def generate_k8s(program: NovaProgram) -> dict[str, str]:
    name = _release_name(program)
    base = f"helm/{name}"
    files = {
        f"{base}/Chart.yaml": _chart_yaml(name),
        f"{base}/values.yaml": _values_yaml(name),
        f"{base}/templates/backend-deployment.yaml": _deployment(name, "backend"),
        f"{base}/templates/backend-service.yaml": _service(name, "backend"),
        f"{base}/templates/backend-hpa.yaml": _hpa(name, "backend"),
        f"{base}/templates/frontend-deployment.yaml": _deployment(name, "frontend"),
        f"{base}/templates/frontend-service.yaml": _service(name, "frontend"),
        f"{base}/templates/frontend-hpa.yaml": _hpa(name, "frontend"),
        f"{base}/templates/ingressroute.yaml": _ingressroute(name),
    }
    return files
