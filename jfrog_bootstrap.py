import json
import subprocess
import sys
import glob
import os
import time

def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

# ==============================
# CONFIG
# ==============================
load_env_file()
JFROG_URL = os.getenv("JPD_URL")          # https://soleng.jfrog.io
JFROG_TOKEN = os.getenv("ACCESS_TOKEN")
PROJECTS_DIR = "./projects"

if not JFROG_URL or not JFROG_TOKEN:
    print("❌ JPD_URL or ACCESS_TOKEN not set")
    sys.exit(1)

HEADERS = [
    "-H", f"Authorization: Bearer {JFROG_TOKEN}",
    "-H", "Content-Type: application/json"
]

NO_REMOTE_NO_VIRTUAL = {"machinelearning"}   # Local only
REMOTE_ONLY = {"nimmodel"}                   # Remote only

# ==============================
# PACKAGE TYPE NORMALIZATION
# ==============================
def normalize_package_type(pkg_name):
    mapping = {
        "python": "pypi",
        "pypi": "pypi",
        "npm": "npm",
        "maven": "maven",
        "gradle": "gradle",
        "docker": "docker",
        "helm": "helm",
        "nuget": "nuget",
        "terraform": "terraform",
        "go": "go",
        "rpm": "rpm",
        "debian": "debian",
        "generic": "generic",
        "machinelearning": "machinelearning",
        "nimmodel": "nimmodel"
    }
    return mapping.get(pkg_name.lower(), pkg_name.lower())

def get_repo_layout_ref(pkg_type):
    layout_mapping = {
        "maven": "maven-2-default",
        "gradle": "maven-2-default",
        "npm": "npm-default",
        "pypi": "simple-default",
        "docker": "docker-default",
        "helm": "helm-default",
        "nuget": "nuget-default",
        "terraform": "terraform-default",
        "go": "go-default",
        "rpm": "rpm-default",
        "debian": "debian-default",
        "generic": "simple-default",
        "machinelearning": "simple-default",
        "nimmodel": "simple-default"
    }
    return layout_mapping.get(pkg_type.lower(), "simple-default")

# ==============================
# CURL HELPER
# ==============================
def curl(method, url, payload=None, fail_on_error=True):
    cmd = ["curl", "-s", "-w", "%{http_code}", "-X", method] + HEADERS
    if payload:
        cmd += ["-d", json.dumps(payload)]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    body = result.stdout[:-3]
    status = result.stdout[-3:]

    if fail_on_error and status.startswith("4"):
        print(f"❌ {method} {url} failed ({status})")
        print(body)
        sys.exit(1)

    return status, body

# ==============================
# UTILITY
# ==============================
def repo_name(project_key, name):
    return f"{project_key}-{name}".lower()

# ==============================
# GLOBAL STAGES (Lifecycle v2)
# ==============================
def stage_exists(stage):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/access/api/v2/stages/{stage.lower()}",
        fail_on_error=False
    )
    return status == "200"

def create_stage(stage):
    stage_upper = stage.upper()
    stage_lower = stage.lower()

    if stage_exists(stage_lower):
        print(f"ℹ️ Stage '{stage_upper}' already exists")
        return

    print(f"🚀 Creating global stage '{stage_upper}'")

    payload = {
        "name": stage_lower,
        "description": f"{stage_upper} lifecycle stage"
    }

    status, body = curl(
        "POST",
        f"{JFROG_URL}/access/api/v2/stages/",
        payload,
        fail_on_error=False
    )

    if status == "409":
        print(f"ℹ️ Stage '{stage_upper}' already exists")
    elif status.startswith("4"):
        print(f"❌ Failed to create stage '{stage_upper}'")
        print(body)
        sys.exit(1)
    else:
        print(f"✅ Stage '{stage_upper}' created")

# ==============================
# PROJECTS
# ==============================
def project_exists(key):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/access/api/v1/projects/{key}",
        fail_on_error=False
    )
    return status == "200"

def create_project(p):
    key = p["project_key"]

    if project_exists(key):
        print(f"ℹ️ Project '{key}' already exists")
        return

    print(f"🚀 Creating project '{key}'")

    payload = {
        "project_key": key,
        "display_name": p["display_name"],
        "description": p.get("description", "")
    }

    status, body = curl(
        "POST",
        f"{JFROG_URL}/access/api/v1/projects",
        payload,
        fail_on_error=False
    )

    if status == "409":
        print(f"ℹ️ Project '{key}' already exists")
        return
    elif status.startswith("4"):
        print(f"❌ Failed to create project '{key}'")
        print(body)
        sys.exit(1)

    for _ in range(10):
        if project_exists(key):
            print(f"✅ Project '{key}' is ready")
            return
        time.sleep(2)

    print(f"❌ Project '{key}' not visible after creation")
    sys.exit(1)

