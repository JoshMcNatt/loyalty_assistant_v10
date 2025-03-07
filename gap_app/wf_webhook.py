import requests
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkfrontWebhook:
    def __init__(self):
        self.WEBHOOK_URL = "https://hook.app.workfrontfusion.com/mxcvjvj15gusctj09ems17mkeqfao1nm"
        self.headers = {"Content-Type": "application/json"}

    def create_payload(self, bonus_data):
        """Convert bonus configuration to Workfront payload"""
        try:
            # Extract dates from bonus data using consistent field names
            start_date = datetime.strptime(bonus_data[0]['startDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d")
            end_date = datetime.strptime(bonus_data[0]['endDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d")

            return {
                "Kobie Demo Campaign Requests": "Kobie Demo",
                "Subject": f"Bonus Request - {bonus_data[0]['description']}",
                "Project Name": f"Campaign Request - {bonus_data[0]['bonusCode']}",
                "Requestor Name": "Loyalty Assistant",
                "Requestor Email": "loyalty-assistant@kobie.com",
                "Request Type": "Bonus",
                "Bonus_Start_Date": start_date,
                "Bonus_End_Date": end_date,
                "Eligible Universe": "Universal",
                "Partner Organization": "Delta",
                "Audience Reach": "Program",
                "Program": bonus_data[0]['programCode'],
                "Status": "Inactive",
                "Bonus Type": bonus_data[0]['bonusType'],
                "Reward Type": "Miles",
                "Estimated Miles": 1,
                "Reward Amount": bonus_data[0]['rewardAmount'],
                "Rounding Rule": bonus_data[0]['roundingRule'],
                "Reward Details": bonus_data[0]['description'],
                "Bonus Category": bonus_data[0]['bonusCategory'],
                "Calculation Type": bonus_data[0]['calcType'],
                "Release Status": "Draft",
                "Bonus Code": bonus_data[0]['bonusCode']  # Added bonus code mapping
            }
        except Exception as e:
            logger.error(f"Error creating payload: {str(e)}")
            raise

    def send_request(self, bonus_data):
        """Send bonus request to Workfront"""
        try:
            payload = self.create_payload(bonus_data)
            logger.info("Sending request to Workfront...")
            
            response = requests.post(
                self.WEBHOOK_URL,
                data=json.dumps(payload),
                headers=self.headers
            )
            response.raise_for_status()
            
            status_message = f"Status: {response.status_code}"
            logger.info(f"Workfront response: {status_message}")
            return True, status_message
            
        except requests.exceptions.RequestException as e:
            error_message = f"Request failed: {str(e)}"
            logger.error(f"Workfront {error_message}")
            return False, error_message

# Usage example
if __name__ == "__main__":
    # Sample bonus data for testing
    test_bonus_data = [{
        "description": "Test Bonus",
        "bonusType": "TXNBONUS",
        "programCode": "SKYMILES",
        "startDate": "2025-02-27T00:00:00.000",
        "endDate": "2025-03-12T23:59:59.999",
        "calcType": "VARSKU",
        "rewardAmount": 2,
        "roundingRule": "UP",
        "bonusCode": "TEST123"
    }]

    # Test the webhook
    webhook = WorkfrontWebhook()
    success, response = webhook.send_request(test_bonus_data)
    
    if success:
        print(f"✅ Request sent successfully: {response}")
    else:
        print(f"❌ Request failed: {response}")