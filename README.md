# 🎬 The Director Backend

AI-powered backend engine for transforming long-form gameplay footage into short-form, high-retention clip opportunities.

The Director Backend processes uploaded videos, splits them into optimized chunks, analyzes footage with AI, ranks the best moments, and generates editor-ready outputs such as DaVinci Resolve timelines and markdown editing guides.

🔗 **Frontend Repository:** https://github.com/mayurpatel78645/the-director-ui

---

## 🚀 Features

- 📤 Large video upload support
- ⚙️ Background job processing
- ✂️ Automatic chunking with FFmpeg
- 🧠 AI-powered clip analysis
- 📊 Retention-based clip ranking
- 🎞️ DaVinci Resolve `.edl` timeline export
- 📝 Markdown editing guide generation
- 🔄 Frontend polling job status API
- 🧩 Structured JSON outputs using schemas

---

## 🏗️ Engineering Highlights

- **Asynchronous Processing:** Heavy video processing runs in the background while the frontend tracks progress through job polling.
- **Chunk-Based Pipeline:** Long videos are split into smaller segments for faster and more efficient AI analysis.
- **Parallel AI Analysis:** Multiple chunks can be processed concurrently to reduce total runtime.
- **Structured AI Responses:** Uses schema validation to keep AI outputs consistent and frontend-friendly.
- **Editor Workflow Integration:** Generates outputs that fit directly into post-production workflows.

---

## 🛠 Tech Stack

- **Python**
- **FastAPI**
- **Uvicorn**
- **FFmpeg**
- **Google Gemini API**
- **Pydantic**
- **Concurrent Futures**

---

## 🧠 How It Works

### 1. Upload Video
The client uploads a long-form video to the API.

### 2. Create Job
The backend immediately returns a job ID and starts processing asynchronously.

### 3. Video Chunking
FFmpeg compresses and splits the video into smaller chunks.

### 4. AI Analysis
Each chunk is analyzed to identify strong short-form moments.

### 5. Ranking & Compilation
The best clips are ranked and combined into the final result.

### 6. Export Outputs
Generated outputs can include:

- `timeline.edl`
- `Editing_Guide.md`
- structured JSON response

---

## 📂 Project Structure

```text
the-director-backend/
│── server.py
│── ai_analysis.py
│── video_processor.py
│── generate_workspace.py
│── test_api.py
│── requirements.txt
│── .gitignore
│── README.md
````

---

## ⚡ Installation

### 1. Clone Repository

```bash
git clone https://github.com/mayurpatel78645/the-director-backend.git
cd the-director-backend
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Mac/Linux

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Environment Variables

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_api_key_here
```

### 5. Run the Server

```bash
python server.py
```

Server runs on:

```text
http://localhost:8000
```

---

## 📡 API Endpoints

### POST `/api/analyze`

Upload a video and start processing.

**Response**

```json
{
  "status": "success",
  "job_id": "uuid"
}
```

---

### GET `/api/status/{job_id}`

Check processing status.

**Possible States**

* `PROCESSING`
* `COMPLETE`
* `ERROR`

---

## 📌 Example Use Cases

* Gaming creators turning VODs into Shorts
* Editors speeding up clip discovery
* Agencies processing creator content at scale
* Highlight extraction from streams

---

## 🔮 Roadmap

* User authentication
* Cloud storage
* WebSocket progress updates
* Project dashboard
* Direct publishing to Shorts/TikTok
* SaaS subscriptions

---

## 👨‍💻 Author

**Mayur Patel**

GitHub: [https://github.com/mayurpatel78645](https://github.com/mayurpatel78645)

---

## 📄 License

Copyright (c) 2026 Mayur Patel. All rights reserved.

This project is proprietary. Unauthorized copying, modification, or distribution is strictly prohibited.

```
```
