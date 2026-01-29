import json
import subprocess
import sys
import glob
import os
import time

# ==============================
# CONFIG
# ==============================
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

NO_REMOTE_NO_VIRTUAL = {"machinelearning"}

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
    return f"{project_key}-{name}"

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
    stage = stage.lower()

    if stage_exists(stage):
        print(f"ℹ️ Stage '{stage}' already exists")
        return

    print(f"🚀 Creating global stage '{stage}'")

    payload = {
        "name": stage,
        "description": f"{stage} lifecycle stage"
    }

    status, body = curl(
        "POST",
        f"{JFROG_URL}/access/api/v2/stages/",
        payload,
        fail_on_error=False
    )

    if status == "409":
        print(f"ℹ️ Stage '{stage}' already exists")
    elif status.startswith("4"):
        print(f"❌ Failed to create stage '{stage}'")
        print(body)
        sys.exit(1)
    else:
        print(f"✅ Stage '{stage}' created")

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

    # wait for propagation
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

def create_local_repo(name, pkg, project_key, stage):
    if repo_exists(name):
        print(f"ℹ️ Local repo '{name}' already exists")
        return

    print(f"📦 Creating local repo '{name}'")

    payload = {
        "rclass": "local",
        "packageType": pkg,
        "projectKey": project_key,
        "xrayIndex": True,
        "properties": {
            "env": [stage.lower()],
            "project": [project_key]
        }
    }

    curl("PUT", f"{JFROG_URL}/artifactory/api/repositories/{name}", payload)

def create_remote_repo(name, pkg, url, project_key):
    if repo_exists(name):
        print(f"ℹ️ Remote repo '{name}' already exists")
        return

    print(f"🌐 Creating remote repo '{name}'")

    payload = {
        "rclass": "remote",
        "packageType": pkg,
        "url": url,
        "projectKey": project_key
    }

    curl("PUT", f"{JFROG_URL}/artifactory/api/repositories/{name}", payload)

def create_virtual_repo(name, pkg, repos, project_key):
    if repo_exists(name):
        print(f"ℹ️ Virtual repo '{name}' already exists")
        return

    print(f"🧩 Creating virtual repo '{name}'")

    payload = {
        "rclass": "virtual",
        "packageType": pkg,
        "repositories": repos,
        "defaultDeploymentRepo": repos[0],
        "projectKey": project_key
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

    # 1️⃣ Global stages
    for s in p.get("stages", []):
        create_stage(s)

    # 2️⃣ Project
    create_project(p)

    # 3️⃣ Repositories
    for pkg in p["package_types"]:
        pkg_name = pkg["name"]
        pkg_lower = pkg_name.lower()
        remote_url = pkg.get("remote_url", "")

        local_repos = []
        for s in p.get("stages", []):
            repo = repo_name(key, f"{pkg_name}-{s.lower()}-local")
            create_local_repo(repo, pkg_name, key, s)
            local_repos.append(repo)

        if pkg_lower in NO_REMOTE_NO_VIRTUAL:
            print(f"⏭️ Skipping remote & virtual for '{pkg_name}'")
            continue

        remote_repo = repo_name(key, f"{pkg_name}-remote")
        create_remote_repo(remote_repo, pkg_name, remote_url, key)

        virtual_repo = repo_name(key, f"{pkg_name}-virtual")
        create_virtual_repo(virtual_repo, pkg_name, local_repos + [remote_repo], key)

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
