"""
Générateur de backend NoSQL : AST NOVA -> application FastAPI + Beanie/Motor
(MongoDB), tâche #29 — sélectionné via `application { database: mongodb }`
(voir parser._validate_app_database / keywords.DATABASE_ENGINES).

Chemin de code DISTINCT du backend SQL (`api_fastapi.py`), pas une simple
variante : les entités deviennent des `Document` Beanie (au lieu de tables
SQLModel) et les routeurs CRUD sont asynchrones (`await item.insert()` etc.
au lieu de `Session.add()/commit()`). Tout ce qui ne dépend PAS du moteur de
stockage est réutilisé tel quel depuis `api_fastapi.py` (import direct,
plutôt que dupliqué) : `_HEADER`, `_has_uploads`/`_UPLOADS_ROUTER_TEMPLATE`
(upload sur disque, jamais en base), `_generate_emailer` (SMTP direct),
`_validation_check_lines` (comparaisons `item.<champ>` pures, aucune
requête SQL), `_model_class_name`/`_table_name` (nommage), et les helpers
`_multilingual_*` (leur sortie `Field(default=None)` est de la syntaxe
Pydantic standard, valide aussi bien sous SQLModel que sous Beanie/Pydantic
pur).

Limites assumées de ce MVP NoSQL (voir parser._validate_mongo_unsupported_
features, qui les rejette à la compilation plutôt que de générer un projet
cassé) : pas de bloc `requete`/`query` (filtres/tris/jointures construits
directement en SQLAlchemy côté SQL), pas de bloc `calendar`/`calendrier`
(idem), pas de relation `has_many` matérialisée (résumé texte construit via
une requête SQL dans `api_fastapi.py::_has_many_relation_info` — seul
`belongs_to`, stocké comme un simple champ `<cible>_id: str`, est supporté
ici). `chart` reste supporté quand il porte sur une entité (réutilise
l'endpoint liste CRUD, agnostique du moteur) ; `validation` (règles
croisant plusieurs champs), `email`/`notifier:`, `auth`, les champs
`fichier`/`image`/`multilingue` et `application { langues: ... }`
fonctionnent à l'identique du backend SQL.
"""

from __future__ import annotations

from ..ast_nodes import Entity, NovaProgram
from .api_fastapi import (
    _HEADER,
    _calendar_ics_slug,
    _format_query_value,
    _generate_emailer,
    _has_many_relation_info,
    _has_uploads,
    _ICS_ESCAPE_HELPER,
    _model_class_name,
    _multilingual_column_names,
    _multilingual_model_lines,
    _multilingual_schema_lines,
    _relation_display_field,
    _table_name,
    _UPLOADS_ROUTER_TEMPLATE,
    _validation_check_lines,
)
from .utils import PY_TYPE_MAP, to_pascal_case, to_snake_case


def _mongo_field_line(f) -> str:
    """Ligne de champ `Document` Beanie pour un champ simple (non
    multilingue, non référence) — `unique` devient le type `Indexed(...,
    unique=True)` (mécanisme Beanie : un `Field(unique=True)` ordinaire,
    qui fonctionne côté SQLModel, n'existe pas en Pydantic pur)."""
    py_type = PY_TYPE_MAP.get(f.type, "str")
    base_type = f"Indexed({py_type}, unique=True)" if f.unique else py_type
    type_hint = base_type if f.required else f"Optional[{base_type}]"
    opts = []
    if f.pattern:
        opts.append(f'pattern=r"{f.pattern}"')
    if f.default is not None:
        opts.append(f"default={f.default!r}")
    elif not f.required:
        opts.append("default=None")
    opts_str = ", ".join(opts)
    suffix = f" = Field({opts_str})" if opts_str else ""
    return f"    {to_snake_case(f.name)}: {type_hint}{suffix}"


def _mongo_schema_field(f) -> str:
    """Même champ pour les schémas Create/Update (Pydantic `BaseModel`
    simple, sans `Indexed`/index — ceux-ci n'existent que sur le
    `Document` lui-même)."""
    py_type = PY_TYPE_MAP.get(f.type, "str") if not f.is_reference else "str"
    type_hint = py_type if f.required else f"Optional[{py_type}]"
    if f.pattern:
        kwargs = f'pattern=r"{f.pattern}"' if f.required else f'default=None, pattern=r"{f.pattern}"'
        return f"    {to_snake_case(f.name)}: {type_hint} = Field({kwargs})"
    default = "" if f.required else " = None"
    return f"    {to_snake_case(f.name)}: {type_hint}{default}"


