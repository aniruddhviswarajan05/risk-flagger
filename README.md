# 🚀 SIGNAL Market AI — Unusual Market Activity Terminal

> **AI-Powered Real-Time Market Intelligence & Anomaly Scanner for NSE India & US Stock Markets**
> 
> Detects volume spikes, institutional order flow shifts, and trading anomalies, delivering plain-language AI insights powered by **Amazon Bedrock (Claude 3)**.

---

## 🌐 Live Production Access

- **Live Production URL**: [https://frontend-pi-lake-14.vercel.app](https://frontend-pi-lake-14.vercel.app) *(24/7 Global Uptime)*
- **Local Dev Server**: `http://127.0.0.1:3000`
- **Backend API**: `http://127.0.0.1:8000`

---

## 👥 Team & Work Division

### **Aniruddh Viswarajan** — *Team Lead & Lead Systems Architect* (Major Contribution)
- **Core Anomaly Engine**: Designed and implemented the Python volume spike anomaly rules engine ([`core/rules.py`](file:///c:/Users/aniru/Desktop/n/risk-flagger/core/rules.py)).
- **Amazon Bedrock AI Integration**: Built the generative AI prompt generator and Bedrock (Claude 3) explainer layer ([`core/bedrock_prompt.py`](file:///c:/Users/aniru/Desktop/n/risk-flagger/core/bedrock_prompt.py)).
- **3D Interactive Market Map**: Engineered the Three.js 3D Earth globe visualization with raycasted exchange node inspection modals.
- **Spatial Hand Gesture Engine**: Implemented Google MediaPipe Vision SDK (`@mediapipe/tasks-vision`) webcam hand tracking for contactless UI navigation.
- **Fallback Intelligence Engine**: Created deterministic AI market simulation logic for unlisted & pre-IPO equities (e.g. `ATHER`, `OLA`).
- **Cloud Deployment & Architecture**: Configured Vercel production deployment, API Gateway integration, and local backend server daemon.

### **Rishika Das** — *Frontend UI/UX Specialist*
- **Terminal UI Design**: Designed the dark-mode glassmorphism interface, tabbed navigation, and market overview dashboards.
- **Gold Particle FX Background**: Created the interactive HTML5 canvas particle background system with dynamic node constellation physics.
- **Micro-Animations & Styling**: Developed design tokens, custom CSS keyframe animations, toast notification system, and haptic feedback.

### **Mansi Nayak** — *Backend & Data Engineer*
- **Live Market Data Pipeline**: Integrated Yahoo Finance (`yfinance`) live quote & volume history fetching for NSE and US tickers.
- **Lambda Microservices**: Implemented `/analyze` and `/history` AWS Lambda function handlers ([`lambda_functions/`](file:///c:/Users/aniru/Desktop/n/risk-flagger/lambda_functions/)).
- **Historical Persistence**: Built local history JSON logging and DynamoDB table schema for flag event auditing.

### **S. Sushree** — *Cloud Infrastructure & Security*
- **Amazon Cognito Auth**: Configured user authentication workflows, JWT HMAC verification, and secure password hashing.
- **AWS SAM Infrastructure**: Built the SAM CloudFormation infrastructure template ([`infrastructure/template.yaml`](file:///c:/Users/aniru/Desktop/n/risk-flagger/infrastructure/template.yaml)) defining Lambda, API Gateway, and S3 buckets.
- **EventBridge Automation**: Set up 15-minute background cron triggers (`cron(0/15 * * * ? *)`) for automated watchlist scanning.

---

## ✨ Key Features

1. **Real-Time Volume Spike Detection**:
   - Calculates 30-day baseline average volumes and flags tickers exceeding **3.0× threshold**.
   - Supports both **NSE India (`.NS`)** and **US Equities (`AAPL`, `TSLA`, `NVDA`)**.

2. **Amazon Bedrock AI Explanations**:
   - Translates raw volume & price metrics into plain-language institutional insights without financial jargon.

3. **3D Interactive Market Map Globe**:
   - Three.js 3D Earth showing 8 major global financial hubs (Mumbai, New York, London, Tokyo, Singapore, Hong Kong, Frankfurt, Sydney).
   - Raycast node selection to inspect exchange volume and launch 1-click anomaly analysis.

4. **Spatial Hand Gesture Control Mode (`🖐️`)**:
   - Control the terminal using webcam hand gestures powered by **Google MediaPipe Tasks Vision**.
   - Supports pinch-to-click, open-palm menu, and horizontal swipe gestures.

5. **Dynamic Gold Particle Physics Background**:
   - Floating interactive particle field with mouse attraction physics and node connection lines.

---

## 🛠️ Project Structure

```
risk-flagger/
├── core/                       # Core Python logic (no AWS dependencies)
│   ├── rules.py                # Volume spike rule & fallback engine
│   └── bedrock_prompt.py       # Amazon Bedrock prompt builder
├── backend_server.py           # Local HTTP server emulating AWS API Gateway
├── local_history.json          # Persistent local flag history database
├── local_users.json            # Encrypted local user database
├── lambda_functions/
│   ├── analyze/                # POST /analyze — runs rule + Bedrock + saves flag
│   ├── history/                # GET /history — retrieves past flags
│   └── scheduled_check/        # Background EventBridge cron scanner
├── infrastructure/
│   ├── template.yaml           # SAM template: Lambda + API Gateway + Cognito
│   └── watchlist.json          # Predefined watchlist tickers
├── frontend/
│   ├── index.html              # Main terminal application UI
│   └── vercel.json             # Vercel deployment configuration
└── requirements.txt            # Python dependencies
```

---

## 💻 Local Quickstart

### Prerequisites
- Python 3.11+
- Node.js & npm

### 1. Start Backend Server
```bash
python backend_server.py 8000
```

### 2. Start Frontend Server
```bash
python -m http.server 3000 --directory frontend
```

Open `http://127.0.0.1:3000` in your browser.

---

## ☁️ AWS Serverless Deployment (SAM)

To deploy the backend stack directly to your AWS account:

```bash
cd infrastructure
sam build --template-file template.yaml
sam deploy --guided --template-file template.yaml
```

**AWS Resources Provisioned**:
- **AWS Lambda**: `AnalyzeFunction`, `HistoryFunction`, `ScheduledCheckFunction`
- **Amazon API Gateway**: HTTP REST API with CORS support
- **Amazon Bedrock**: Anthropic Claude 3 Sonnet model invocation
- **Amazon Cognito**: User Pool & User Pool Client
- **Amazon EventBridge**: 15-minute cron market scanner

---

## 📜 License
Built for Hackathon Submission. Open Source & Apache 2.0 Licensed.
