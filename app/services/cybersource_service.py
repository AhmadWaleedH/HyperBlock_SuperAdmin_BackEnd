import os
import json
import uuid
import hmac
import hashlib
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

class CybersourceService:
    def __init__(self):
        self.merchant_id = os.getenv("CYBERSOURCE_MERCHANT_ID")
        self.api_key_id = os.getenv("CYBERSOURCE_API_KEY_ID")
        self.secret_key = os.getenv("CYBERSOURCE_SECRET_KEY")
        self.profile_id = os.getenv("CYBERSOURCE_PROFILE_ID")
        self.environment = os.getenv("CYBERSOURCE_ENVIRONMENT", "test")
        
        # Set base URL based on environment
        self.base_url = "https://apitest.cybersource.com" if self.environment == "test" else "https://api.cybersource.com"
        
    
    def _generate_signature(self, resource_path: str, payload: Dict[str, Any], method: str) -> Dict[str, str]:
        """Generate signature for Cybersource API request"""
        timestamp = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        payload_string = json.dumps(payload) if payload else ""
        
        # Calculate digest
        digest = hashlib.sha256(payload_string.encode('utf-8')).digest()
        digest_base64 = base64.b64encode(digest).decode('utf-8')
        
        # Extract host from base URL
        host = self.base_url.replace("https://", "")
        
        # Create the signature string
        signature_string = f"host: {host}\ndate: {timestamp}\n(request-target): {method.lower()} {resource_path}\ndigest: SHA-256={digest_base64}\nv-c-merchant-id: {self.merchant_id}"
        
        # Generate the signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature_base64 = base64.b64encode(signature).decode('utf-8')
        
        # Return headers
        return {
            "v-c-merchant-id": self.merchant_id,
            "Date": timestamp,
            "Digest": f"SHA-256={digest_base64}",
            "Signature": f'keyid="{self.api_key_id}", algorithm="HmacSHA256", headers="host date (request-target) digest v-c-merchant-id", signature="{signature_base64}"'
        }

    async def create_checkout_session(self, amount: float, currency: str, reference_id: str, subscription_type: str, return_url: str) -> Dict[str, str]:
        """Create a Cybersource Unified Checkout session"""
        resource_path = "/pts/v2/checkouts"
        
        payload = {
            "clientReferenceInformation": {
                "code": reference_id
            },
            "processingInformation": {
                "commerceIndicator": "recurring"
            },
            "orderInformation": {
                "amountDetails": {
                    "totalAmount": str(amount),
                    "currency": currency
                }
            },
            "unifiedCheckoutInformation": {
                "profileId": self.profile_id,
                "returnUrl": return_url
            }
        }
        
        headers = self._generate_signature(resource_path, payload, "post")
        headers["Content-Type"] = "application/json"
        
        try:
            response = requests.post(
                f"{self.base_url}{resource_path}",
                headers=headers,
                json=payload
            )
            
            print("Response Status Code:", response.status_code)
            print("Response Body:", response.text)
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create checkout session: {response.text}"
                )
            
            data = response.json()
            return {
                "session_id": data.get("id"),
                "checkout_url": data.get("_links", {}).get("redirect", {}).get("href")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating checkout session: {str(e)}"
            )
    
    async def verify_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """Verify a completed checkout session"""
        resource_path = f"/up/v1/checkouts/{session_id}"
        
        headers = self._generate_signature(resource_path, None, "get")
        
        try:
            response = requests.get(
                f"{self.base_url}{resource_path}",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to verify checkout session: {response.text}"
                )
            
            data = response.json()
            
            # Extract payment token and customer info if available
            payment_token = None
            customer_id = None
            
            if "tokenInformation" in data:
                token_info = data.get("tokenInformation", {})
                if "paymentInstrument" in token_info:
                    payment_token = token_info.get("paymentInstrument", {}).get("id")
                if "customer" in token_info:
                    customer_id = token_info.get("customer", {}).get("id")
            
            return {
                "status": data.get("status"),
                "payment_token": payment_token,
                "customer_id": customer_id,
                "transaction_id": data.get("id"),
                "raw_response": data
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying checkout session: {str(e)}"
            )
    
    async def verify_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """Verify the signature from a Cybersource webhook"""
        webhook_secret = os.getenv("CYBERSOURCE_WEBHOOK_SECRET")
        if not webhook_secret:
            return False
        
        computed_signature = base64.b64encode(
            hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return signature == computed_signature