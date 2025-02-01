# Azure OpenAI Streaming Demo

A minimal Python demo to stream completions from an Azure OpenAI deployment via APIM and count tokens using [tiktoken](https://github.com/openai/tiktoken).

## Prerequisites

- Python 3.7+
- An Azure OpenAI deployment behind API Management
- APIM subscription key

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
   export API_MANAGEMENT_GATEWAY_URL="https://<your-apim-instance>.azure-api.net"
   export DEPLOYMENT_NAME="<your-deployment-name>"
   export APIM_SUBSCRIPTION_KEY="<your-apim-subscription-key>"
   export API_VERSION="2024-03-01-preview"       # Optional, default is used if not set
   export MODEL_FOR_TOKENS="gpt-4o-mini-2024-07-18" # Optional, default is used if not set
   ```

## Run the Demo

Simply run:

```bash
python main.py
```

When prompted, enter your question. The script streams the response in real time and logs token counts for both the prompt and the generated completion.

## License

MIT License