def _generate_mongo_models(program: NovaProgram) -> str:
    active_langs = program.active_languages()
    lines = [
        _HEADER,
        "from __future__ import annotations",
        "",
        "from datetime import date, datetime",
        "from typing import Optional",
        "",
        "from beanie import Document, Indexed",
        "from pydantic import BaseModel, Field",
        "",
        "",
    ]
    for entity in program.entities:
        cls = _model_class_name(entity)
        table = _table_name(entity)
        fk_field_names = [to_snake_case(rel.target) + "_id" for rel in entity.relations if rel.kind == "belongs_to"]

        lines.append(f"class {cls}(Document):")
        lines.append(f'    """Généré depuis `entity {entity.name}` / `entité {entity.name}` '
                      f'(backend NoSQL, Beanie/MongoDB — tâche #29)."""')
        for f in entity.fields:
            if f.multilingual:
                lines += _multilingual_model_lines(f, active_langs)
            else:
                lines.append(_mongo_field_line(f))
        for fk_name in fk_field_names:
            lines.append(f"    {fk_name}: Optional[str] = Field(default=None)")
        lines.append("")
        lines.append("    class Settings:")
        lines.append(f'        name = "{table}"')
        lines.append("")
        lines.append("")

        lines.append(f"class {cls}Create(BaseModel):")
        body = list(entity.fields)
        if not body and not fk_field_names:
            lines.append("    pass")
        for f in body:
            if f.multilingual:
                lines += _multilingual_schema_lines(f, active_langs)
            else:
                lines.append(_mongo_schema_field(f))
        for fk_name in fk_field_names:
            lines.append(f"    {fk_name}: Optional[str] = None")
        lines.append("")
        lines.append("")

        lines.append(f"class {cls}Update(BaseModel):")
        if not body and not fk_field_names:
            lines.append("    pass")
        for f in body:
            if f.multilingual:
                lines += _multilingual_schema_lines(f, active_langs)
                continue
            py_type = PY_TYPE_MAP.get(f.type, "str") if not f.is_reference else "str"
            lines.append(f"    {to_snake_case(f.name)}: Optional[{py_type}] = None")
        for fk_name in fk_field_names:
            lines.append(f"    {fk_name}: Optional[str] = None")
        lines.append("")
        lines.append("")

        # Schéma de lecture supplémentaire pour les entités portant au moins
        # un `has_many` (tâche #34) : même rôle que `{cls}Read(SQLModel)`
        # côté backend SQL (voir api_fastapi.py) — `id` est ici `Optional[
        # str]` (pas `int`) puisque `_generate_mongo_router` convertit
        # explicitement l'ObjectId Beanie en chaîne avant de construire ce
        # dict (voir son commentaire sur `data["id"] = str(item.id)`).
        has_many_info = _has_many_relation_info(entity, program)
        if has_many_info:
            lines.append(f"class {cls}Read(BaseModel):")
            lines.append("    id: Optional[str] = None")
            for f in entity.fields:
                if f.multilingual:
                    lines += [f"    {col}: Optional[str] = None" for col in _multilingual_column_names(f, active_langs)]
                    continue
                py_type = PY_TYPE_MAP.get(f.type, "str") if not f.is_reference else "str"
                lines.append(f"    {to_snake_case(f.name)}: Optional[{py_type}] = None")
            for fk_name in fk_field_names:
                lines.append(f"    {fk_name}: Optional[str] = None")
            for _child_cls, _child_table, _fk_col, text_field, _display_attr in has_many_info:
                lines.append(f'    {text_field}: str = ""')
            lines.append("")
            lines.append("")

    return "\n".join(lines) + "\n"


def _generate_mongo_database(program: NovaProgram) -> str:
    document_classes = [_model_class_name(e) for e in program.entities]
    has_auth = program.auth is not None and program.auth.enabled

    import_lines = []
    if document_classes:
        import_lines.append(f"from .models import {', '.join(document_classes)}")
    if has_auth:
        import_lines.append("from .auth import User")
    import_line = "\n".join(import_lines)

    document_models = list(document_classes) + (["User"] if has_auth else [])
    document_models_literal = "[" + ", ".join(document_models) + "]"
    return _HEADER + f'''
from __future__ import annotations

import os

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

{import_line}

# URL de connexion Mongo — surchargeable sans recompiler (même variable que
# le backend SQL, voir codegen/docker.py::_compose et parser._validate_app_
# database) : NOVA_DATABASE_URL, jamais un identifiant en dur ici.
DATABASE_URL = os.environ.get(
    "NOVA_DATABASE_URL", "mongodb://nova:nova@db:27017/nova?authSource=admin"
)

# Nom de la base Mongo, à part de l'URL (plutôt que de dépendre du chemin
# "/nova" dans NOVA_DATABASE_URL, absent d'une chaîne de connexion sans nom
# de base explicite — ex. un cluster Atlas partagé) : surchargeable seul via
# NOVA_MONGO_DB sans toucher au reste de l'URL de connexion.
MONGO_DB_NAME = os.environ.get("NOVA_MONGO_DB", "nova")

_client = AsyncIOMotorClient(DATABASE_URL)
_database = _client[MONGO_DB_NAME]

DOCUMENT_MODELS = {document_models_literal}


async def init_db() -> None:
    """Enregistre les modèles Beanie auprès de la base au démarrage
    (équivalent Mongo de `SQLModel.metadata.create_all`, voir database.py
    du backend SQL) — asynchrone, contrairement à son équivalent SQL."""
    await init_beanie(database=_database, document_models=DOCUMENT_MODELS)
'''