# ==============================
# REPOSITORIES
# ==============================
def repo_exists(name):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/artifactory/api/repositories/{name}",
        fail_on_error=False
    )
    return status == "200"

def create_local_repo(name, pkg_type, project_key, stage):
    if repo_exists(name):
        print(f"ℹ️ Local repo '{name}' already exists")
        return

    print(f"📦 Creating local repo '{name}' → {stage}")

    payload = {
        "rclass": "local",
        "packageType": pkg_type,
        "repoLayoutRef": get_repo_layout_ref(pkg_type),
        "projectKey": project_key,
        "xrayIndex": True,
        "properties": {
            "env": [stage],
            "project": [project_key]
        }
    }

    curl("PUT", f"{JFROG_URL}/artifactory/api/repositories/{name}", payload)

def create_remote_repo(name, pkg_type, url, project_key):
    if repo_exists(name):
        print(f"ℹ️ Remote repo '{name}' already exists")
        return

    print(f"🌐 Creating remote repo '{name}' → DEV")

    payload = {
        "rclass": "remote",
        "packageType": pkg_type,
        "repoLayoutRef": get_repo_layout_ref(pkg_type),
        "url": url,
        "projectKey": project_key,
        "properties": {
            "env": ["DEV"],
            "project": [project_key]
        }
    }

    curl("PUT", f"{JFROG_URL}/artifactory/api/repositories/{name}", payload)

def create_virtual_repo(name, pkg_type, repos, project_key):
    if repo_exists(name):
        print(f"ℹ️ Virtual repo '{name}' already exists")
        return

    print(f"🧩 Creating virtual repo '{name}' → DEV")

    payload = {
        "rclass": "virtual",
        "packageType": pkg_type,
        "repoLayoutRef": get_repo_layout_ref(pkg_type),
        "repositories": repos,
        "defaultDeploymentRepo": repos[0],
        "projectKey": project_key,
        "properties": {
            "env": ["DEV"],
            "project": [project_key]
        }
    }

    curl("PUT", f"{JFROG_URL}/artifactory/api/repositories/{name}", payload)

# ==============================
# APPLICATIONS
# ==============================
def create_application(app, project_key):
    print(f"🚀 Creating application '{app['name']}'")

    payload = {
        "application_name": app["name"],
        "application_key": app.get("applicationKey", ""),
        "description": app.get("description", ""),
        "project_key": project_key
    }

    status, body = curl(
        "POST",
        f"{JFROG_URL}/apptrust/api/v1/applications",
        payload,
        fail_on_error=False
    )

    if status == "409":
        print(f"ℹ️ Application '{app['name']}' already exists")
    elif status.startswith("4"):
        print(f"❌ Failed to create application '{app['name']}'")
        print(body)
        sys.exit(1)
    else:
        print(f"✅ Application '{app['name']}' created")

# ==============================
# PROCESS PROJECT
# ==============================
def process_project(p):
    key = p["project_key"]

    print("\n==============================")
    print(f"Processing project {key}")
    print("==============================")

    # 1️⃣ Stages
    for s in p.get("stages", []):
        create_stage(s)

    # 2️⃣ Project
    create_project(p)

    # 3️⃣ Repositories
    for pkg in p["package_types"]:
        pkg_name = pkg["name"]
        pkg_lower = pkg_name.lower()
        pkg_type = normalize_package_type(pkg_name)
        remote_url = pkg.get("remote_url", "")

        # NimModel → Remote only
        if pkg_lower in REMOTE_ONLY:
            remote_repo = repo_name(key, f"{pkg_name}-remote")
            create_remote_repo(remote_repo, pkg_type, remote_url, key)
            continue

        local_repos = []
        for s in p.get("stages", []):
            stage_upper = s.upper()
            repo = repo_name(key, f"{pkg_name}-{s.lower()}-local")
            create_local_repo(repo, pkg_type, key, stage_upper)
            local_repos.append(repo)

        # MachineLearning → Local only
        if pkg_lower in NO_REMOTE_NO_VIRTUAL:
            continue

        remote_repo = repo_name(key, f"{pkg_name}-remote")
        create_remote_repo(remote_repo, pkg_type, remote_url, key)

        virtual_repo = repo_name(key, f"{pkg_name}-virtual")
        create_virtual_repo(virtual_repo, pkg_type, local_repos + [remote_repo], key)

    # 4️⃣ Applications
    for app in p.get("applications", []):
        create_application(app, key)

# ==============================
# MAIN
# ==============================
def main():
    files = glob.glob(os.path.join(PROJECTS_DIR, "*.json"))
    if not files:
        print("❌ No project JSON files found")
        sys.exit(1)

    for f in files:
        print(f"\n📄 Loading {f}")
        with open(f) as fh:
            data = json.load(fh)

        for project in data.get("projects", []):
            process_project(project)

if __name__ == "__main__":
    main()
