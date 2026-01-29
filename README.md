Got it — the formatting you pasted **is correct GitHub-Flavored Markdown** and the reason it “didn’t look right” earlier is because GitHub is very strict about **spacing, fences, and headers**.

Below is a **clean, GitHub-perfect `README.md`** based on your **actual project model (including `MachineLearning` rules and your sample JSON)**.
You can paste this directly into GitHub and it will render exactly as intended.

---

# 🐸 JFrog Project Automation Framework

This repository provides a fully automated way to create and manage **JFrog Lifecycle Stages, Projects, Repositories, and Applications** using JSON configuration files.

It follows **GitOps principles** so your JFrog platform can be provisioned, audited, and reproduced from source control.

---

## 🚀 What This Tool Does

For every project defined in JSON, the framework will:

1. Create **Global Lifecycle Stages**
2. Create a **JFrog Project**
3. Create **Artifactory Repositories**
4. Create **JFrog Applications (AppTrust)**

All operations use **JFrog REST APIs** and are **idempotent** (safe to re-run).

---

## 📦 What Gets Created

| Resource      | Description                                  |
| ------------- | -------------------------------------------- |
| Stages        | Global lifecycle stages (`dev`, `prod`, etc) |
| Projects      | One JFrog project per team                   |
| Local Repos   | One per package type per stage               |
| Remote Repos  | Proxy to upstream (optional)                 |
| Virtual Repos | Unified endpoint (optional)                  |
| Applications  | Used for AppTrust & SDLC flows               |

---

## 🧠 Built-In Rules

### Lifecycle Stages

* Created globally using:

```
POST /access/api/v2/stages
```

* All stage names are **lower-cased**
* Stages are applied to repositories as:

```
env=dev
env=prod
```

---

### Package Type Rules

| Package Type    | Local | Remote | Virtual |
| --------------- | ----- | ------ | ------- |
| python          | ✅     | ✅      | ✅       |
| docker          | ✅     | ✅      | ✅       |
| HuggingFaceML   | ✅     | ✅      | ✅       |
| MachineLearning | ✅     | ❌      | ❌       |

`MachineLearning` is treated as an **internal ML model store**:

* No remote proxy
* No virtual repository

---

## 📂 Repository Structure

```
.
├── create_jfrog_resources.py
├── projects/
│   ├── mlt.json
│   ├── pay.json
│   └── dev.json
└── README.md
```

Each JSON file may contain **one or more projects**.

---

## 🔐 Prerequisites

You need:

| Requirement    | Description                            |
| -------------- | -------------------------------------- |
| JFrog Platform | Access, Artifactory & AppTrust enabled |
| Access Token   | Platform Admin or Project Admin        |
| Python 3       | Installed                              |
| curl           | Installed                              |

---

## 🔑 Environment Variables

```bash
export JPD_URL=https://{{JPDURL}}
export ACCESS_TOKEN=<your-access-token>
```

---

## ▶️ How to Run

```bash
python3 create_jfrog_resources.py
```

The script will:

1. Load all JSON files from `./projects`
2. Create global lifecycle stages
3. Create JFrog projects
4. Create repositories
5. Create applications

It can be run safely multiple times.

---

## 📄 Example `projects/mlt.json`

```json
{
  "projects": [
    {
      "project_key": "mlt",
      "display_name": "ML Team",
      "description": "ML team workspace",

      "stages": ["DEV", "PROD"],

      "package_types": [
        { "name": "python", "remote_url": "https://pypi.org/simple" },
        { "name": "docker", "remote_url": "https://registry-1.docker.io/" },
        { "name": "HuggingFaceML", "remote_url": "https://huggingface.co" },
        { "name": "MachineLearning", "remote_url": "" }
      ],

      "applications": [
        {
          "name": "ml-app",
          "description": "this is ML application",
          "applicationKey": "mlapp"
        }
      ]
    }
  ]
}
```

---

## 🧩 What Gets Created (Example)

For project `mlt`:

| Resource                       |
| ------------------------------ |
| mlt-python-dev-local           |
| mlt-python-prod-local          |
| mlt-python-remote              |
| mlt-python-virtual             |
| mlt-docker-dev-local           |
| mlt-docker-prod-local          |
| mlt-docker-remote              |
| mlt-docker-virtual             |
| mlt-huggingfaceml-dev-local    |
| mlt-huggingfaceml-prod-local   |
| mlt-huggingfaceml-remote       |
| mlt-huggingfaceml-virtual      |
| mlt-machinelearning-dev-local  |
| mlt-machinelearning-prod-local |
| ml-app (Application)           |

---

## 🛡 Safety & Reliability

The framework:

* Validates all API responses
* Stops on failure
* Avoids duplicate creation
* Uses correct API ordering
* Uses **JFrog Access API v2** for lifecycle stages

---

## 🔮 Roadmap

This architecture supports:

* Promotion pipelines
* Xray security policies
* Environment-based access control
* CI/CD onboarding
* Multi-team GitOps