def _generate_mongo_auth(program: NovaProgram) -> str:
    auth = program.auth
    roles = auth.roles if auth and auth.roles else ["user"]
    default_role = auth.default_role if auth else "user"
    roles_literal = "[" + ", ".join(repr(r) for r in roles) + "]"
    return _HEADER + f'''
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from beanie import Document, Indexed
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# Bloc `auth {{ ... }}` du fichier .nova : rôles déclarés et rôle par défaut
# attribué à l'inscription si aucun n'est précisé.
ROLES = {roles_literal}
DEFAULT_ROLE = "{default_role}"

# Clé de signature JWT : à définir en production via la variable
# d'environnement NOVA_JWT_SECRET — même mécanisme que le backend SQL.
SECRET_KEY = os.environ.get("NOVA_JWT_SECRET", "nova-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class User(Document):
    """Collection utilisateur générée par le bloc `auth {{ ... }}` —
    indépendante des entités du DSL (équivalent Mongo de la table
    `nova_users` du backend SQL)."""

    email: Indexed(str, unique=True)
    password_hash: str
    role: str = Field(default=DEFAULT_ROLE)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "nova_users"


class UserCreate(BaseModel):
    # Pas de champ `role` ici, volontairement : voir `register()` ci-dessous
    # (même choix que le backend SQL).
    email: str
    password: str


class RoleUpdate(BaseModel):
    role: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({{"exp": expire}})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou absents / Missing or invalid credentials",
        headers={{"WWW-Authenticate": "Bearer"}},
    )
    if token is None:
        raise credentials_error
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_error
    except JWTError:
        raise credentials_error
    user = await User.find_one(User.email == email)
    if user is None:
        raise credentials_error
    return user


def require_role(role: str):
    """Dépendance FastAPI protégeant une route/un routeur pour un rôle donné
    — un utilisateur "admin" passe toujours, quel que soit le rôle requis
    (même comportement que le backend SQL)."""

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != role and user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé / Forbidden")
        return user

    return _dependency


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=User, response_model_exclude={{"password_hash"}}, response_model_by_alias=False)
async def register(payload: UserCreate):
    """Le rôle attribué n'est JAMAIS choisi par l'appelant : le tout premier
    compte créé sur le projet devient automatiquement "admin" (même
    bootstrap que le backend SQL, voir sa docstring équivalente)."""
    existing = await User.find_one(User.email == payload.email)
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email déjà utilisé / Email already registered")
    is_first_user = (await User.find_one()) is None
    role = "admin" if (is_first_user and "admin" in ROLES) else DEFAULT_ROLE
    user = User(email=payload.email, password_hash=hash_password(payload.password), role=role)
    await user.insert()
    return user


@router.patch("/users/{{user_id}}/role", response_model=User, response_model_exclude={{"password_hash"}}, response_model_by_alias=False)
async def set_user_role(user_id: str, payload: RoleUpdate, admin: User = Depends(require_role("admin"))):
    """Promeut/rétrograde un compte existant — réservé aux admins (même
    comportement que le backend SQL)."""
    if payload.role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Rôle inconnu / Unknown role: {{payload.role}}")
    try:
        user = await User.get(user_id)
    except Exception:
        user = None
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable / User not found")
    user.role = payload.role
    await user.save()
    return user


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Compatible OAuth2PasswordRequestForm : envoyer `username` (= email) et
    `password` en `application/x-www-form-urlencoded`."""
    user = await User.find_one(User.email == form_data.username)
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides / Invalid credentials")
    token = create_access_token({{"sub": user.email, "role": user.role}})
    return {{"access_token": token, "token_type": "bearer"}}


@router.get("/me", response_model=User, response_model_exclude={{"password_hash"}}, response_model_by_alias=False)
async def me(user: User = Depends(get_current_user)):
    return user
'''


