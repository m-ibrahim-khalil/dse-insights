#!/usr/bin/env bash
# Create or update .env on a fresh clone, generating every secret locally.
#
# Also adds keys that appeared in .env.example since .env was written, so an
# existing checkout picks up new configuration instead of failing with an
# unset-variable warning halfway through `docker compose up`.
#
# Secrets are generated only when still blank: regenerating the Fernet key would
# make every connection already stored in Airflow's metadata database
# undecryptable.
set -euo pipefail

cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; echo "created .env from .env.example"; }

python3 - "$(id -u)" <<'PY'
import base64, os, pathlib, re, sys

uid = sys.argv[1]
env, example = pathlib.Path(".env"), pathlib.Path(".env.example")

def keys(text):
    return {m.group(1) for m in re.finditer(r"^([A-Z0-9_]+)=", text, re.M)}

lines = env.read_text().splitlines()
missing = [
    line for line in example.read_text().splitlines()
    if (m := re.match(r"^([A-Z0-9_]+)=", line)) and m.group(1) not in keys(env.read_text())
]
if missing:
    lines += ["", "# Added from .env.example"] + missing

def is_secret(key):
    # Anything that looks like a credential and was left blank. The warehouse
    # password is deliberately excluded: it is a documented local default and
    # changing it would orphan an existing warehouse volume.
    return key != "DSE_PG_PASSWORD" and key.endswith(("_KEY", "_SECRET", "_PASSWORD"))

added, generated, out = [m.split("=")[0] for m in missing], [], []
for line in lines:
    key, sep, value = line.partition("=")
    if key == "AIRFLOW_UID":
        out.append(f"AIRFLOW_UID={uid}")
    elif sep and value == "" and is_secret(key):
        out.append(f"{key}={base64.urlsafe_b64encode(os.urandom(32)).decode()}")
        generated.append(key)
    else:
        out.append(line)

env.write_text("\n".join(out) + "\n")
print("added keys :", ", ".join(added) or "none")
print("generated  :", ", ".join(generated) or "none")
PY
echo "environment ready"
