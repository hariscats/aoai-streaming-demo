import os
import requests
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import tiktoken
from tabulate import tabulate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configuration variables from environment
api_management_gateway_url = os.getenv("API_MANAGEMENT_GATEWAY_URL")
deployment_name = os.getenv("DEPLOYMENT_NAME")  # The deployment name for the API call
subscription_key = os.getenv("APIM_SUBSCRIPTION_KEY")
api_version = os.getenv("API_VERSION", "2024-09-01-preview")
# Model used for token counting (adjust as needed)
token_count_model = os.getenv("MODEL_FOR_TOKENS", "gpt-4o-mini-2024-07-18")

# Validate required environment variables
if not api_management_gateway_url:
    raise ValueError("Missing API_MANAGEMENT_GATEWAY_URL environment variable.")
if not deployment_name:
    raise ValueError("Missing DEPLOYMENT_NAME environment variable.")
if not subscription_key:
    raise ValueError("Missing APIM_SUBSCRIPTION_KEY environment variable.")

# Construct the API endpoint
completions_endpoint = f"{api_management_gateway_url}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

# Define headers for the APIM call
request_headers = {
    "Ocp-Apim-Subscription-Key": subscription_key,
    "Content-Type": "application/json",
    "Accept": "text/event-stream",  # Expect a streaming response
    "Request-ID": str(datetime.utcnow().timestamp()),
    "Client-Name": "AzureOpenAIStreamingDemo",
}

# Get user input
user_message = input("Enter your question: ")

# Build the request body with streaming enabled, including usage information
request_body = {
    "messages": [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": user_message}
    ],
    "max_tokens": 200,
    "temperature": 0.7,
    "top_p": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "stream": True,  # Enable streaming
    "stream_options": {"include_usage": True}  # Request that usage data is returned
}

###############################################################################
# Helper function to count tokens from messages using tiktoken
###############################################################################
def num_tokens_from_messages(messages, model=token_count_model):
    """
    Returns the number of tokens in a list of messages for the given model.
    This implementation is adapted from the OpenAI Cookbook.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    
    # These settings are based on how ChatGPT models format messages.
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06"
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0125.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4o-mini" in model:
        print("Warning: gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-mini-2024-07-18.")
        return num_tokens_from_messages(messages, model="gpt-4o-mini-2024-07-18")
    elif "gpt-4o" in model:
        print("Warning: gpt-4o and gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-2024-08-06.")
        return num_tokens_from_messages(messages, model="gpt-4o-2024-08-06")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(f"num_tokens_from_messages() is not implemented for model {model}.")

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # Every reply is primed with a special token sequence
    return num_tokens

# Count and log prompt token count
prompt_token_count = num_tokens_from_messages(request_body["messages"])
logging.info(f"Prompt token count: {prompt_token_count}")

logging.info(f"Sending request to: {completions_endpoint}")
logging.info(f"Request Headers: {json.dumps(request_headers, indent=2)}")
logging.info(f"Request Body: {json.dumps(request_body, indent=2)}")

###############################################################################
# Function to stream the chat completion response from APIM
###############################################################################
def stream_chat_completion(endpoint, headers, body):
    """
    Sends a POST request with streaming enabled and yields each JSON chunk as it arrives.
    Each line in the response should begin with "data: " per the server-sent events format.
    """
    try:
        with requests.post(endpoint, headers=headers, json=body, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            logging.info("Stream ended.")
                            break
                        try:
                            chunk = json.loads(data_str)
                            yield chunk
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error: {e} with data: {data_str}")
                    else:
                        logging.debug(f"Ignored line: {line}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Streaming request failed: {e}")
        yield None

###############################################################################
# Process the streaming response and count tokens in the completion text
###############################################################################
collected_tokens = []
all_chunks = []         # Store every JSON chunk for later printing
streamed_usage = None   # To capture the usage field from the final chunk
start_time = time.time()

logging.info("Streaming response...")

for chunk in stream_chat_completion(completions_endpoint, request_headers, request_body):
    elapsed = time.time() - start_time
    if chunk is None:
        logging.error("Received an error chunk; aborting.")
        break

    # Append the chunk to our list of all chunks
    all_chunks.append(chunk)

    # Check if this chunk contains usage information (typically in the final chunk)
    if "usage" in chunk and chunk["usage"]:
        streamed_usage = chunk["usage"]

    # Extract tokens from the delta field (streamed responses use 'delta' instead of a full message)
    if "choices" in chunk and chunk["choices"]:
        delta = chunk["choices"][0].get("delta", {})
        token = delta.get("content")
        if token:
            print(token, end="", flush=True)
            collected_tokens.append(token)
            logging.info(f"Received token '{token}' at {elapsed:.2f} seconds.")
    else:
        logging.debug("Received chunk without choices: " + json.dumps(chunk, indent=2))

print("\n")
full_reply = "".join(collected_tokens)
total_time = time.time() - start_time

# Count completion tokens using tiktoken
try:
    encoding = tiktoken.encoding_for_model(token_count_model)
except KeyError:
    print("Warning: model not found. Using o200k_base encoding.")
    encoding = tiktoken.get_encoding("o200k_base")
completion_token_count = len(encoding.encode(full_reply))
logging.info(f"Completion token count (tiktoken): {completion_token_count}")

total_tokens = prompt_token_count + completion_token_count
logging.info(f"Full reply: {full_reply}")
logging.info(f"Total streaming time: {total_time:.2f} seconds")
logging.info(f"Total tokens used (computed): {total_tokens}")

# Print raw streamed JSON output and usage before printing the table
print("\nRaw Streamed JSON Output:")
print(json.dumps(all_chunks, indent=4))

if streamed_usage:
    print("\nStreamed Usage Data:")
    print(json.dumps(streamed_usage, indent=4))
else:
    print("\nNo usage data was received in the stream.")

# Prepare comparison table data
if streamed_usage:
    api_prompt_tokens = streamed_usage.get("prompt_tokens", "N/A")
    api_completion_tokens = streamed_usage.get("completion_tokens", "N/A")
    api_total_tokens = streamed_usage.get("total_tokens", "N/A")
else:
    api_prompt_tokens = api_completion_tokens = api_total_tokens = "N/A"

table_data = [
    ["Prompt Tokens", prompt_token_count, api_prompt_tokens],
    ["Completion Tokens", completion_token_count, api_completion_tokens],
    ["Total Tokens", total_tokens, api_total_tokens]
]

print("\nComparison Table:")
print(tabulate(table_data, headers=["Metric", "Computed", "API Usage"], tablefmt="grid"))