def _generate_mongo_router(
    entity: Entity,
    actions: list[str],
    protected_role: str | None = None,
    notify_actions: list[str] | None = None,
    notify_recipient_field: str | None = None,
    notify_attachment_field: str | None = None,
    program: NovaProgram | None = None,
) -> str:
    cls = _model_class_name(entity)
    table = _table_name(entity)
    var = to_snake_case(entity.name)
    tag = entity.name
    notify_actions = notify_actions or []
    recipient_snake = to_snake_case(notify_recipient_field) if notify_recipient_field else None
    attachment_snake = to_snake_case(notify_attachment_field) if notify_attachment_field else None

    def _notify_kwargs(recipient_expr: str | None, attachment_expr: str | None) -> str:
        extra = ""
        if recipient_expr:
            extra += f", to=({recipient_expr} or None)"
        if attachment_expr:
            extra += (
                f", attachment_path=(UPLOADS_DIR / Path({attachment_expr}).name "
                f"if {attachment_expr} else None)"
            )
        return extra

    has_unique_field = any(f.unique for f in entity.fields)
    has_many_info = _mongo_has_many_relation_info(entity, program) if program is not None else []
    lines = [
        _HEADER,
        "from __future__ import annotations",
        "",
        "from fastapi import APIRouter, Depends, HTTPException",
    ]
    if has_unique_field:
        # `champ ... unique` -> index Beanie (voir _mongo_field_line) : une
        # violation lève `DuplicateKeyError` côté MongoDB, jamais attrapée
        # par défaut (le driver la laisse remonter) — convertie ici en 422,
        # même sémantique que la contrainte `unique=True` du backend SQL
        # (violation de contrainte -> erreur 4xx, pas un 500 générique).
        lines.append("from pymongo.errors import DuplicateKeyError")
    lines += [
        "",
        f"from ..models import {cls}, {cls}Create, {cls}Update",
    ]
    if protected_role:
        lines.append("from ..auth import require_role")
    if notify_actions:
        lines.append("from ..emailer import send_email")
    if attachment_snake:
        lines.append("from pathlib import Path")
        lines.append("from ._uploads import UPLOADS_DIR")
    lines.append("")
    router_kwargs = f'prefix="/{table}", tags=["{tag}"]'
    if protected_role:
        router_kwargs += f', dependencies=[Depends(require_role("{protected_role}"))]'
    lines += [
        f"router = APIRouter({router_kwargs})",
        "",
        "",
    ]

    def _related_text_lines(indent: str, item_expr: str) -> list[str]:
        # Équivalent Mongo de `api_fastapi._generate_router._related_text_
        # lines` : une requête Motor par relation `has_many`, filtrée sur
        # la clé étrangère (stockée comme `Optional[str]` côté enfant, voir
        # `_generate_mongo_models`) — `str(...)` convertit explicitement
        # l'ObjectId Beanie de `item_expr.id` en la même représentation
        # texte que celle écrite dans ce champ à la création (voir
        # `create_<var>` : le payload `<parent>_id` arrive déjà en chaîne
        # depuis le client, JSON ne connaissant pas ObjectId).
        out = []
        for child_cls, child_table, fk_col, text_field, display_attr in has_many_info:
            related_var = f"related_{child_table}"
            out.append(
                f"{indent}{related_var} = await models.{child_cls}.find("
                f"models.{child_cls}.{fk_col} == str({item_expr}.id)).to_list()"
            )
            out.append(
                f'{indent}data["{text_field}"] = ", ".join(str(getattr(c, "{display_attr}")) for c in {related_var})'
            )
        return out

    if has_many_info:
        lines[lines.index(f"from ..models import {cls}, {cls}Create, {cls}Update")] = (
            f"from ..models import {cls}, {cls}Create, {cls}Read, {cls}Update"
        )
        lines.insert(lines.index(f"from ..models import {cls}, {cls}Create, {cls}Read, {cls}Update") + 1, "from .. import models")

    if "list" in actions:
        if has_many_info:
            lines += [
                f'@router.get("/", response_model=list[{cls}Read], response_model_by_alias=False)',
                f"async def list_{table}():",
                f'    """list / liste — retourne tous les {tag}, avec un résumé texte '
                f'des enregistrements liés ({", ".join(t for _c, _t, _f, t, _d in has_many_info)})."""',
                f"    items = await {cls}.find_all().to_list()",
                "    result = []",
                "    for item in items:",
                "        data = item.model_dump()",
                "        data[\"id\"] = str(item.id)",
            ]
            lines += _related_text_lines("        ", "item")
            lines += [
                "        result.append(data)",
                "    return result",
                "",
                "",
            ]
        else:
            lines += [
                f'@router.get("/", response_model=list[{cls}], response_model_by_alias=False)',
                f"async def list_{table}():",
                f'    """list / liste — retourne tous les {tag}."""',
                f"    return await {cls}.find_all().to_list()",
                "",
                "",
            ]

    if "get" in actions:
        if has_many_info:
            lines += [
                f'@router.get("/{{item_id}}", response_model={cls}Read, response_model_by_alias=False)',
                f"async def get_{var}(item_id: str):",
                f'    """get / obtenir / lire — retourne un {tag} par id, avec un résumé '
                f'texte des enregistrements liés."""',
                "    try:",
                f"        item = await {cls}.get(item_id)",
                "    except Exception:",
                "        item = None",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{tag} not found")',
                "    data = item.model_dump()",
                "    data[\"id\"] = str(item.id)",
            ]
            lines += _related_text_lines("    ", "item")
            lines += [
                "    return data",
                "",
                "",
            ]
        else:
            lines += [
                f'@router.get("/{{item_id}}", response_model={cls}, response_model_by_alias=False)',
                f"async def get_{var}(item_id: str):",
                f'    """get / obtenir / lire — retourne un {tag} par id."""',
                "    try:",
                f"        item = await {cls}.get(item_id)",
                "    except Exception:",
                "        item = None",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{tag} not found")',
                "    return item",
                "",
                "",
            ]

    if "create" in actions:
        lines += [
            f'@router.post("/", response_model={cls}, status_code=201, response_model_by_alias=False)',
            f"async def create_{var}(payload: {cls}Create):",
            f'    """create / créer — crée un nouveau {tag}."""',
            f"    item = {cls}(**payload.model_dump())",
        ]
        if program is not None:
            lines += _validation_check_lines(entity, program)
        if has_unique_field:
            lines += [
                "    try:",
                "        await item.insert()",
                "    except DuplicateKeyError:",
                f'        raise HTTPException(status_code=422, detail="{tag}: valeur déjà utilisée / value already in use")',
            ]
        else:
            lines += [
                "    await item.insert()",
            ]
        if "create" in notify_actions:
            notify_kwargs = _notify_kwargs(
                f"item.{recipient_snake}" if recipient_snake else None,
                f"item.{attachment_snake}" if attachment_snake else None,
            )
            lines.append(
                f'    send_email(\n'
                f'        subject="[NOVA] Nouveau {tag} / New {tag}",\n'
                f'        body=f"{tag} #{{item.id}} créé / created.",\n'
                f'        html_body=f"""<html><body style="font-family:sans-serif">'
                f'<h2 style="color:#7c66dc">[NOVA] Nouveau {tag} / New {tag}</h2>'
                f'<p>{tag} #{{item.id}} créé / created.</p></body></html>"""{notify_kwargs},\n'
                f'    )'
            )
        lines += [
            "    return item",
            "",
            "",
        ]

    if "update" in actions:
        lines += [
            f'@router.put("/{{item_id}}", response_model={cls}, response_model_by_alias=False)',
            f"async def update_{var}(item_id: str, payload: {cls}Update):",
            f'    """update / modifier — met à jour un {tag} existant."""',
            "    try:",
            f"        item = await {cls}.get(item_id)",
            "    except Exception:",
            "        item = None",
            "    if item is None:",
            f'        raise HTTPException(status_code=404, detail="{tag} not found")',
            "    for key, value in payload.model_dump(exclude_unset=True).items():",
            "        setattr(item, key, value)",
        ]
        if program is not None:
            lines += _validation_check_lines(entity, program)
        if has_unique_field:
            lines += [
                "    try:",
                "        await item.save()",
                "    except DuplicateKeyError:",
                f'        raise HTTPException(status_code=422, detail="{tag}: valeur déjà utilisée / value already in use")',
            ]
        else:
            lines += [
                "    await item.save()",
            ]
        if "update" in notify_actions:
            notify_kwargs = _notify_kwargs(
                f"item.{recipient_snake}" if recipient_snake else None,
                f"item.{attachment_snake}" if attachment_snake else None,
            )
            lines.append(
                f'    send_email(\n'
                f'        subject="[NOVA] {tag} modifié / updated",\n'
                f'        body=f"{tag} #{{item.id}} mis à jour / updated.",\n'
                f'        html_body=f"""<html><body style="font-family:sans-serif">'
                f'<h2 style="color:#7c66dc">[NOVA] {tag} modifié / updated</h2>'
                f'<p>{tag} #{{item.id}} mis à jour / updated.</p></body></html>"""{notify_kwargs},\n'
                f'    )'
            )
        lines += [
            "    return item",
            "",
            "",
        ]

    if "delete" in actions:
        lines += [
            f'@router.delete("/{{item_id}}", status_code=204)',
            f"async def delete_{var}(item_id: str):",
            f'    """delete / supprimer — supprime un {tag}."""',
            "    try:",
            f"        item = await {cls}.get(item_id)",
            "    except Exception:",
            "        item = None",
            "    if item is None:",
            f'        raise HTTPException(status_code=404, detail="{tag} not found")',
        ]
        if "delete" in notify_actions:
            lines.append("    deleted_id = item.id")
            if recipient_snake:
                lines.append(f"    deleted_to = item.{recipient_snake}")
            if attachment_snake:
                lines.append(f"    deleted_attachment = item.{attachment_snake}")
        lines.append("    await item.delete()")
        if "delete" in notify_actions:
            notify_kwargs = _notify_kwargs(
                "deleted_to" if recipient_snake else None,
                "deleted_attachment" if attachment_snake else None,
            )
            lines.append(
                f'    send_email(\n'
                f'        subject="[NOVA] {tag} supprimé / deleted",\n'
                f'        body=f"{tag} #{{deleted_id}} supprimé / deleted.",\n'
                f'        html_body=f"""<html><body style="font-family:sans-serif">'
                f'<h2 style="color:#7c66dc">[NOVA] {tag} supprimé / deleted</h2>'
                f'<p>{tag} #{{deleted_id}} supprimé / deleted.</p></body></html>"""{notify_kwargs},\n'
                f'    )'
            )
        lines += [
            "    return None",
            "",
            "",
        ]

    return "\n".join(lines) + "\n"


