# AI-Powered Code Intelligence & Review Platform

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Java](https://img.shields.io/badge/Java-21-orange)
![C%2FC%2B%2B](https://img.shields.io/badge/C%2FC%2B%2B-Cppcheck-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-blue)
![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-black)
![Qwen3](https://img.shields.io/badge/Qwen3-8B-purple)
![PMD](https://img.shields.io/badge/PMD-Java%20Analysis-blue)
![Cppcheck](https://img.shields.io/badge/Cppcheck-C%2FC%2B%2B-orange)
![License](https://img.shields.io/badge/License-Educational-orange)

A full-stack code intelligence platform that combines deterministic static analysis, engineering metrics, risk scoring, historical tracking, and local AI explanations to help developers understand and improve source code.

The platform accepts source code through paste, ZIP upload, or GitHub repository input. It automatically routes supported files to the appropriate analysis tools, converts their findings into one common issue format, calculates deterministic project metrics and scores, and uses a local LLM to explain important findings using the actual source-code context.

> **Core principle:** static-analysis tools are the source of truth for issue detection, severity, metrics, and scoring. The AI layer enriches the results with understandable explanations and practical fixes.

---

## 🚀 Current Capabilities

The current implementation supports:

- Python analysis with **Flake8 + Bandit**
- Java analysis with **PMD**
- C and C++ analysis with **Cppcheck**
- Paste-code, ZIP-upload, and GitHub-repository ingestion
- Automatic supported-language routing
- Unified issue normalization across analysis tools
- Severity and category mapping
- Lines of Code and issue-density metrics
- Deterministic 0–100 project scoring
- Low / Medium / High project risk levels
- File-level issue concentration and heatmap data
- Recurring-issue analysis
- Historical scan storage and trend analysis
- Local AI explanations using **Ollama + Qwen3 8B**
- Source-code-aware AI context around reported findings
- AI-generated project summaries and recommendations
- Rule-based fallback explanations when the local LLM is unavailable
- React dashboard for scan results and project health

---

## 🏗️ System Architecture

![Architecture Diagram](docs/architecture.png)

### End-to-end pipeline

```text
                 SOURCE CODE INPUT
        ┌────────────┼────────────┐
        │            │            │
      Paste        ZIP         GitHub
        │            │            │
        └────────────┼────────────┘
                     ↓
                INGESTION LAYER
                     ↓
              LANGUAGE DETECTION
                     ↓
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
    Python         Java         C / C++
       ↓             ↓             ↓
 Flake8+Bandit      PMD        Cppcheck
       └─────────────┼─────────────┘
                     ↓
             ISSUE NORMALIZATION
                     ↓
               METRICS ENGINE
                     ↓
          DETERMINISTIC SCORING
                     ↓
             FINDING PRIORITIZATION
                     ↓
             SOURCE CONTEXT READ
                     ↓
          LOCAL AI ENRICHMENT
              Ollama + Qwen3
                     ↓
            SCAN + HISTORY STORAGE
                     ↓
                REACT DASHBOARD
```

The pipeline is deliberately separated into deterministic analysis and AI enrichment. This prevents the LLM from changing scanner findings, severity, project metrics, or the calculated score.

---

## 🔎 Multi-Language Static Analysis

### Python — Flake8 + Bandit

**Flake8** analyzes Python code quality and style, including linting violations, unused imports, formatting problems, and other maintainability issues.

**Bandit** analyzes Python code for security-sensitive coding patterns and potentially unsafe operations.

### Java — PMD

**PMD** performs static analysis on Java source code using Java quality and security rules.

PMD priority is normalized into the platform's severity model:

| PMD Priority | Platform Severity |
|---:|---|
| 1–2 | High |
| 3 | Medium |
| 4–5 | Low |

### C / C++ — Cppcheck

**Cppcheck** performs static analysis on C and C++ source code and reports potential bugs, warnings, style problems, performance concerns, portability issues, and security-related findings when applicable.

Supported extensions:

- C: `.c`, `.h`
- C++: `.cc`, `.cpp`, `.cxx`, `.hh`, `.hpp`, `.hxx`

Cppcheck XML output is converted into the platform's common issue structure. Informational metadata produced by Cppcheck, such as checker-report information, is excluded from source-code issue counts and scoring.

---

## 🧩 Unified Issue Model

Different static-analysis tools produce different output formats. The normalization layer converts them into a common structure so the rest of the platform can process findings consistently.

Conceptually, a normalized issue contains:

```text
UnifiedIssue
├── tool
├── rule_id
├── severity
├── confidence
├── file
├── line
├── message
└── category
```

Additional tool-specific information can be retained when useful, such as PMD priority/ruleset or Cppcheck CWE information.

### Why normalization matters

Without normalization, every dashboard, metrics, scoring, and AI component would need separate logic for each scanner. The unified model provides one common interface for all supported languages.

---

## 📊 Engineering Metrics

The metrics layer calculates project-level and file-level information independently of the AI layer.

Current metrics include:

- Total issues
- Severity breakdown
- Issues by analysis tool
- Lines of Code (LOC)
- Issue density
- File-level issue concentration
- Top refactor-priority files
- Severity heatmap data
- Recurring issues
- Penalty breakdown
- Historical scan trends

LOC is calculated from the active supported-language analysis output rather than from the AI layer.

---

## 🎯 Deterministic Risk Scoring

The scoring engine calculates a project score from static-analysis results and engineering metrics.

The score is deterministic and independent of the LLM.

Conceptually:

```text
final_score = clamp(100 - penalty, 0, 100)
```

The scoring process considers factors such as issue severity and issue density, then produces a score from 0 to 100.

### Risk levels

| Score | Risk Level |
|---:|---|
| 80–100 | Low Risk |
| 50–79 | Medium Risk |
| 0–49 | High Risk |

The AI does **not** recalculate or override this score.

---

## 🧠 Local AI Code Review

The platform includes a local AI enrichment layer powered by:

- **Ollama** — local LLM runtime
- **Qwen3 8B** — default local model

The current implementation communicates with Ollama using Python's standard-library HTTP client, so an OpenAI SDK or OpenAI API key is not required for the current AI path.

### AI workflow

```text
Static-analysis finding
          ↓
Select important findings
          ↓
Read source-code context
          ↓
Send finding + context to Ollama
          ↓
Qwen3 8B generates structured response
          ↓
Validate/use explanation
          ↓
Display in dashboard
```

### Source-code-aware context

For important findings, the backend reads a small window around the reported source line. The target line is marked clearly, and the source path is resolved inside the scan input directory before reading.

This allows the model to explain the actual code instead of relying only on a scanner message.

### AI output

For selected findings, the model generates:

- **Explanation** — what the code is doing and why it was flagged
- **Fix** — a practical code-specific improvement
- **Risk** — the realistic potential risk
- **Impact** — the realistic consequence

The project summary can also include:

- Overall project assessment
- Priority action
- Score explanation
- Security overview
- Quality overview
- Recommendations

### AI safety and consistency rules

The AI layer is instructed to:

- Treat scanner severity as authoritative
- Never increase the supplied severity
- Avoid inventing attacker capabilities
- Avoid inventing unsupported attack scenarios
- Distinguish potential issues from confirmed vulnerabilities
- Use source code as the primary evidence for explanations
- Avoid describing low/medium findings as high/critical
- Provide specific fixes rather than generic advice
- Keep security claims tied to actual security evidence

If the local LLM is unavailable, the platform can continue using deterministic analysis and rule-based explanations.

---

## 🖥️ Dashboard

The frontend provides an interactive interface for creating scans and reviewing project health.

### Input methods

#### Paste Code

Paste source code directly into the application and scan it.

#### Upload ZIP

Upload a project archive containing supported source files.

#### GitHub Repository

Provide a GitHub repository for ingestion and analysis.

### Dashboard features

- Scan creation and monitoring
- Project score
- Risk level
- Total issues
- Lines of Code
- Severity distribution
- Issues by analysis tool
- Top risky findings
- AI explanations
- AI fixes and impact descriptions
- Security and quality summaries
- Priority actions
- Recommendations
- File-level issue information
- Heatmap information
- Recurring issues
- Historical scan records
- Project trend charts
- Raw scan information

---

## 🔄 Scan Lifecycle

```text
1. Create scan
2. Receive source code
3. Ingest files
4. Detect supported languages
5. Route files to analysis tools
6. Run static analysis
7. Normalize findings
8. Calculate metrics
9. Calculate deterministic score
10. Prioritize important findings
11. Read source-code context
12. Generate local AI explanations
13. Generate project summary
14. Store scan results
15. Update history
16. Display results in dashboard
```

### Language routing

```text
.py
 ↓
Flake8 + Bandit

.java
 ↓
PMD

.c / .h
 ↓
Cppcheck

.cc / .cpp / .cxx / .hh / .hpp / .hxx
 ↓
Cppcheck
```

All normalized findings then follow the same downstream path:

```text
Unified Issues
      ↓
   Metrics
      ↓
   Scoring
      ↓
AI Enrichment
      ↓
 Dashboard
```

---

## 🏛️ Backend Architecture

```text
backend/app/
├── api/
│   └── routes/
│       ├── scans.py
│       └── multi_language_scans.py
│
├── services/
│   ├── ai/
│   │   ├── generator.py
│   │   ├── llm_generator.py
│   │   ├── rules.py
│   │   └── history/
│   │
│   ├── history/
│   ├── ingestion/
│   ├── pipeline/
│   │   └── simple_pipeline.py
│   ├── processors/
│   │   ├── normalize.py
│   │   ├── normalize_pmd.py
│   │   ├── normalize_cppcheck.py
│   │   └── metrics.py
│   ├── runners/
│   │   ├── flake8_runner.py
│   │   ├── bandit_runner.py
│   │   ├── pmd_runner.py
│   │   ├── cppcheck_runner.py
│   │   └── runner_utils.py
│   └── scoring/
│
└── main.py
```

### Important components

| Component | Purpose |
|---|---|
| `multi_language_scans.py` | Handles multi-language scan inputs and routes supported files |
| `simple_pipeline.py` | Coordinates the complete analysis pipeline |
| `flake8_runner.py` | Runs Flake8 for Python quality analysis |
| `bandit_runner.py` | Runs Bandit for Python security analysis |
| `pmd_runner.py` | Runs PMD for Java analysis |
| `cppcheck_runner.py` | Runs Cppcheck for C/C++ analysis |
| `normalize.py` | Normalizes Flake8/Bandit findings and builds unified issues |
| `normalize_pmd.py` | Converts PMD findings into the unified issue model |
| `normalize_cppcheck.py` | Converts Cppcheck findings into the unified issue model |
| `metrics.py` | Calculates project engineering metrics |
| `scoring/` | Calculates deterministic project risk score |
| `generator.py` | Coordinates AI enrichment and project AI output |
| `llm_generator.py` | Communicates with the local Ollama model |
| `rules.py` | Provides rule-based explanation fallback |
| `history/` | Stores and retrieves historical scan information |

---

## 🧰 Technology Stack

### Backend

- Python 3.x
- FastAPI
- Flake8
- Bandit
- PMD
- Cppcheck
- Java 21
- Ollama
- Qwen3 8B

### Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- Recharts

### Storage

- Local filesystem
- JSON scan artifacts
- JSONL historical data

---

## 📁 Project Structure

```text
ai-code-intelligence-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   ├── history/
│   │   │   ├── ingestion/
│   │   │   ├── pipeline/
│   │   │   ├── processors/
│   │   │   ├── runners/
│   │   │   └── scoring/
│   │   └── main.py
│   │
│   └── storage/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── public/
│
└── docs/
    ├── architecture.png
    └── dashboard.png
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Manojmanu696/ai-code-intelligence-platform.git
cd ai-code-intelligence-platform
```

### 2. Backend environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Java and PMD

Java analysis requires a JDK and PMD available on the system PATH.

```bash
java -version
javac -version
pmd --version
```

The project is currently configured/documented around Java 21 and PMD 7.x.

### 4. C/C++ analysis

Cppcheck must be available on the system PATH.

```bash
cppcheck --version
```

### 5. Local AI

Install and run Ollama, then make sure the configured model is available:

```bash
ollama list
```

The default project model is:

```text
qwen3:8b
```

The local Ollama endpoint used by the application is:

```text
http://localhost:11434/api/generate
```

### 6. Start the backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

### 7. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Example Analysis Flow

A project containing multiple languages can be analyzed through the same platform:

```text
project/
├── app.py
├── security.py
├── Main.java
├── service.c
└── engine.cpp
```

The platform routes the files as follows:

```text
app.py / security.py
        ↓
  Flake8 + Bandit

Main.java
    ↓
   PMD

service.c / engine.cpp
        ↓
    Cppcheck
```

The findings are then merged into one common result set for metrics, scoring, prioritization, and dashboard display.

---

## 🔐 Design Principles

### Deterministic analysis first

Static-analysis tools provide the authoritative findings. The AI does not replace them.

### AI as an explanation layer

The LLM makes findings easier to understand and provides code-specific remediation suggestions.

### Source-code evidence

Important AI explanations use actual source-code context around the reported line.

### Multi-language consistency

Different scanners are converted into one common issue model so downstream components work consistently across languages.

### Local processing

The current AI implementation runs the LLM locally through Ollama rather than requiring a cloud LLM API.

### Graceful fallback

If the local LLM is unavailable, deterministic analysis and rule-based explanations remain available.

---

## 📌 What Makes the Project Different

The platform is not only a linting dashboard. It combines several stages into one workflow:

```text
Static Analysis
      +
Unified Issue Model
      +
Engineering Metrics
      +
Deterministic Risk Scoring
      +
Source-Code-Aware Local AI
      +
Historical Tracking
      +
Interactive Dashboard
```

This provides both **machine-detected evidence** and **human-readable explanations** in a single system.

---

## 🔮 Future Enhancements

Possible future extensions include:

- Additional programming languages
- More language-specific security scanners
- AI-assisted refactoring workflows
- Pull-request review integration
- CI/CD integration
- GitHub Actions integration
- Developer impact analysis
- More advanced historical analytics
- Automated remediation suggestions

Java and C/C++ analysis are already implemented and are therefore not listed as future language support.

---

## 🎓 Academic / Final-Year Project Relevance

This project demonstrates practical integration of:

- Full-stack web development
- REST API design
- Static code analysis
- Software security analysis
- Multi-language processing
- Data normalization
- Engineering metrics
- Deterministic scoring
- Local LLM integration
- Source-code-aware AI processing
- Historical data analysis
- Interactive data visualization

The architecture also demonstrates separation of concerns between **analysis**, **normalization**, **metrics**, **scoring**, **AI enrichment**, **storage**, and **presentation**.

---

## 📜 License

This project is intended for educational and academic use.
