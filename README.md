# 🤖 AI Instagram Story Bot

A fully automated Python bot that posts one AI-generated Instagram image daily, driven by a 365-day Time Traveler story stored in an Excel file.

---

## ✨ Features

- 📖 Reads daily story data from `story.xlsx`
- 🎨 Generates images via **Google Gemini Imagen 3**
- ✍️ Writes captions via **Google Gemini Flash**
- ☁️ Hosts images on **Cloudinary** (free tier)
- 📸 Posts to **Instagram** via the Graph API
- ⏰ Runs automatically at **00:05 UTC** every day
- 🔁 Retries up to 3 times on any failure
- 📝 Full structured logging to `logs/app.log`

---

## 📁 Project Structure

```
project-root/
├── app/
│   ├── __init__.py
│   ├── config.py           # Centralised config & logging
│   ├── bot.py              # Pipeline orchestrator
│   ├── excel_reader.py     # Read & update story.xlsx
│   ├── image_generator.py  # Gemini Imagen 3 image generation
│   ├── caption_generator.py# Gemini Flash caption generation
│   ├── image_uploader.py   # Cloudinary upload
│   ├── instagram_poster.py # Instagram Graph API posting
│   └── scheduler.py        # APScheduler cron job
├── data/
│   └── story.xlsx          # 365-day story data
├── generated_images/       # Locally saved generated images
├── logs/
│   └── app.log
├── generate_excel.py       # One-time script to seed story.xlsx
├── main.py                 # Entrypoint
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

Copy `.env` and fill in your credentials:

```bash
cp .env .env.local
```

```env
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

This creates `data/story.xlsx` with 365 pre-written days. Edit the rows with your own prompts as desired.

### 4. Run immediately (test)

```bash
python main.py --now
```

### 5. Run with daily scheduler

```bash
python main.py
```

---

## 🔑 Getting API Credentials

### Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy to `GOOGLE_API_KEY`

### Instagram Graph API
1. Create a [Meta Developer App](https://developers.facebook.com/)
2. Add **Instagram Graph API** product
3. Connect your **Instagram Business** or **Creator** account
4. Generate a **long-lived access token** (60-day expiry)
5. Copy your **Instagram Business Account ID** from the API Explorer

> ⚠️ Long-lived tokens expire after 60 days. Use [token refresh logic](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived) or a service like [token refresher](https://developers.facebook.com/tools/accesstoken/) to keep it alive.

### Cloudinary (free image hosting)
1. Sign up at [cloudinary.com](https://cloudinary.com) (free tier: 25 credits/month)
2. Go to **Dashboard** → copy Cloud Name, API Key, API Secret

---

## ☁️ Deploy on Render

### 1. Push to GitHub

```bash
git add .
git commit -m "initial commit"
git push origin main
```

### 2. Create a Render Web Service

1. Go to [render.com](https://render.com) and click **New → Web Service**
2. Connect your GitHub repo
3. Use these settings:

| Setting | Value |
|---|---|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |
| **Instance Type** | Free (or Starter for reliability) |

### 3. Add environment variables on Render

Go to **Environment** tab and add all variables from your `.env` file.

### 4. Deploy

Click **Deploy**. Render will keep the service alive 24/7, and APScheduler will fire the bot at 00:05 UTC daily.

> 💡 **Tip:** On Render's free tier, the service spins down after 15 minutes of inactivity. Use the **Starter ($7/mo)** plan to ensure the scheduler never misses a job.

---

## 📋 Excel File Format

| Column | Description |
|---|---|
| Day | 1–365 |
| Title | Episode title |
| Story Phase | Arc name |
| Image Prompt | Prompt sent to Gemini Imagen |
| Caption Context | Context for caption generation |
| Next Day Teaser | Teaser for next episode |
| Style | Art style (e.g., "cinematic realism") |
| Mood | Mood (e.g., "mysterious and tense") |
| Hashtags | Space-separated hashtags |
| Status | `Pending` → `Posted` (or `Failed`) |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `GOOGLE_API_KEY not set` | Fill in `.env` and restart |
| `Instagram API error 190` | Access token expired — refresh it |
| `No pending rows found` | All rows are Posted — reset Status column |
| Render service sleeps | Upgrade to Starter plan |
| Image not generated | Check Gemini API quota / billing |

---

## 📜 License

MIT