def _generate_mongo_main(program: NovaProgram) -> str:
    app_name = program.app.name if program.app else "NovaApp"
    has_auth = program.auth is not None and program.auth.enabled
    has_uploads = _has_uploads(program)
    lines = [
        _HEADER,
        "from __future__ import annotations",
        "",
        "import importlib",
        "import pkgutil",
        "",
        "from fastapi import FastAPI",
        "from fastapi.middleware.cors import CORSMiddleware",
    ]
    if has_uploads:
        lines.append("from fastapi.staticfiles import StaticFiles")
    lines += [
        "",
        "from .database import init_db",
        "from . import routers_custom",
    ]
    if has_auth:
        lines.append("from .auth import router as auth_router")
    if has_uploads:
        lines.append("from .routers._uploads import router as uploads_router, UPLOADS_DIR")
    if program.queries:
        lines.append("from .routers._requetes import router as requetes_router")
    if program.calendars:
        lines.append("from .routers._ics import router as ics_router")
    for api in program.apis:
        entity = program.get_entity(api.entity)
        if entity is None:
            continue
        table = _table_name(entity)
        lines.append(f"from .routers.{table} import router as {table}_router")
    lines += [
        "",
        f'app = FastAPI(title="{app_name}", description="Généré par NOVA / Generated by NOVA (backend NoSQL)")',
        "",
        "app.add_middleware(",
        "    CORSMiddleware,",
        '    allow_origins=["*"],',
        "    allow_methods=[\"*\"],",
        "    allow_headers=[\"*\"],",
        ")",
        "",
        "",
        '@app.on_event("startup")',
        "async def on_startup() -> None:",
        "    await init_db()",
        "",
        "",
    ]
    if has_uploads:
        lines.append('app.mount("/files", StaticFiles(directory=str(UPLOADS_DIR)), name="files")')
    if has_auth:
        lines.append("app.include_router(auth_router)")
    if has_uploads:
        lines.append("app.include_router(uploads_router)")
    if program.queries:
        lines.append("app.include_router(requetes_router)")
    if program.calendars:
        lines.append("app.include_router(ics_router)")
    for api in program.apis:
        entity = program.get_entity(api.entity)
        if entity is None:
            continue
        table = _table_name(entity)
        lines.append(f"app.include_router({table}_router)")
    lines += [
        "",
        "# Logique métier hors DSL : voir backend/app/routers_custom/example.py",
        "# (même mécanisme d'inclusion automatique que le backend SQL).",
        "for _finder, _mod_name, _ispkg in pkgutil.iter_modules(routers_custom.__path__):",
        '    _custom_mod = importlib.import_module(f".routers_custom.{_mod_name}", package=__package__)',
        '    if hasattr(_custom_mod, "router"):',
        "        app.include_router(_custom_mod.router)",
        "",
        "",
        '@app.get("/health")',
        "def health():",
        '    return {"status": "ok"}',
        "",
    ]
    return "\n".join(lines) + "\n"


