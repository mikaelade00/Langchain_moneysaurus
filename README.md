# LangGraph Financial Recorder (Moneysaurus) 🦖💰

Moneysaurus is an AI-powered financial assistant built using **LangGraph** and **Gemini 2.0/2.5 Flash**. This bot is designed to automatically record your expenses via Telegram, through both text messages and photos of receipts/bills.

## ✨ Key Features
- **Natural Language Processing**: Record expenses simply by typing naturally (e.g., "Bought chicken rice for 15k for lunch").
- **Vision Support**: Automatically extract expense data from photos of receipts or shopping bills.
- **Smart Categorization**: AI automatically categorizes your expenses.
- **Memory Management**: Equipped with a `limit_memory` feature for token efficiency and stable performance.
- **Persistent Storage**: Uses PostgreSQL to keep your expense history organized.
- **Interactive Retrieval**: Ask for total expenses or summaries per category directly in the chat.

## 🛠️ Tech Stack
- **AI Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) & [LangChain](https://github.com/langchain-ai/langchain)
- **LLM**: [Google Gemini 2.0/2.5 Flash](https://ai.google.dev/)
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (with pgvector support)
- **Deployment**: Docker & Ngrok (for Telegram Webhook)
- **Integration**: [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/username/Langchain_moneysaurus.git
cd Langchain_moneysaurus
```

### 2. Configure Environment
Copy the `.env.example` file to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Fill in the following variables in `.env`:
- `GOOGLE_API_KEY`: Get it from [Google AI Studio](https://aistudio.google.com/).
- `TELEGRAM_BOT_TOKEN`: Get it from [@BotFather](https://t.me/botfather).
- `WEBHOOK_URL`: Your ngrok URL or public domain.
- `POSTGRES_...`: Your database configuration.

### 3. Install Dependencies (Local Mode)
To run without Docker:
```bash
pip install -r requirements.txt
python main.py
```

## 🐳 Deployment with Docker
The easiest way to run this project is using Docker Compose:

1. Ensure Docker and Docker Compose are installed.
2. Run the command:
   ```bash
   docker-compose up -d
   ```
3. The bot will run automatically, and ngrok will provide the tunnel for the Telegram webhook.

## 📝 Usage
1. Open your Telegram bot.
2. Send a message like: *"Record buying fried rice for 20000 and ice tea for 5000"*
3. Or send a **photo of your receipt**.
4. The AI will confirm the recorded data.
5. Check summaries: *"What is my total expense?"* or *"Show expenses per category"*.

## 🛡️ Security
- Sensitive credentials are stored in `.env` (ignored by git).
- Equipped with `WEBHOOK_SECRET` to validate every request from the Telegram API.

## 🤝 Contributing
Contributions are always welcome! Please contact the developer or submit a Pull Request.

---
Built with ❤️ using Gemini & LangGraph.
