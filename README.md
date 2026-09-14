# Investigation Intelligence Pipeline 🔍⚖️

An end-to-end forensic analysis engine and decision-support system for multi-witness, multi-suspect investigations. This pipeline ingests unstructured testimony, extracts structured chronological claims using LLMs, assesses credibility via empirical psychological frameworks, and resolves contradictions using graph theory and information theory.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Analytical Modules](#-analytical-modules)
  - [1. Forensic NLP Extraction](#1-forensic-nlp-extraction)
  - [2. Criteria-Based Content Analysis (CBCA)](#2-criteria-based-content-analysis-cbca)
  - [3. Reality Monitoring (RM)](#3-reality-monitoring-rm)
  - [4. Corroboration Network & PageRank](#4-corroboration-network--pagerank)
  - [5. Conflict Graph & Maximum Independent Set (MIS)](#5-conflict-graph--maximum-independent-set-mis)
  - [6. Temporal Precedence & Topological Sort](#6-temporal-precedence--topological-sort)
  - [7. Contested Fact Shannon Entropy](#7-contested-fact-shannon-entropy)
- [User Interfaces & Visualizations](#-user-interfaces--visualizations)
- [Repository Structure](#-repository-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
- [Execution & Usage](#-execution--usage)
  - [Option A: Web Application Server (Interactive GUI)](#option-a-web-application-server-interactive-gui)
  - [Option B: Main Pipeline (CLI with Gemini)](#option-b-main-pipeline-cli-with-gemini)
  - [Option C: Groq Fast Pipeline](#option-c-groq-fast-pipeline)
  - [Option D: Offline Mock Pipeline (Zero API Keys)](#option-d-offline-mock-pipeline-zero-api-keys)
  - [Option E: Standalone Algorithms](#option-e-standalone-algorithms)
- [Data Formats](#-data-formats)
- [Security & Git Hygiene](#-security--git-hygiene)
- [Academic References](#-academic-references)
- [License](#-license)

---

## 🔍 Overview

Criminal and corporate investigations frequently involve conflicting statements, unreliable witnesses, missing timeline pieces, and cognitive biases. 

The **Investigation Intelligence Pipeline** solves this by converting raw natural language statements into a mathematically rigorous, auditable investigation dossier. It evaluates testimony across two gold-standard forensic psychology models (CBCA and RM), models cross-statement corroboration and conflict as formal graphs, computes consistent truth subsets via Maximum Independent Set, and visualizes the results on an interactive chronological timeline and comprehensive forensic report.

---

## ✨ Key Features

- **Multi-Witness Forensic Extraction**: Parses free-form text into atomic chronological events with speaker attribution, confidence scores, and time intervals.
- **19-Criterion CBCA Scoring**: Quantifies criteria such as logical structure, spontaneous corrections, unusual details, and self-deprecation.
- **8-Criterion Reality Monitoring**: Distinguishes genuine perceptual and spatial memories from fabricated or imagined accounts.
- **Corroboration PageRank**: Weighs mutual witness corroboration to highlight central, highly-supported event nodes.
- **Greedy Conflict MIS**: Identifies mutually exclusive contradictions and computes the largest mathematically consistent subset of events.
- **Topological Precedence DAG**: Establishes causal and chronological sequencing while flagging impossible time paradoxes.
- **Contested Fact Entropy**: Calculates Shannon entropy ($H(X)$) to measure uncertainty across contested claims.
- **Zero-Dependency Core**: All graph algorithms, psychological scoring engines, and the web GUI run using Python's standard library.
- **Dual LLM Provider Support**: Native integration with Google Gemini (`google-genai`) and Groq (`llama-3.3-70b-versatile`).

---

## 🏛 System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Testimony Ingestion"]
        A[Raw Natural Language Statements\nJSON / Web Form] --> B[Forensic NLP Engine\nGemini / Groq]
    end

    subgraph Extraction ["2. Structured Extraction"]
        B --> C1[Atomic Timeline Events\nwith Start/End Times]
        B --> C2[CBCA & RM\nPsychological Annotations]
        B --> C3[Corroboration Pairs\nand Conflict Pairs]
        B --> C4[Contested Facts &\nPrecedence Relations]
    end

    subgraph Analysis ["3. Multi-Model Algorithmic Analysis"]
        C2 --> D1[CBCA Engine\n19 Empirical Criteria]
        C2 --> D2[Reality Monitoring Engine\n8 Perceptual Criteria]
        C3 --> D3[Corroboration Graph\nWeighted PageRank]
        C3 --> D4[Conflict Graph\nGreedy MIS Approximation]
        C4 --> D5[Temporal DAG\nTopological Sort]
        C4 --> D6[Contested Facts\nShannon Entropy H(X)]
    end

    subgraph Synthesis ["4. Consolidation & Output"]
        D1 & D2 & D3 & D4 & D5 & D6 --> E[Master Timeline & Case Result\ncase_result.json]
        E --> F1[Interactive SVG Timeline\ntimeline.html]
        E --> F2[Forensic Investigation Report\nreport.html]
        E --> F3[Web GUI\nlocalhost:8500]
    end
```

---

## 🧠 Analytical Modules

### 1. Forensic NLP Extraction
- Implemented in `nlp_engine.py` (Google Gemini) and `pipeline.py` (Groq / LLaMA).
- Parses free-form transcripts into normalized events, speaker metadata, temporal ranges (`time_start`, `time_end`), and pairwise relations.

### 2. Criteria-Based Content Analysis (CBCA)
- Located in `cbca/`.
- Evaluates 19 standardized criteria grouped across:
  - **General Characteristics**: Logical structure, unstructured production, quantity of details.
  - **Specific Contents**: Contextual embedding, descriptions of interactions, reproduction of conversation, unexpected complications.
  - **Peculiarities of Content**: Unusual details, superfluous details, accurately reported details misunderstood, external associations, accounts of subjective mental state, attribution of perpetrator's state of mind.
  - **Motivation-Related Contents**: Spontaneous corrections, admitting lack of memory, raising doubts about own testimony, self-deprecation, pardoning the perpetrator.
  - **Offense-Specific Elements**: Details characteristic of the offense.

### 3. Reality Monitoring (RM)
- Located in `rm/`.
- Evaluates 8 criteria based on cognitive memory frameworks:
  - Perceptual information (visual, auditory, tactile).
  - Spatial information (locations, positions, distances).
  - Temporal information (explicit sequencing, timestamps).
  - Affect / Emotion (internal emotional reactions).
  - Cognitive operations (explicit reasoning or deductions during the event).
  - Plausibility, realism, and reconstructive consistency.

### 4. Corroboration Network & PageRank
- Located in `pagerank/`.
- Constructs a directed, weighted graph where nodes represent claimed events and edges represent mutual witness corroboration.
- Power iteration algorithm computes eigenvalue centrality to identify the most robustly supported facts.

### 5. Conflict Graph & Maximum Independent Set (MIS)
- Located in `conflict_graph_mis/`.
- Nodes represent claimed events; edges represent mutual logical, spatial, or temporal contradictions.
- A greedy heuristic algorithm computes the **Maximum Independent Set (MIS)** — the largest set of events that can simultaneously be true without internal contradiction.

### 6. Temporal Precedence & Topological Sort
- Located in `topological_sort/`.
- Builds a Directed Acyclic Graph (DAG) of cause-and-effect and temporal constraints.
- Identifies circular causal paradoxes and returns the strictly ordered incident progression.

### 7. Contested Fact Shannon Entropy
- Located in `entropy/`.
- Evaluates contested claims where witnesses disagree:
  $$H(X) = - \sum_{i=1}^n P(x_i) \log_2 P(x_i)$$
- Yields entropy in bits and normalized entropy ($0.0 \le \bar{H} \le 1.0$), quantifying investigation ambiguity.

---

## 🖥 User Interfaces & Visualizations

| Interface | File | Description |
|-----------|------|-------------|
| **Interactive Web Server** | `server.py` | Local web application (`http://localhost:8500`) with live case editor, speaker management, pipeline execution, and case library. |
| **Interactive Timeline** | `output/timeline.html` | SVG-based interactive timeline with zoom/pan, speaker-colored event markers, red conflict arcs, green corroboration curves, and metadata cards. |
| **Investigation Dossier** | `output/report.html` | Executive dossier featuring credibility scorecards, MIS consensus timeline, entropy breakdown, and unresolved contradiction logs. |

---

## 📂 Repository Structure

```text
Investigation/
├── .env.example              # Template for API keys
├── .gitignore                # Git ignore rules for caches, venvs, and secrets
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
│
├── main.py                   # Main CLI pipeline orchestrator (Gemini)
├── pipeline.py               # Alternative orchestrator (Groq LLaMA)
├── mock_pipeline.py          # Zero-API offline demo pipeline
├── server.py                 # Interactive web server & GUI
├── nlp_engine.py             # LLM prompt construction & JSON extraction
├── timeline_generator.py     # Generates interactive SVG timeline.html
├── report_generator.py       # Generates comprehensive report.html
│
├── case_input.json           # Active case input file for web/server pipeline
├── statements_input.json     # Sample multi-witness statement input
│
├── cases/                    # Stored investigation case studies
│   ├── CASE-2026-0824.json   # Multi-witness warehouse theft scenario
│   └── CASE-2026-0912.json   # Server room data breach scenario
│
├── cbca/                     # Criteria-Based Content Analysis module
│   ├── cbca.py               # Analysis logic & scoring calculation
│   └── criteria.py           # 19 CBCA criteria definitions & catalog
│
├── rm/                       # Reality Monitoring module
│   ├── rm.py                 # Scoring & classification logic
│   └── criteria.py           # 8 RM criteria definitions & weights
│
├── conflict_graph_mis/       # Conflict graph & Greedy MIS algorithm
│   └── algorithm.py
│
├── pagerank/                 # Corroboration network PageRank algorithm
│   └── algorithm.py
│
├── topological_sort/         # Temporal precedence DAG sorter
│   └── algorithm.py
│
├── entropy/                  # Shannon entropy calculation module
│   └── algorithm.py
│
└── output/                   # Generated pipeline artifacts (.gitkeep preserved)
    ├── .gitkeep
    ├── case_result.json      # Complete consolidated analysis JSON
    ├── timeline.html         # Interactive timeline visualization
    └── report.html           # Forensic investigation report
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** (Python 3.10+ recommended)
- A **Google Gemini API Key** (optional: Groq API key)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/investigation-pipeline.git
   cd investigation-pipeline
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Setup

Copy `.env.example` to create your local `.env`:

```bash
cp .env.example .env      # macOS/Linux
copy .env.example .env    # Windows
```

Edit `.env` with your API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GROQ_API_KEY=your_actual_groq_api_key_here  # Optional
```

---

## 💻 Execution & Usage

### Option A: Web Application Server (Interactive GUI)

Launch the built-in investigation server:
```bash
python server.py
```
Open **`http://localhost:8500`** in your browser to:
- Enter and manage witnesses, statements, and incident times.
- Run the full pipeline with live status updates.
- Switch between cases stored in `cases/`.
- Launch the interactive timeline viewer and forensic report.

*(To specify a custom port: `python server.py 9000`)*

---

### Option B: Main Pipeline (CLI with Gemini)

Run against the default `statements_input.json`:
```bash
python main.py
```

Run with custom statements:
```bash
python main.py cases/CASE-2026-0824.json
```

Outputs will be saved in the `output/` directory:
- `output/case_result.json`
- `output/timeline.html`

---

### Option C: Groq Fast Pipeline

Run the pipeline using Groq LLaMA 3.3 70B:
```bash
python pipeline.py
```

Outputs will be generated in `output/` (including `output/report.html`).

---

### Option D: Offline Mock Pipeline (Zero API Keys)

Need to test the UI or algorithms without spending API tokens? Run the deterministic mock pipeline:
```bash
python mock_pipeline.py
```
Generates a full synthetic investigation dossier and timeline in seconds.

---

### Option E: Standalone Algorithms

Every algorithm module can be executed in isolation with standard JSON inputs:

```bash
# Criteria-Based Content Analysis (CBCA)
python cbca/cbca.py

# Reality Monitoring (RM)
python rm/rm.py

# Corroboration PageRank
python pagerank/algorithm.py

# Conflict Graph Greedy MIS
python conflict_graph_mis/algorithm.py

# Shannon Entropy
python entropy/algorithm.py

# Temporal Topological Sort
python topological_sort/algorithm.py
```

---

## 📋 Data Formats

### Case Input (`case_input.json`)
```json
{
  "case_id": "CASE-2026-0824",
  "incident": "Break-in and hardware theft at Apex Distribution Warehouse.",
  "statements": [
    {
      "statement_id": "S1",
      "speaker_name": "Marcus Vance",
      "speaker_role": "Night Security Guard",
      "statement_text": "I was conducting my round at 23:15 when I saw a blue van..."
    },
    {
      "statement_id": "S2",
      "speaker_name": "Elena Rostova",
      "speaker_role": "Facilities Lead",
      "statement_text": "At 23:10 I heard the loading bay alarm chirp..."
    }
  ]
}
```

---

## 🔒 Security & Git Hygiene

- **`.env` is Git-Ignored**: API credentials and secrets must **never** be checked into version control.
- **Generated Outputs**: The `output/` folder is tracked via `.gitkeep`, while actual generated HTML reports and JSON runs are ignored.
- **Data Privacy**: Ensure witness statements and real-world case files conform to applicable local data privacy and handling regulations.

---

## 📚 Academic References

- **CBCA (Criteria-Based Content Analysis)**:
  - Steller, M., & Köhnken, G. (1989). *Criteria-based statement analysis*. In D. C. Raskin (Ed.), Psychological methods in criminal investigation and evidence.
  - Vrij, A. (2005). *Criteria-Based Content Analysis: A qualitative review of the first 37 studies*. Psychology, Public Policy, and Law, 11(1), 3–41.
- **RM (Reality Monitoring)**:
  - Johnson, M. K., & Raye, C. L. (1981). *Reality monitoring*. Psychological Review, 88(1), 67–85.
  - Sporer, S. L. (2004). *Reality monitoring and the detection of deception*. In P. A. Granhag & L. A. Strömwall (Eds.), The detection of deception in forensic contexts.
- **Graph & Information Theory**:
  - Page, L., Brin, S., Motwani, R., & Winograd, T. (1999). *The PageRank Citation Ranking: Bringing Order to the Web*. Stanford InfoLab.
  - Shannon, C. E. (1948). *A Mathematical Theory of Communication*. Bell System Technical Journal, 27(3), 379–423.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