_CUSTOM_ROUTER_EXAMPLE_MONGO = '''\
"""
Exemple de routeur "custom" (backend/app/routers_custom/example.py) — variante
backend NoSQL (Beanie/MongoDB). Ce dossier n'est JAMAIS régénéré par
`nova compile` : créé une seule fois, laissé intact ensuite. C'est ici
qu'écrire tout ce que le DSL NOVA ne couvre pas, y compris les points non
supportés par ce backend NoSQL dans ce MVP (`requete`/query, `calendar`,
`has_many` matérialisé — voir la docstring de codegen/api_mongo.py).

Tout module de ce dossier exposant une variable `router` (un
`fastapi.APIRouter`) est automatiquement inclus par app/main.py.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/custom", tags=["custom"])


@router.get("/ping")
def ping():
    """Vérifie que ce routeur custom est bien chargé."""
    return {"status": "custom router actif"}


# ---------------------------------------------------------------------------
# Exemple : validation par expression régulière avant écriture en base.
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")


@router.post("/exemple-validation")
async def exemple_validation(email: str):
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Email invalide")
    # Écriture en base directe via un Document Beanie, comme dans les
    # routeurs générés (voir app/routers/<entite>.py) :
    #   from ..models import MonEntite
    #   item = MonEntite(...)
    #   await item.insert()
    return {"email": email, "valide": True}


@router.get("/exemple-requete-complexe")
async def exemple_requete_complexe():
    """Point de départ pour une requête au-delà du CRUD simple (agrégation
    Mongo...). Remplacez ce corps par votre propre logique, en important vos
    modèles depuis `..models`."""
    return {"exemple": "adaptez cette fonction à vos propres modèles"}
'''


