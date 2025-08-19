import time
from secret_manager import access_secret
import json
zcrm_oauth = json.loads(access_secret("kitrum-cloud", "zoho_crm"))
zp_oauth = json.loads(access_secret("kitrum-cloud", "zoho_people"))
zb_oauth = None
success_status_codes = [200, 201, 400]
