# Deploy MCQ Answer Sheet Checker (Web App)

---

## Make it live (step-by-step)

### 1. Put your project on GitHub

- Create a new repo at [github.com/new](https://github.com/new) (e.g. `mcq-answer-checker`).
- In your project folder (`paras answer checking system`), run:

  ```powershell
  git init
  git add .
  git commit -m "Initial commit - MCQ checker web app"
  git branch -M main
  git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
  git push -u origin main
  ```

- **Important:** Your repo must include `cnn_model.h5` (in the project root, same folder as `main.py`). If the file is very large (>100 MB), GitHub may reject it; then use [Git LFS](https://git-lfs.com/) or host the model elsewhere and add a build step on Render to fetch it.

### 2. Deploy on Render (one URL for app + API)

1. Go to **[render.com](https://render.com)** and sign up (free with GitHub).
2. Click **New** → **Web Service**.
3. Connect your **GitHub** account and select the repo you just pushed.
4. Use these settings:

   | Setting | Value |
   |--------|--------|
   | **Name** | `mcq-answer-checker` (or any name) |
   | **Region** | Choose closest to you |
   | **Root Directory** | Leave **empty** |
   | **Runtime** | Python 3 |
   | **Build Command** | `cd webapp && pip install -r requirements.txt` |
   | **Start Command** | `cd webapp && gunicorn app:app` |

5. Under **Advanced**, add an environment variable (optional):  
   `PYTHON_VERSION` = `3.11`
6. Click **Create Web Service**. Render will build and deploy (first time can take several minutes because of TensorFlow).
7. When it’s done, open the URL Render shows (e.g. `https://mcq-answer-checker.onrender.com`). That’s your **live app** — same UI as local: upload model answer → generate metadata → upload student sheets → grade.

### 3. Optional: custom domain

In the Render dashboard for your service: **Settings** → **Custom Domain** → add your domain and follow the DNS instructions.

---

## Quick start (run locally)

1. **Model file**: Ensure `cnn_model.h5` exists in the **project root** (parent of `webapp/`), or copy it into `webapp/`.
2. **From project root**:
   ```bash
   cd webapp
   pip install -r requirements.txt
   python app.py
   ```
3. Open **http://localhost:5000** — upload model answer → Generate metadata → upload student sheets → Grade.

---

## Deploy backend (Render recommended)

1. **Push your repo to GitHub** (include `cnn_model.h5` in the repo, or add it in Render’s build step).
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect the repo. Set:
   - **Root Directory**: leave **empty** (repo root) so `cnn_model.h5` at root and `webapp/` are both available.
   - **Build Command**: `cd webapp && pip install -r requirements.txt`
   - **Start Command**: `cd webapp && gunicorn app:app`
   - **Python**: 3.11
4. Deploy. Note the URL, e.g. `https://mcq-answer-checker-api.onrender.com`.

**If you set Root Directory to `webapp`** (so build/start run from `webapp/`):
- Put `cnn_model.h5` inside the `webapp/` folder (or add a build step that copies it there).
- Build: `pip install -r requirements.txt`, Start: `gunicorn app:app`.

---

## Deploy frontend (Netlify) — optional

If you host the **frontend** on Netlify and the **backend** on Render:

1. **Backend URL**: Deploy the backend first and copy its URL (e.g. `https://mcq-answer-checker-api.onrender.com`).
2. **Point frontend to it**: In `webapp/static/index.html`, set the API base URL before the script:
   ```html
   <script>window.API_BASE = 'https://mcq-answer-checker-api.onrender.com';</script>
   ```
   Then in the script, use: `const API_BASE = window.API_BASE || window.location.origin;`
3. In **Netlify**: New site from Git → choose repo. Set:
   - **Base directory**: `webapp/static`
   - **Build command**: leave empty (static site).
   - **Publish directory**: `webapp/static` (or `.` if base is already `webapp/static`).
4. Deploy. Your site will call the Render backend.

**Easier option**: Deploy only the backend on Render. The Flask app serves the frontend at `/`, so one URL gives you both UI and API (no Netlify needed).

---

## Deploy backend on Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
2. Set **Root Directory** to `webapp` (or leave empty and set start to `cd webapp && gunicorn app:app`).
3. Add `cnn_model.h5` in `webapp/` if root is `webapp`.
4. Set **Start Command**: `gunicorn app:app` (if root is `webapp`) or `cd webapp && gunicorn app:app` (if root is repo).
5. Deploy and use the generated URL.

---

## API summary

| Endpoint            | Method | Description |
|---------------------|--------|-------------|
| `/`                 | GET    | Serves the web UI. |
| `/api/health`       | GET    | Returns `{"status":"ok","model_loaded":true/false}`. |
| `/api/metadata`     | POST   | Form: `model_answer` = image file. Returns metadata JSON. |
| `/api/grade`        | POST   | Form: `metadata` = JSON string, `sheets` = one or more image files. Returns JSON. Add `?format=csv` to download CSV. |

All responses are JSON unless `format=csv`. Errors return `{"error": "message"}` with 4xx/5xx status.