def _generate_mongo_query_router(program: NovaProgram) -> str:
    """Équivalent Mongo de `api_fastapi._generate_query_router` (tâche
    #34) : filtre/`ou:`/tri/limite traduits en filtres Beanie (qui
    supportent nativement les mêmes opérateurs Python que SQLAlchemy sur
    un attribut de `Document` — `Cls.champ > valeur`, etc. — voir
    https://beanie-odm.dev), pas en agrégation Mongo brute. Les jointures
    (`jointure:`) ne sont PAS supportées ici (voir
    `parser._validate_mongo_unsupported_features`) : `Query.joins` est
    donc toujours vide pour tout programme qui atteint cette fonction."""
    has_or_groups = any(q.filter_groups for q in program.queries)
    lines = [
        _HEADER,
        "from __future__ import annotations",
        "",
        "from fastapi import APIRouter",
    ]
    if has_or_groups:
        lines.append("from beanie.operators import Or")
    lines += [
        "",
        "from .. import models",
        "",
        'router = APIRouter(prefix="/requetes", tags=["requetes"])',
        "",
        "",
    ]
    for q in program.queries:
        entity = program.get_entity(q.entity)
        cls = to_pascal_case(entity.name) if entity else to_pascal_case(q.entity)
        slug = to_snake_case(q.name).replace("_", "-")
        fn_name = to_snake_case(q.name)
        lines += [
            f'@router.get("/{slug}", response_model=list[models.{cls}], response_model_by_alias=False)',
            f"async def {fn_name}():",
            f'    """Requête déclarative `requete {q.name} sur {q.entity} {{ ... }}` du fichier .nova (backend NoSQL)."""',
            "    conditions = []",
        ]
        for f in q.filters:
            snake = to_snake_case(f.field)
            lines.append(f"    conditions.append(models.{cls}.{snake} {f.op} {_format_query_value(f.value)})")
        for group in q.filter_groups:
            or_terms = ", ".join(
                f"models.{cls}.{to_snake_case(f.field)} {f.op} {_format_query_value(f.value)}"
                for f in group.filters
            )
            lines.append(f"    conditions.append(Or({or_terms}))")
        lines.append(f"    query = models.{cls}.find(*conditions)")
        if q.order_by:
            snake = to_snake_case(q.order_by)
            sign = "-" if q.order_dir == "desc" else "+"
            lines.append(f"    query = query.sort({sign}models.{cls}.{snake})")
        if q.limit is not None:
            lines.append(f"    query = query.limit({q.limit})")
        lines += [
            "    return await query.to_list()",
            "",
            "",
        ]
    return "\n".join(lines) + "\n"


def _mongo_has_many_relation_info(entity: Entity, program: NovaProgram):
    """Comme `api_fastapi._has_many_relation_info` (même forme de tuple),
    réutilisée telle quelle (elle ne dépend d'aucun mécanisme SQL — seul
    le nom des champs/collections lui importe) : voir _has_many_relation_
    info importé plus haut. Cette fonction est un simple alias pour que le
    nom apparaisse explicitement dans ce module côté lisibilité/tests."""
    return _has_many_relation_info(entity, program)


