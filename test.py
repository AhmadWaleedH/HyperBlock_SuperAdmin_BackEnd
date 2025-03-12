import requests
import json
import hmac
import hashlib
import base64
from datetime import datetime

# Example credentials
merchant_id = "14988441_1741802590"
api_key_id = "9c3a475b-f0e9-44f7-b602-e5834cd02a70"
secret_key = "gEF7hzsV2fB1PyOJ25iUpPgifVu1cM4n1J/GXqQ33xM="
profile_id = "14988441_1741802590_nt_acct"
base_url = "https://apitest.cybersource.com"

# Generate headers
def generate_signature(resource_path, payload, method):
    timestamp = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    payload_string = json.dumps(payload) if payload else ""
    
    digest = hashlib.sha256(payload_string.encode('utf-8')).digest()
    digest_base64 = base64.b64encode(digest).decode('utf-8')
    
    host = base_url.replace("https://", "")
    signature_string = f"host: {host}\ndate: {timestamp}\n(request-target): {method.lower()} {resource_path}\ndigest: SHA-256={digest_base64}\nv-c-merchant-id: {merchant_id}"
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    signature_base64 = base64.b64encode(signature).decode('utf-8')
    
    return {
        "v-c-merchant-id": merchant_id,
        "Date": timestamp,
        "Digest": f"SHA-256={digest_base64}",
        "Signature": f'keyid="{api_key_id}", algorithm="HmacSHA256", headers="host date (request-target) digest v-c-merchant-id", signature="{signature_base64}"',
        "Content-Type": "application/json"
    }

# Create payload
payload = {
    "clientReferenceInformation": {
        "code": "test_ref_123"
    },
    "processingInformation": {
        "commerceIndicator": "recurring"
    },
    "orderInformation": {
        "amountDetails": {
            "totalAmount": "10.00",
            "currency": "USD"
        }
    },
    "unifiedCheckoutInformation": {
        "profileId": profile_id,
        "returnUrl": "https://yourwebsite.com/return"
    }
}

# Generate headers
resource_path = "/pts/v2/checkouts"
headers = generate_signature(resource_path, payload, "post")

# Make the request
response = requests.post(
    f"{base_url}{resource_path}",
    headers=headers,
    json=payload
)

print("Response Status Code:", response.status_code)
print("Response Body:", response.text)