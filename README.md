# AutoFiC

> **Remediate vulnerable source code at scale using LLMs and automation.**

[![License](https://img.shields.io/github/license/AutoFiC/autofic-core)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)


## 🚀 Overview

**AutoFiC** is the project, providing a CLI-based automation pipeline for detecting, analyzing, and remediating source code vulnerabilities using the power of LLMs and static analysis tools.

The project is designed for **automated security auditing, bulk code scanning, and mass vulnerability remediation** across multiple repositories, with seamless integration into modern CI/CD workflows.


## ✨ Features

- **Automated Vulnerability Detection**  
  Integrates with tools like **CodeQL, Semgrep, Snyk Code** to identify vulnerabilities in source code.

- **LLM-Powered Remediation**  
  Uses Large Language Models to suggest and patch vulnerabilities automatically.

- **Multi-Repository Support**  
  Bulk-clone and analyze many repositories with configurable filters (e.g., stars, language).

- **CLI Tooling**  
  Command-line interface for easy integration into scripts and CI/CD pipelines.

- **SARIF/JSON Reporting**  
  Outputs results in standardized formats for downstream processing or dashboards.

- **Extensible and Modular**  
  Easily extend with new vulnerability scanners, languages, or custom rules.


## 🏗️ Architecture

```
                                            +---------------------+
                                            |   [GitHub Repos]    |
                                            +----------+----------+
                                                       |
                                                       v
                                            +---------------------+
                                            | Vulnerability Scan  |   (CodeQL / Semgrep / Snyk)
                                            +----------+----------+
                                                       |
                                          SARIF/JSON   v
                                            +---------------------+
                                            |    autofic-core     |
                                            |   (Orchestrator)    |
                                            +----------+----------+
                                                       |
                                    +------------------+-------------------+
                                    |                                      |
                                    v                                      v
                          +---------------------+                +---------------------+
                          |   LLM-based Patch   |<-------------->|   Patch Validator   |
                          |  (OpenAI, etc.)     |                |   (Optional CI)     |
                          +---------------------+                +---------------------+
                                    |
                                    v
                            +---------------+
                            |  Auto PR to   |
                            |   GitHub Repo |
                            +---------------+
```
- **Vulnerability Scan** : Detect vulnerabilities with static analysis tools (CodeQL, Semgrep, Snyk).
- **autofic-core** : Parses findings, sends code to LLM, receives patch suggestions, applies fixes.
- **LLM-based Patch** : Uses large language models (e.g., OpenAI) to generate secure code patches.
- **Patch Validator (Optional)** : Runs CI/tests to validate patches.
- **Auto PR** : Automatically creates a pull request with the fix to the target repository.


## ⚡ Getting Started

### 1. Prerequisites

- **Python 3.8+**
- [CodeQL CLI](https://codeql.github.com/docs/codeql-cli/) *(for CodeQL support)*
- [Semgrep CLI](https://semgrep.dev/docs/cli/) *(for Semgrep support)*
- [Snyk CLI](https://docs.snyk.io/snyk-cli/install-the-snyk-cli) *(optional)*
- GitHub Personal Access Token (if accessing private repos)

### 2. Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/AutoFiC/autofic-core.git
cd autofic-core
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install --upgrade pip; pip install -r requirements.txt; pip install -e .;
````

### 3. Usage

#### 🚦 CLI Example


```bash
python -m autofic_core.cli \
  --repo <Vulnerable Repository> \
  --sast <semgrep|codeql|snyk> \
  --llm \
  --save-dir <Absolute Path> \
  --patch \
  --pr
```

- --repo : Target repository URL
- --sast : Vulnerability scanner to use (semgrep, codeql, etc.)
- --llm : Enable LLM-based remediation
- --save-dir : Directory to store scan results
- --patch : Apply suggested patches
- --pr : Automatically create a Pull Request with fixes

#### 🔄 Typical Workflow
- Scan the target repository for vulnerabilities using static analysis.
- Remediate detected vulnerabilities with automated LLM-based patch suggestions.
- Generate reports and/or create a Pull Request with the security fixes.
- See python -m autofic_core.cli --help for the full list of options and usage details.


## 🧩 Configuration

Configuration is done via CLI flags and/or `.env` files.

* `GITHUB_TOKEN` - For accessing private repositories and creating pull requests.
* `OPENAI_API_KEY` - For LLM-powered patch suggestions.
* `USER_NAME` - Name or ID for audit trails or commit information.
* `DISCORD_WEBHOOK_URL` - (Optional) Discord webhook URL for notifications.
* `SLACK_WEBHOOK_URL` - (Optional) Slack webhook URL for notifications.


## 🤝 Contributing

We welcome all contributions!

1. Fork the repo and create your branch : `git checkout -b feature/your-feature`
2. Commit your changes : `git commit -am 'Add new feature'`
3. Push to the branch : `git push origin feature/your-feature`
4. Open a Pull Request


## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](https://github.com/AutoFiC/autofic-core/blob/dev/LICENSE) file for details.


## 🙋 Contact

* Issues/Feature Requests : [GitHub Issues](https://github.com/AutoFiC/autofic-core/issues)
* Main Team : [AutoFiC Organization](https://github.com/AutoFiC)
* Main Page : [AutoFiC Official](https://autofic.github.io)


## 👨‍💻 Developers

| Name | GitHub | Role |
|------|--------|------|
| Minchae Kim | [@minxxcozy](https://github.com/minxxcozy) | 👩🏻‍💻 Development Team |
| Eunsol Kim | [@eunsol1530](https://github.com/eunsol1530) | 👩🏻‍💻 Development Team |
| Jeongmin Oh | [@soonae](https://github.com/soonnae) | 👩🏻‍💻 Development Team |
| Inyeong Jang | [@inyeongjang](https://github.com/inyeongjang) | 👩🏻‍💻 Development Team |
| Hongseo Jang | [@pxxguin](https://github.com/pxxguin) | 🔬 Research Team |
| Yunji Jeong | [@jungyun404](https://github.com/jungyun404) | 🔬 Research Team |
| Yunjeong Choe | [@yjchoe818](https://github.com/yjchoe818) | 🔬 Research Team |
| Seonju Park | [@seoonju](https://github.com/seoonju) | 🔬 Research Team |
| Suhyun Park | [@lovehyun](https://github.com/lovehyun) | 👨🏻‍🏫 Mentor |
| Changhyun Lee | [@eeche](https://github.com/eeche) | 👨🏻‍🏫 Project Leader |