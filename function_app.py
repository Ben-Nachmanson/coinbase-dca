import logging
import azure.functions as func
from coinbase.rest import RESTClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from json import dumps
import uuid

# Azure Key Vault Configuration
key_vault_name = "cb-key"
KVUri = f"https://{key_vault_name}.vault.azure.net/"
key_secret = "api-key"
api_secret = "api-secret"

# Azure Function App
app = func.FunctionApp()

# Timer trigger function 0 6 1,15 * * "
@app.timer_trigger(schedule="0 12 1,15 * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    try:
        api_key, api_secret = get_api_credentials()  # Retrieve API keys dynamically
        limit_order(api_key, api_secret)
    except Exception as e:
        logging.error(f"Order Failed: {str(e)}")

    logging.info('Python timer trigger function executed.')

# Function to get API keys from Azure Key Vault
def get_api_credentials():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KVUri, credential=credential)

    # Retrieve API keys
    retrieved_api_key = client.get_secret(key_secret).value
    retrieved_api_secret = client.get_secret(api_secret).value

    return retrieved_api_key, retrieved_api_secret

# Function to place limit order
def limit_order(api_key, api_secret):
    client = RESTClient(api_key=api_key, api_secret=api_secret)

    # Fetch current BTC-USDC price
    product = client.get_product("BTC-USDC")
    btc_usdc_price = float(product["price"])

    # Set limit price to market price
    adjusted_btc_usdc_price = btc_usdc_price

    # Define budget and fee
    usdc_amount = 500
    taker_fee = 0.0075

    # Calculate USDC available for BTC after fee (approximation)
    price_after_fee = usdc_amount - (usdc_amount * taker_fee)  
    print(f"USDC after fee: {price_after_fee}")

    # Calculate BTC amount to buy
    base_size = price_after_fee / adjusted_btc_usdc_price
    base_size_str = f"{base_size:.8f}"  # Format to 8 decimal places
    print(f"Base size (BTC): {base_size_str}")

    #Uncomment to place limit order
    order = client.limit_order_gtc_buy(
        client_order_id=str(uuid.uuid4()),
        product_id="BTC-USDC",
        base_size=base_size_str,
        limit_price=str(adjusted_btc_usdc_price)
    )

    # Check order status
    if order['success']:
        order_id = order['success_response']['order_id']
        print(f"Order placed successfully. Order ID: {order_id}")
    else:
        error_response = order['error_response']
        print(f"Error: {error_response}")
