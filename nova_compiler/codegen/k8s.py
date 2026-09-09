"""
Générateur Kubernetes : un chart Helm minimal (Deployments, Services, HPA,
IngressRoute Traefik, ConfigMap, Secret, PVC) pour le backend et le frontend
générés.

ConfigMap/Secret/PVC reprennent exactement les variables d'environnement et
le volume déjà utilisés par docker-compose (voir codegen/docker.py) — même
liste de variables, mêmes valeurs de développement par défaut (à surcharger
en production via `-f my-values.yaml` ou `--set`) : NOVA_DATABASE_URL/
NOVA_JWT_SECRET/NOVA_SMTP_PASSWORD dans le Secret (une chaîne de connexion
peut porter des identifiants, un JWT secret et un mot de passe SMTP en sont
par nature), NOVA_BACKEND_URL/NOVA_PUBLIC_BACKEND_URL/NOVA_SMTP_HOST/PORT/
USER/FROM dans le ConfigMap (rien de sensible). Le PVC persiste `/app` côté
backend (fichier SQLite par défaut, comme le volume `backend_data` de
docker-compose) — NB : avec plusieurs réplicas (HPA activé par défaut, voir
`_values_yaml`) et un PVC `ReadWriteOnce`, seul UN pod peut le monter à la
fois ; passer à une vraie base réseau (Postgres/MySQL, tâche #28) avant de
scaler le backend au-delà d'un réplica en production, et désactiver le PVC
(`persistence.enabled: false`) dans ce cas.

Aligné sur la feuille de route NOVA Phase 2 (K8s, Helm, Traefik, HPA).
"""

from __future__ import annotations

from .. import keywords as kw
from ..ast_nodes import Email, NovaProgram
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


def _values_yaml(
    name: str,
    has_auth: bool,
    has_uploads: bool,
    has_email: bool,
    email,
    db_engine: str = "sqlite",
) -> str:
    # `config`/`secrets` reprennent exactement les variables conditionnelles
    # de docker-compose (voir codegen/docker.py::_compose) : mêmes clés,
    # mêmes valeurs de développement par défaut — la seule différence est le
    # découpage ConfigMap (non sensible) / Secret (sensible), qui n'existe
    # pas en docker-compose (un seul bloc `environment:`).
    jwt_secret_line = (
        "\n  # Bloc `auth { ... }` détecté : à surcharger avec une vraie valeur"
        "\n  # secrète en production (`openssl rand -hex 32`, par exemple)."
        '\n  jwtSecret: "nova-dev-secret-change-me"'
        if has_auth
        else ""
    )
    smtp_password_line = (
        "\n  # Bloc `email { ... }` détecté : le mot de passe SMTP n'est JAMAIS"
        "\n  # écrit dans le fichier .nova (voir backend/app/emailer.py) — à"
        "\n  # surcharger ici en production."
        '\n  smtpPassword: ""'
        if has_email
        else ""
    )
    smtp_config_lines = (
        f"\n  # Bloc `email {{ ... }}` détecté : configuration SMTP non sensible"
        f"\n  # (le mot de passe, lui, est dans `secrets.smtpPassword` ci-dessus)."
        f'\n  smtpHost: "{email.host}"'
        f"\n  smtpPort: {email.port}"
        f'\n  smtpUser: "{email.user}"'
        f'\n  smtpFrom: "{email.from_addr}"'
        f'\n  smtpTo: "{email.to_addr}"'
        if has_email
        else ""
    )
    public_backend_url_line = (
        "\n  # Champ `file`/`image` détecté : URL du backend joignable DEPUIS LE"
        "\n  # NAVIGATEUR (aperçus/téléchargements) — à surcharger avec le vrai"
        f"\n  # domaine public en production (ex. https://{name}.example.com)."
        f'\n  publicBackendUrl: "http://{name}.example.com"'
        if has_uploads
        else ""
    )
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

# ConfigMap {name}-config : variables d'environnement non sensibles.
config:
  backendUrl: "http://{name}-backend:8000"{public_backend_url_line}{smtp_config_lines}

# Secret {name}-secret : variables sensibles (jamais en clair dans le
# fichier .nova source, voir docstring de ce module).
secrets:
  databaseUrl: "{kw.DB_DEFAULT_URLS.get(db_engine, kw.DB_DEFAULT_URLS["sqlite"])}"{jwt_secret_line}{smtp_password_line}

# PVC {name}-backend-data : persiste le fichier SQLite du backend (défaut,
# voir docstring de ce module) — désactivez une fois passé à une vraie base
# réseau (Postgres/MySQL) pour pouvoir scaler le backend à plusieurs
# réplicas.
persistence:
  enabled: true
  size: 1Gi
  storageClassName: ""
  accessMode: ReadWriteOnce
"""


def _deployment(name: str, component: str, mount_pvc: bool = False) -> str:
    # `envFrom` (ConfigMap + Secret) : les deux composants reçoivent les
    # mêmes variables — quelques-unes ne concernent que le backend (ex.
    # NOVA_DATABASE_URL), mais une variable d'environnement inutilisée ne
    # gêne pas, et ça évite de dupliquer la liste par composant ici.
    env_from = f"""\
          envFrom:
            - configMapRef:
                name: {name}-config
            - secretRef:
                name: {name}-secret
