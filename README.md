
# 🦾 LAZARUS // Autonomous Resurrection Engine

![Lazarus Concept](https://img.shields.io/badge/STATUS-OPERATIONAL-39ff14?style=for-the-badge&logo=cpu)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%2015%20%7C%20Gemini%202.0-black?style=for-the-badge)

> **"From Legacy to Cyberpunk in One Click."**

**Lazarus** is an AI-powered modernization agent that takes old, dusty repositories and "resurrects" them into modern, cloud-native architectures. It doesn't just fix bugs—it **re-architects** the entire stack, generates a new UI, and opens a Pull Request with the modernized code.

---

## ✨ Features

- **🤖 Autonomous AI Agent**: Powered by **Google Gemini 2.0 Flash**, it analyzes your legacy code and hallucinates a modern architecture.
- **🔒 E2B Sandboxed Execution**: All generated code is tested in a secure, cloud-based Linux sandbox (E2B) before it ever touches your repo.
- **🎨 Cyberpunk / Corporate UI**:
    - **"HAXOR" Mode**: Deep Void Black (`#0a0a0a`) & Neon Green (`#39ff14`) aesthetic.
    - **"CORP" Mode**: Clean, professional Light Mode for enterprise presentations.
    - **Toggle**: Seamless theme switching with persistent state.
- **⚡ Real-Time Neural Logs**: Watch the AI "think" with a Matrix-style streaming terminal (NDJSON).
- **👁️ Interactive Preview**: See the resurrected application *live* in an iframe before deploying.
- **GitOps Integration**: One-click "Create Migration Branch" to open a PR on your repo.

---

## 🛠️ Tech Stack

**The Brain (Backend):**
- **Language**: Python 3.10+
- **Core**: `http.server` (Zero-dependency core) + `requests`
- **AI**: Google Gemini API
- **Runtime**: E2B Code Interpreter (Sandboxing)

**The Face (Frontend):**
- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS v4 + Lucide Icons
- **Vibe**: Custom Cyberpunk Glassmorphism

---

## 🚀 Getting Started

### Prerequisites
1.  **Google Gemini API Key** (for the brains).
2.  **E2B API Key** (for the sandbox).
3.  **GitHub Token** (optional, for PR creation).

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/ArunN2005/lazarus-hackathon.git
    cd lazarus-hackathon
    ```

2.  **Setup Environment**
    Create a `.env` file in `backend/` (see `backend/.env.example`):
    ```properties
    GEMINI_API_KEY=your_key_here
    E2B_API_KEY=your_key_here
    GITHUB_TOKEN=your_token_here
    ```

3.  **Run the Engine**
    *Windows (PowerShell)*:
    ```powershell
    .\run.ps1
    ```
    *Linux/Mac*:
    ```bash
    chmod +x run.sh
    ./run.sh
    ```

4.  **Access the Dashboard**
    Open `http://localhost:3000` in your browser.

---

## 🕹️ Usage Guide

1.  **Enter Target**: Paste the GitHub URL of a legacy repository (e.g., an old Flask app).
2.  **Set Vibe**: Tell Lazarus what you want (e.g., *"Make it a modern SaaS with a dark mode"*).
3.  **Initialize**: Click **INITIALIZE PROTOCOL**.
4.  **Watch**: 
    -   The **Process Steps** will show the AI analyzing and planning.
    -   The **Preview Tab** will render the new UI in real-time.
5.  **Deploy**: If you like what you see, click **CREATE MIGRATION BRANCH** to push the code to GitHub.

---

## 📂 Project Structure

```
lazarus-hackathon/
├── backend/                 # The Brain (Python)
│   ├── lazarus_agent.py     # AI Logic & E2B Integration
│   ├── main.py              # API Server
│   └── ...
├── frontend/                # The Face (Next.js)
│   ├── app/page.tsx         # Main Dashboard UI
│   ├── app/globals.css      # Cyberpunk Styles
│   └── ...
└── run.ps1                  # One-click start script
```

---

## 🛡️ Security
- **No Secrets in History**: We use strictly ignored `.env` files.
- **Sandboxed**: AI code runs in E2B, not on your local machine.

---

*Verified for the Future.* 🦾
