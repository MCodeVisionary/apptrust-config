import json
import subprocess
import sys
import glob
import os

# ==============================
# CONFIG
# ==============================
JFROG_URL = os.getenv("JPD_URL")
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
REMOTE_ONLY = {"nimmodel"}

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

    if fail_on_error and status.startswith("4") and status != "404":
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
# EXISTS CHECKS
# ==============================
def project_exists(project_key):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/access/api/v1/projects/{project_key}",
        fail_on_error=False
    )
    return status == "200"

def repo_exists(name):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/artifactory/api/repositories/{name}",
        fail_on_error=False
    )
    return status == "200"

def app_exists(app_name):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/apptrust/api/v1/applications/{app_name}",
        fail_on_error=False
    )
    return status == "200"

# ==============================
# DELETE FUNCTIONS
# ==============================
def delete_application(name):
    if not app_exists(name):
        print(f"ℹ️ Application '{name}' does not exist, skipping")
        return

    print(f"🗑️ Deleting application '{name}'")
    curl("DELETE", f"{JFROG_URL}/apptrust/api/v1/applications/{name}")
    print(f"✅ Deleted application '{name}'")

def delete_repo(name):
    if not repo_exists(name):
        print(f"ℹ️ Repository '{name}' does not exist, skipping")
        return

    print(f"🗑️ Deleting repository '{name}'")
    curl("DELETE", f"{JFROG_URL}/artifactory/api/repositories/{name}")
    print(f"✅ Deleted repository '{name}'")

def delete_project(key):
    if not project_exists(key):
        print(f"ℹ️ Project '{key}' does not exist, skipping")
        return

    print(f"🗑️ Deleting project '{key}'")
    status, body = curl(
        "DELETE",
        f"{JFROG_URL}/access/api/v1/projects/{key}",
        fail_on_error=False
    )

    if status.startswith("4"):
        print(f"❌ Failed to delete project '{key}'")
        print(body)
        return

    print(f"✅ Deleted project '{key}'")

# ==============================
# PROCESS PROJECT
# ==============================
def process_project(project):
    key = project["project_key"]

    print("\n==============================")
    print(f"Cleaning project {key}")
    print("==============================")

    # 1️⃣ Applications
    for app in project.get("applications", []):
        delete_application(app["name"])

    # 2️⃣ Repositories
    for pkg in project.get("package_types", []):
        pkg_name = pkg["name"]
        lower = pkg_name.lower()

        # Local repos (per stage)
        if lower not in REMOTE_ONLY:
            for stage in project.get("stages", []):
                local = repo_name(key, f"{pkg_name}-{stage.lower()}-local")
                delete_repo(local)

        # Remote repo
        if lower not in NO_REMOTE_NO_VIRTUAL:
            remote = repo_name(key, f"{pkg_name}-remote")
            delete_repo(remote)

        # Virtual repo
        if lower not in NO_REMOTE_NO_VIRTUAL and lower not in REMOTE_ONLY:
            virtual = repo_name(key, f"{pkg_name}-virtual")
            delete_repo(virtual)

    # 3️⃣ Project
    delete_project(key)

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