"""
    # Volume PVC : uniquement le backend (persistance du fichier SQLite,
    # voir docstring du module) — `volumeMounts` ET `volumes` conditionnés
    # ENSEMBLE à `persistence.enabled` (même garde que le PVC lui-même, voir
    # `_pvc`) : l'un sans l'autre pointerait vers un volume inexistant ou
    # laisserait un volume déclaré mais jamais monté.
    volume_mount = (
        f"""\
      {{{{- if .Values.persistence.enabled }}}}
          volumeMounts:
            - name: data
              mountPath: /app
      {{{{- end }}}}
"""
        if mount_pvc
        else ""
    )
    volumes = (
        f"""\
      {{{{- if .Values.persistence.enabled }}}}
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: {name}-backend-data
      {{{{- end }}}}
"""
        if mount_pvc
        else ""
    )
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
{env_from}{volume_mount}{volumes}"""


def _configmap(name: str, has_uploads: bool, has_email: bool) -> str:
    # Reprend `config:` de `_values_yaml` — rien de sensible ici (voir
    # docstring du module).
    public_backend_url_line = (
        '\n  NOVA_PUBLIC_BACKEND_URL: "{{ .Values.config.publicBackendUrl }}"'
        if has_uploads
        else ""
    )
    smtp_lines = (
        '\n  NOVA_SMTP_HOST: "{{ .Values.config.smtpHost }}"'
        '\n  NOVA_SMTP_PORT: "{{ .Values.config.smtpPort }}"'
        '\n  NOVA_SMTP_USER: "{{ .Values.config.smtpUser }}"'
        '\n  NOVA_SMTP_FROM: "{{ .Values.config.smtpFrom }}"'
        '\n  NOVA_SMTP_TO: "{{ .Values.config.smtpTo }}"'
        if has_email
        else ""
    )
    return f"""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}-config
data:
  NOVA_BACKEND_URL: "{{{{ .Values.config.backendUrl }}}}"{public_backend_url_line}{smtp_lines}
"""


def _secret(name: str, has_auth: bool, has_email: bool) -> str:
    # `stringData` (texte en clair dans le manifeste, encodé automatiquement
    # par Kubernetes) reprend `secrets:` de `_values_yaml` — voir docstring
    # du module pour la justification du découpage ConfigMap/Secret.
    jwt_secret_line = (
        '\n  NOVA_JWT_SECRET: "{{ .Values.secrets.jwtSecret }}"' if has_auth else ""
    )
    smtp_password_line = (
        '\n  NOVA_SMTP_PASSWORD: "{{ .Values.secrets.smtpPassword }}"'
        if has_email
        else ""
    )
    return f"""\
apiVersion: v1
kind: Secret
metadata:
  name: {name}-secret
type: Opaque
stringData:
  NOVA_DATABASE_URL: "{{{{ .Values.secrets.databaseUrl }}}}"{jwt_secret_line}{smtp_password_line}
"""


def _pvc(name: str) -> str:
    # Persiste `/app` côté backend (fichier SQLite par défaut) — voir la
    # docstring du module pour la mise en garde ReadWriteOnce/multi-réplica.
    return f"""\
{{{{- if .Values.persistence.enabled }}}}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {name}-backend-data
spec:
  accessModes:
    - {{{{ .Values.persistence.accessMode }}}}
  {{{{- if .Values.persistence.storageClassName }}}}
  storageClassName: {{{{ .Values.persistence.storageClassName }}}}
  {{{{- end }}}}
  resources:
    requests:
      storage: {{{{ .Values.persistence.size }}}}
{{{{- end }}}}
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
    has_auth = program.auth is not None and program.auth.enabled
    has_uploads = any(f.type in ("file", "image") for e in program.entities for f in e.fields)
    has_email = program.email is not None
    email = program.email or Email()
    db_engine = program.database_engine()
    files = {
        f"{base}/Chart.yaml": _chart_yaml(name),
        f"{base}/values.yaml": _values_yaml(name, has_auth, has_uploads, has_email, email, db_engine),
        f"{base}/templates/configmap.yaml": _configmap(name, has_uploads, has_email),
        f"{base}/templates/secret.yaml": _secret(name, has_auth, has_email),
        f"{base}/templates/pvc.yaml": _pvc(name),
        f"{base}/templates/backend-deployment.yaml": _deployment(name, "backend", mount_pvc=True),
        f"{base}/templates/backend-service.yaml": _service(name, "backend"),
        f"{base}/templates/backend-hpa.yaml": _hpa(name, "backend"),
        f"{base}/templates/frontend-deployment.yaml": _deployment(name, "frontend"),
        f"{base}/templates/frontend-service.yaml": _service(name, "frontend"),
        f"{base}/templates/frontend-hpa.yaml": _hpa(name, "frontend"),
        f"{base}/templates/ingressroute.yaml": _ingressroute(name),
    }
    return files
