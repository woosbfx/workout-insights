# 🏋️ Brass Facts Workout Tracker

An interactive Streamlit dashboard for analyzing your workout trends using data from the Strong app. Automatically tracks your total volume, reps, and RPE, and uses OpenAI to generate personalized performance insights.

---

## 🔧 Features

- 📊 Interactive dashboard for weekly/monthly trends
- 📈 Drill down by exercise or body part
- 🧠 One-click performance analysis using OpenAI
- 📥 Upload your Strong app `.csv` export
- 🐋 Docker + `docker-compose` support for dev mode
- 🧪 Fine-tuning prep script to collect training data

---

## 📁 Project Structure

```
.
├── app.py                    # Main Streamlit app
├── lambda.py                # CSV transformation and classification script
├── env/
│   ├── strong.csv           # Raw data export from Strong
│   └── analysis_output.csv  # Transformed, aggregated data
├── docker-compose.yml       # Base Docker config
├── docker-compose.dev.yml   # Development config (volumes, hot reload)
├── requirements.txt         # Python dependencies
└── .env                     # OpenAI API key and other secrets
```

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/brass-facts.git
cd brass-facts
```

### 2. Set up your `.env` file

```env
OPENAI_API_KEY=your-openai-key
```

### 3. Run the app with Docker (dev mode)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The app will be available at: [http://localhost:8501](http://localhost:8501)

---

## 🧠 OpenAI Insights

To generate performance feedback:
1. Navigate to **Workout Trends**
2. Filter down to any single exercise or body part
3. Click **“🧠 Get Performance Insights”**
4. The app will send the chart view + full context to OpenAI and return personalized analysis

---

## 🧪 Fine-Tuning Prep (Optional)

To prepare training data for OpenAI fine-tuning:

```bash
python fine_tune.py
```

This will output `.jsonl` files containing example prompts and ideal responses.

---

## 📦 Dependencies

Install dependencies (if running locally):

```bash
pip install -r requirements.txt
```

Key libraries:
- `streamlit`
- `pandas`
- `altair`
- `plotly`
- `duckdb`
- `openai`
- `python-dotenv`

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
