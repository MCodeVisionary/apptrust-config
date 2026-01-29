Here is a **ready-to-use `README.md`** you can copy directly into your repository.

---

# 🐸 JFrog Project Automation Framework

This repository provides a fully automated way to create and manage **JFrog Lifecycle Stages, Projects, Repositories, and Applications** using JSON configuration files.

It follows **GitOps principles** so your JFrog platform can be provisioned, audited, and reproduced from source control.

---

# 🚀 What This Tool Does

For every project defined in JSON, the framework will:

1. Create **Global Lifecycle Stages**
2. Create a **JFrog Project**
3. Create **Artifactory Repositories** (local, remote, virtual)
4. Create **JFrog Applications**

All operations use **JFrog REST APIs** and are idempotent (safe to re-run).

---

# 📦 What Gets Created

| Resource      | Description                                        |
| ------------- | -------------------------------------------------- |
| Stages        | Global lifecycle stages (`dev`, `qa`, `prod`, etc) |
| Projects      | JFrog project per team                             |
| Local Repos   | One per stage                                      |
| Remote Repos  | Proxy to upstream (optional)                       |
| Virtual Repos | Unified endpoint (optional)                        |
| Applications  | Used for AppTrust & SDLC flows                     |

---

# 🧠 Built-In Rules

### Stage Handling

* Stages are created **globally** using:

```
POST /access/api/v2/stages
```

* Stages are always converted to **lowercase**
* Stages are applied to repos using:

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

`MachineLearning` repositories are treated as **internal ML model stores** and therefore:

* No remote proxy
* No virtual repo

---

# 📂 Directory Layout

```
.
├── create_jfrog_resources.py
├── projects/
│   ├── pay.json
│   ├── mlt.json
│   └── dev.json
└── README.md
```

Each JSON file may contain **one or more projects**.

---

# 🔐 Prerequisites

You need:

| Requirement    | Description                                 |
| -------------- | ------------------------------------------- |
| JFrog Platform | With Access, Artifactory & AppTrust enabled |
| Access Token   | Platform Admin or Project Admin             |
| Python 3       | Installed                                   |
| curl           | Installed                                   |

---

# 🔑 Environment Variables

Set these before running the script:

```bash
export JPD_URL=https://soleng.jfrog.io
export ACCESS_TOKEN=<your-access-token>
```

---

# ▶️ How to Run

```bash
python3 create_jfrog_resources.py
```

The script will:

1. Load all JSON files from `./projects`
2. Create lifecycle stages
3. Create projects
4. Create repositories
5. Create applications

It can be safely run multiple times.

---

# 📄 Example Project File

```json
{
  "projects": [
    {
      "project_key": "pay",
      "display_name": "Payments",
      "description": "Payments systems",

      "stages": ["DEV", "PROD"],

      "package_types": [
        { "name": "python", "remote_url": "https://pypi.org/simple" },
        { "name": "MachineLearning", "remote_url": "" }
      ],

      "applications": [
        {
          "name": "payment-api",
          "applicationKey": "paymentapi",
          "description": "Payment backend"
        }
      ]
    }
  ]
}
```

---

# 🧩 What Gets Created (Example)

For project `pay`:

| Resource                       |
| ------------------------------ |
| pay-python-dev-local           |
| pay-python-prod-local          |
| pay-python-remote              |
| pay-python-virtual             |
| pay-machinelearning-dev-local  |
| pay-machinelearning-prod-local |
| payment-api (Application)      |

---

# 🛡 Safety

The framework:

* Validates API responses
* Stops on errors
* Avoids duplicate creation
* Uses correct API ordering
* Works with JFrog Access API v2

---

# 🔮 Future Enhancements

This architecture supports:

* Promotion workflows
* Xray policies
* Team-based permissions
* CI/CD onboarding
* Environment separation

---


