# 🤖 AI Instagram Story Bot

A fully automated Python bot that posts one AI-generated Instagram image daily, driven by a 365-day Time Traveler story stored in an Excel file.

---

## ✨ Features

- 📖 Reads daily story data from `story.xlsx`
- 🎨 Generates images via **Hugging Face** (Stable Diffusion XL) — free tier
- ✍️ Writes captions via **Google Gemini Flash** — free tier
- ☁️ Hosts images on **Cloudinary** (free tier)
- 📸 Posts to **Instagram** via the Graph API
- ⏰ Runs automatically at **12:05 AM IST** every day via GitHub Actions
- 🔁 Retries up to 5 times on any failure
- 💾 Saves `pending_publish.json` if Instagram posting fails — retry separately without regenerating the image
- 📝 Full structured logging to `logs/app.log`

---

## 📁 Project Structure

```
project-root/
├── app/
│   ├── __init__.py
│   ├── config.py             # Centralised config & logging
│   ├── bot.py                # Pipeline orchestrator
│   ├── excel_reader.py       # Read & update story.xlsx
│   ├── image_generator.py    # Hugging Face SDXL image generation
│   ├── caption_generator.py  # Gemini Flash caption generation
│   ├── image_uploader.py     # Cloudinary upload
│   ├── instagram_poster.py   # Instagram Graph API posting
│   ├── pending_store.py      # Save/load/clear pending_publish.json
│   └── scheduler.py          # APScheduler cron job
├── data/
│   └── story.xlsx            # 365-day story data
├── generated_images/         # Locally saved generated images
├── logs/
│   └── app.log
├── .github/
│   └── workflows/
│       ├── daily_post.yml      # Runs daily at 12:05 AM IST
│       └── retry_publish.yml   # Manual retry for failed Instagram posts
├── generate_excel.py         # One-time script to seed story.xlsx
├── main.py                   # Entrypoint
├── requirements.txt
└── .env
```

---

## 🚀 Local Setup

### 1. Clone & install

```bash
git clone https://github.com/yourname/instagram-bot.git
cd instagram-bot
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Fill in all values in .env
```

```env
HUGGINGFACE_API_KEY=your_huggingface_api_key
GOOGLE_API_KEY=your_google_gemini_api_key
INSTAGRAM_ACCESS_TOKEN=your_instagram_long_lived_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_ig_business_account_id
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

### 3. Generate the Excel story file

```bash
python generate_excel.py
```

Creates `data/story.xlsx` with 365 pre-written days. Edit rows with your own prompts as desired.

### 4. Run immediately (test)

```bash
python main.py --now
```

### 5. Retry a failed Instagram publish only

```bash
python main.py --retry
```

### 6. Run with daily scheduler

```bash
python main.py
```

---

## 🔑 Getting API Credentials

### Hugging Face API Key (Image Generation)
1. Sign up at [huggingface.co](https://huggingface.co)
2. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. Click **New token** → select type **"Fine-grained"**
4. Enable permission: **"Make calls to the serverless Inference API"**
5. Copy to `HUGGINGFACE_API_KEY`

### Google Gemini API Key (Caption Generation)
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy to `GOOGLE_API_KEY`

### Instagram Graph API
1. Create a [Meta Developer App](https://developers.facebook.com/)
2. Add **Instagram Graph API** product
3. Set app to **Live Mode** (not Development)
4. Add and approve the `instagram_content_publish` permission
5. Connect your **Instagram Business** or **Creator** account
6. Generate a **long-lived access token** (valid for 60 days)
7. Copy your **Instagram Business Account ID**

> ⚠️ Long-lived tokens expire after **60 days**. Regenerate and update your GitHub secret before expiry.

### Cloudinary (Image Hosting)
1. Sign up at [cloudinary.com](https://cloudinary.com) — free tier: 25GB storage
2. Go to **Dashboard** → copy Cloud Name, API Key, API Secret
3. Copy all three values to your `.env`

---

## ☁️ Deploy on GitHub Actions (Free)

### 1. Push to GitHub

```bash
git add .
git commit -m "initial commit"
git push origin main
```

> Make sure `data/story.xlsx` is committed — it must be in the repo.

### 2. Add your secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Create one secret named **`ENV`** with the full contents of your `.env` file:

```
HUGGINGFACE_API_KEY=your_key
GOOGLE_API_KEY=your_key
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_id
CLOUDINARY_CLOUD_NAME=your_name
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
```

### 3. That's it

The bot runs automatically every day at **12:05 AM IST** (18:35 UTC).

To test manually: **Actions → Daily Instagram Post → Run workflow**

---

## 🔁 Retry Failed Instagram Posts

If the image was generated and uploaded to Cloudinary successfully but Instagram posting failed, the bot saves a `pending_publish.json` file to the repo with the Cloudinary URL and caption.

To retry the Instagram publish **without regenerating the image**:

1. Fix whatever caused the Instagram failure (expired token, permissions, etc.)
2. Go to **Actions → Retry Instagram Publish → Run workflow**

The retry workflow will:
- Read `pending_publish.json`
- Post to Instagram only
- Update `story.xlsx` to `Posted`
- Delete `pending_publish.json` from the repo

---

## 📋 Excel File Format

| Column | Description |
|---|---|
| Day | 1–365 |
| Title | Episode title |
| Story Phase | Arc name |
| Image Prompt | Prompt sent to Stable Diffusion XL |
| Caption Context | Context for caption generation |
| Next Day Teaser | Teaser shown at end of caption |
| Style | Art style (e.g., `cinematic realism`) |
| Mood | Mood (e.g., `mysterious and tense`) |
| Hashtags | Space-separated hashtags |
| Status | `Pending` → `Posted` or `Failed` |

---

## 🛠️ Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `HUGGINGFACE_API_KEY not set` | Missing env var | Add to `.env` or GitHub secret |
| `403 insufficient permissions` | HF token type wrong | Regenerate with "Inference API" permission enabled |
| `Instagram API error 200: API access blocked` | App in Dev mode or missing permission | Switch app to Live Mode, approve `instagram_content_publish` |
| `Instagram API error 190` | Access token expired | Regenerate token, update GitHub secret |
| `No pending rows found` | All rows are Posted | Reset Status column in Excel |
| GitHub workflow disabled | Repo inactive for 60 days | Re-enable under Actions tab |

---

## ⏰ Cron Schedule

| Workflow | Schedule | Timezone |
|---|---|---|
| Daily Instagram Post | `35 18 * * *` | 12:05 AM IST (18:35 UTC) |
| Retry Instagram Publish | Manual only | — |

To change the posting time, edit `cron: '35 18 * * *'` in `.github/workflows/daily_post.yml`.
Use [crontab.guru](https://crontab.guru) to calculate your desired UTC time.

---

## 📜 License

MIT