def _generate_mongo_calendar_ics_router(program: NovaProgram) -> str:
    """Équivalent Mongo de `api_fastapi._generate_calendar_ics_router`
    (tâche #34) : même format iCalendar (RFC 5545) produit par de simples
    f-strings, mais lecture asynchrone via `Document.find_all()` (Motor)
    au lieu de `Session.exec(select(...))` (SQLAlchemy)."""
    lines = [
        _HEADER,
        "from __future__ import annotations",
        "",
        "from datetime import datetime, timezone",
        "",
        "from fastapi import APIRouter, Depends, Response",
        "",
        "from .. import models",
    ]
    cal_roles: dict[str, str | None] = {}
    for cal in program.calendars:
        api = next((a for a in program.apis if a.entity == cal.entity), None)
        cal_roles[cal.name] = api.protected_role if api else None
    if any(cal_roles.values()):
        lines.append("from ..auth import require_role")
    lines.append(_ICS_ESCAPE_HELPER)
    lines += [
        'router = APIRouter(prefix="/ics", tags=["calendriers"])',
        "",
        "",
    ]
    for cal in program.calendars:
        entity = program.get_entity(cal.entity)
        if entity is None:
            continue
        cls = _model_class_name(entity)
        slug = _calendar_ics_slug(cal)
        fn_name = to_snake_case(cal.name)
        date_field_snake = to_snake_case(cal.date_field)
        title_field_snake = to_snake_case(cal.title_field) if cal.title_field else None
        date_field_obj = next((f for f in entity.fields if f.name == cal.date_field), None)
        is_datetime = bool(date_field_obj and date_field_obj.type == "datetime")
        role = cal_roles.get(cal.name)
        route_decorator = f'@router.get("/{slug}.ics"'
        if role:
            route_decorator += f', dependencies=[Depends(require_role("{role}"))]'
        route_decorator += ")"
        title_default = repr(cal.entity)
        title_expr = (
            f'_ics_escape(str(getattr(item, "{title_field_snake}", "") or {title_default}))'
            if title_field_snake
            else f"_ics_escape({title_default})"
        )
        dtstart_expr = (
            "raw_date.strftime('%Y%m%dT%H%M%SZ')"
            if is_datetime
            else "raw_date.strftime('%Y%m%d')"
        )
        dtstart_prefix = "DTSTART" if is_datetime else "DTSTART;VALUE=DATE"
        lines += [
            route_decorator,
            f"async def {fn_name}_ics():",
            f'    """Export iCalendar (.ics) du calendrier `{cal.name}` (source : {cal.entity}, backend NoSQL).',
            f'    Un événement par enregistrement dont `{cal.date_field}` n\'est pas vide."""',
            f"    items = await models.{cls}.find_all().to_list()",
            '    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")',
            "    ics_lines = [",
            '        "BEGIN:VCALENDAR",',
            '        "VERSION:2.0",',
            f'        "PRODID:-//NOVA//{cal.name}//FR",',
            '        "CALSCALE:GREGORIAN",',
            "    ]",
            "    for item in items:",
            f'        raw_date = getattr(item, "{date_field_snake}", None)',
            "        if raw_date is None:",
            "            continue",
            f"        summary = {title_expr}",
            '        ics_lines.append("BEGIN:VEVENT")',
            f'        ics_lines.append(f"UID:{to_snake_case(cal.entity)}-{{item.id}}@nova.local")',
            '        ics_lines.append(f"DTSTAMP:{now_stamp}")',
            f'        ics_lines.append(f"{dtstart_prefix}:{{{dtstart_expr}}}")',
            '        ics_lines.append(f"SUMMARY:{summary}")',
            '        ics_lines.append("END:VEVENT")',
            "    ics_lines.append(\"END:VCALENDAR\")",
            '    return Response(content="\\r\\n".join(ics_lines), media_type="text/calendar")',
            "",
            "",
        ]
    return "\n".join(lines) + "\n"


def generate_backend_mongo(program: NovaProgram) -> dict[str, str]:
    has_auth = program.auth is not None and program.auth.enabled
    has_uploads = _has_uploads(program)
    has_email = program.email is not None

    requirements = [
        "fastapi>=0.110",
        "uvicorn[standard]>=0.29",
        "beanie>=1.26",
        "motor>=3.4",
    ]
    if has_auth:
        requirements += ["bcrypt>=4.0", "python-jose[cryptography]>=3.3", "python-multipart>=0.0.9"]
    elif has_uploads:
        requirements.append("python-multipart>=0.0.9")
    if has_uploads:
        requirements.append("Pillow>=10.0")

    files: dict[str, str] = {
        "backend/app/__init__.py": "",
        "backend/app/models.py": _generate_mongo_models(program),
        "backend/app/database.py": _generate_mongo_database(program),
        "backend/app/routers/__init__.py": "",
        "backend/app/main.py": _generate_mongo_main(program),
        "backend/requirements.txt": "\n".join(requirements) + "\n",
    }
    if has_auth:
        files["backend/app/auth.py"] = _generate_mongo_auth(program)
    if has_uploads:
        files["backend/app/routers/_uploads.py"] = _UPLOADS_ROUTER_TEMPLATE
    if has_email:
        files["backend/app/emailer.py"] = _generate_emailer(program)
    if program.queries:
        files["backend/app/routers/_requetes.py"] = _generate_mongo_query_router(program)
    if program.calendars:
        files["backend/app/routers/_ics.py"] = _generate_mongo_calendar_ics_router(program)

    for api in program.apis:
        entity = program.get_entity(api.entity)
        if entity is None:
            continue
        table = _table_name(entity)
        files[f"backend/app/routers/{table}.py"] = _generate_mongo_router(
            entity,
            api.actions,
            api.protected_role,
            api.notify_actions,
            api.notify_recipient_field,
            api.notify_attachment_field,
            program,
        )
    return files


def generate_backend_scaffold_mongo() -> dict[str, str]:
    """Équivalent Mongo de `api_fastapi.generate_backend_scaffold` — mêmes
    règles (créé une seule fois, jamais réécrit ensuite)."""
    return {
        "backend/app/routers_custom/__init__.py": "",
        "backend/app/routers_custom/example.py": _CUSTOM_ROUTER_EXAMPLE_MONGO,
    }
