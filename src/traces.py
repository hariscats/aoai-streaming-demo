import os
import subprocess
import requests
import json
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Configuration
deployment_name = os.getenv("APIM_DEPLOYMENT_NAME")
resource_group_name = os.getenv("RESOURCE_GROUP_NAME")
openai_deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")
openai_api_version = os.getenv("OPENAI_API_VERSION", "2024-09-01-preview")
subscription_key = os.getenv("APIM_SUBSCRIPTION_KEY")

# Helper function to run CLI commands
def run_command(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

# Retrieve deployment outputs
apim_service_id = run_command(
    f"az deployment group show --name {deployment_name} -g {resource_group_name} "
    "--query properties.outputResources[].id -o tsv"
)
apim_resource_gateway_url = run_command(
    f"az deployment group show --name {deployment_name} -g {resource_group_name} "
    "--query properties.outputs.gatewayUrl.value -o tsv"
)

print("👉🏻 APIM Service Id:", apim_service_id)
print("👉🏻 API Gateway URL:", apim_resource_gateway_url)

# Get Azure access token
token = run_command("az account get-access-token --query accessToken --output tsv")

# Request debug credentials for tracing
debug_payload = {
    "credentialsExpireAfter": "PT1H",
    "apiId": apim_service_id + "/apis/openai",
    "purposes": ["tracing"]
}
debug_url = f"https://management.azure.com{apim_service_id}/gateways/managed/listDebugCredentials?api-version=2024-06-01-preview"

debug_response = requests.post(
    debug_url,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    json=debug_payload
)
if debug_response.status_code == 200:
    debug_data = debug_response.json()
    apim_debug_authorization = debug_data.get("token")
else:
    print("Error getting debug credentials:", debug_response.text)
    exit(1)

# Construct the URL for the chat completions endpoint
completions_url = (
    f"{apim_resource_gateway_url}/openai/deployments/{openai_deployment_name}/chat/completions"
    f"?api-version={openai_api_version}"
)

# Prepare the chat messages payload
messages = {
    "messages": [
        {"role": "system", "content": "You are a sarcastic, unhelpful assistant."},
        {"role": "user", "content": "Can you tell me the time, please?"}
    ],
    "stream": True,
    "stream_options": {"include_usage": True}
}

# Make the POST request using the debug token header
response = requests.post(
    completions_url,
    headers={
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Apim-Debug-Authorization': apim_debug_authorization
    },
    json=messages,
    stream=True
)

# Track tokens and timestamps
start_time = datetime.now()
token_timestamps = []
received_tokens = []
usage_info = None

# Handle streaming
if response.status_code == 200:
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            json_data = line[len("data: "):].strip()

            if json_data == "[DONE]":
                break

            try:
                chunk = json.loads(json_data)
                
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        received_tokens.append(content)
                        token_timestamps.append((datetime.now() - start_time).total_seconds())
                        print(content, end="", flush=True)
                
                if "usage" in chunk:
                    usage_info = chunk["usage"]

            except json.JSONDecodeError:
                print("\n⚠️ Error decoding JSON:", json_data)

# Debugging Table
debug_table = [
    ["APIM Service ID", apim_service_id],
    ["API Gateway URL", apim_resource_gateway_url],
    ["Subscription Key Present", bool(subscription_key)],
    ["Response Status Code", response.status_code],
    ["Token Count", len(received_tokens)],
    ["Usage Info Available", bool(usage_info)]
]

print("\nDebugging Information:")
print(tabulate(debug_table, headers=["Metric", "Value"], tablefmt="grid"))

# Plotting Token Streaming Timeline
plt.figure(figsize=(10, 6))
plt.plot(token_timestamps, range(1, len(token_timestamps) + 1), marker='o')
plt.title("Token Streaming Timeline")
plt.xlabel("Time Elapsed (s)")
plt.ylabel("Cumulative Tokens Received")
plt.grid(True)
plt.show()

# Bar Chart for Token Distribution
if usage_info:
    labels = ["Prompt Tokens", "Completion Tokens"]
    values = [usage_info.get("prompt_tokens", 0), usage_info.get("completion_tokens", 0)]

    plt.figure(figsize=(6, 4))
    plt.bar(labels, values, color=['skyblue', 'lightcoral'])
    plt.title("Token Distribution")
    plt.ylabel("Token Count")
    plt.show()
else:
    print("No usage information available.")
