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

HEADERS = [
    "-H", f"Authorization: Bearer {JFROG_TOKEN}",
    "-H", "Content-Type: application/json"
]

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
    return f"{project_key}-{name}"

# ==============================
# CHECK EXISTENCE
# ==============================
def project_exists(project_key):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/access/api/v1/projects/{project_key}",
        fail_on_error=False
    )
    return status == "200"

# def stage_exists(project_key, stage_name):
#     status, _ = curl(
#         "GET",
#         f"{JFROG_URL}/access/api/v1/projects/{project_key}/stages/{stage_name}",
#         fail_on_error=False
#     )
#     return status == "200"

def repo_exists(repo_name_str):
    status, _ = curl(
        "GET",
        f"{JFROG_URL}/artifactory/api/repositories/{repo_name_str}",
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
def delete_application(app_name):
    if not app_exists(app_name):
        print(f"ℹ️ Application '{app_name}' does not exist, skipping")
        return

    print(f"🗑️ Deleting application '{app_name}'")
    curl("DELETE", f"{JFROG_URL}/apptrust/api/v1/applications/{app_name}")
    print(f"✅ Deleted application '{app_name}'")

def delete_repo(repo_name_str):
    if not repo_exists(repo_name_str):
        print(f"ℹ️ Repository '{repo_name_str}' does not exist, skipping")
        return

    print(f"🗑️ Deleting repository '{repo_name_str}'")
    curl("DELETE", f"{JFROG_URL}/artifactory/api/repositories/{repo_name_str}")
    print(f"✅ Deleted repository '{repo_name_str}'")

def delete_project(project_key):
    if not project_exists(project_key):
        print(f"ℹ️ Project '{project_key}' does not exist, skipping")
        return

    print(f"🗑️ Deleting project '{project_key}'")
    status, body = curl(
        "DELETE",
        f"{JFROG_URL}/access/api/v1/projects/{project_key}",
        fail_on_error=False
    )
    if status.startswith("4"):
        print(f"❌ Failed to delete project '{project_key}'")
        print(body)
        return
    print(f"✅ Deleted project '{project_key}'")

def delete_stage(project_key, stage_name):
    if not stage_exists(project_key, stage_name):
        print(f"ℹ️ Stage '{stage_name}' for project '{project_key}' does not exist, skipping")
        return

    print(f"🗑️ Deleting stage '{stage_name}' from project '{project_key}'")
    status, _ = curl(
        "DELETE",
        f"{JFROG_URL}/access/api/v1/projects/{project_key}/stages/{stage_name}",
        fail_on_error=False
    )
    if status == "404":
        print(f"⚠️ Stage API not supported or stage already gone, skipping")
        return
    print(f"✅ Deleted stage '{stage_name}'")

# ==============================
# PROCESS ONE PROJECT
# ==============================
def process_project(project):
    project_key = project["project_key"]
    print(f"\n==============================")
    print(f"Cleaning project {project_key}")
    print(f"==============================")

    # 1️⃣ Delete applications first
    for app in project.get("applications", []):
        delete_application(app["name"])

    # 2️⃣ Delete repositories next
    for pkg in project.get("package_types", []):
        pkg_name = pkg["name"]

        # Delete local repos per stage
        for stage in project.get("stages", []):
            stage_lower = stage.lower()
            local_repo_name = repo_name(project_key, f"{pkg_name}-{stage_lower}-local")
            delete_repo(local_repo_name)

        # Delete remote repo
        remote_repo_name = repo_name(project_key, f"{pkg_name}-remote")
        delete_repo(remote_repo_name)

        # Delete virtual repo
        virtual_repo_name = repo_name(project_key, f"{pkg_name}-virtual")
        delete_repo(virtual_repo_name)

    # 3️⃣ Delete project
    delete_project(project_key)

    # 4️⃣ Delete stages last
    # for stage in project.get("stages", []):
    #     delete_stage(project_key, stage)

# ==============================
# MAIN
# ==============================
def main():
    json_files = glob.glob(os.path.join(PROJECTS_DIR, "*.json"))

    if not json_files:
        print("❌ No project JSON files found")
        sys.exit(1)

    for file in json_files:
        print(f"\n📄 Loading {file}")
        with open(file) as f:
            data = json.load(f)

        for project in data.get("projects", []):
            process_project(project)

if __name__ == "__main__":
    main()
