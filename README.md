# Azure OpenAI Streaming Demo

A minimal Python demo to stream completions from an Azure OpenAI deployment via APIM, count tokens using [tiktoken](https://github.com/openai/tiktoken) on the client-side, and compare against usage data returned from Azure OpenAI (AOAI). Includes advanced debugging features for API response analysis.

## Prerequisites

- Python 3.7+
- An Azure OpenAI deployment behind API Management (APIM)
- APIM subscription key
- Azure CLI (for debugging script functionality)

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/<your-username>/azure-openai-streaming-demo.git
   cd azure-openai-streaming-demo
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set environment variables:**

   In your shell, set the following variables (you can also set them permanently or via your system settings):

   ```bash
   export APIM_DEPLOYMENT_NAME="<your-apim-deployment-name>"
   export APIM_SUBSCRIPTION_KEY="<your-apim-subscription-key>"
   export OPENAI_DEPLOYMENT_NAME="gpt-35-turbo"        # Adjust as needed
   export OPENAI_API_VERSION="2024-09-01-preview"      # Optional, default is used if not set
   ```

   **Note:** These environment variables are required for both `main.py` and `azure_openai_streaming.py`.

## Run the Demo

### 1️⃣ **Streaming Completion with Token Analysis**

```bash
python src/main.py
```

- Streams the response in real time.
- Compares token counts using tiktoken against AOAI's usage data.

### 2️⃣ **Debugging Script**

```bash
python src/traces.py
```

- Captures detailed API response information, including:
  - APIM trace IDs
  - Token streaming timelines
  - Token distribution charts
  - Debugging tables with key metrics for troubleshooting

## License

MIT License