import time
from datetime import datetime, date
from zoho_api.api import api_request
import json

ALL_MEMBERS_LEADS = ["Platform Campaign"]
SUBMISSION_STATUSES = {
    "Hired": ["HIRED", "STARTED"],
    "Lost": ["Lost", "OFFER: Declined", "Not Interested"],
    "Rejected": ["Rejected"]
}

CLOSE_STAGES = {
   "Communication": {
      "INTERNAL: English check sent",
      "INTERNAL: Communication",
      "INTERNAL: Discussing with dev",
      "INTERNAL: CV reviewed",
      "INTERNAL: English checked",
      "INTERNAL: HR Interview scheduled",
      "INTERNAL: Call Skipped",
      "INTERNAL: Test Task",
   },
   "Interviewed by HR": {
      "Tech Interviewer: Approve",
      "INTERNAL: Ready for Submit",
      "INTERNAL: Interviewed by HR",
      "INTERNAL: HR Feedback form sent",
      "INTERNAL: Submitted to tech specialist",
      "INTERNAL: Tech interview scheduled",
      "INTERNAL: Tech call skipped",
      "INTERNAL: Test Task",
   },
   "Interviewed by Tech specialist": {
      "INTERNAL: Tech feedback form sent",
      "INTERNAL: Tech feedback received",
      "CLIENT: Test Task Reviewing"
   },
   "Submitted to client": {
      "CLIENT: Submitted to Client",
      "CLIENT: Tech/Intro Interview",
      "CLIENT: Feedback received",
      "CLIENT: Test Task Processing",
      "CLIENT: Approved",
      "CLIENT: To-be-offered",
      "INTERNAL: Submitted to SM/DM"
   },
   "Offer made": {
      "OFFER: Made",
      "OFFER: Declined"
   },
   "Hired": {
      "Contractor Approved"
   }
}


def split_list(lst, chunk_size=100):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


class CgtCampaignCalculator:
    def __init__(self, campaign, all_campaigns):
        self.sync_date = date.today().strftime('%Y-%m-%d')
        self.all_campaigns = all_campaigns
        self.campaign = campaign
        self.campaign_date = datetime.strptime(campaign['Created_Date'], "%Y-%m-%d").date()
        self.campaign_candidates = []
        self.campaign_candidates_details = {}
        self.campaign_type = campaign['Campaign_Type']
        self.campaign_step = None
        self.request = {}
        self.request_submissions = []
        self.total_leads = 0
        self.campaign_candidates_update_data = []
        self.campaign_update_data = []
        self.candidates_with_other_campaigns = []

    def get_candidates(self):
        page = 0
        while True:
            page += 1
            page_response = api_request(
                f"https://www.zohoapis.com/crm/v2/Marketing_Activities/{self.campaign['id']}/Candidates16?page={page}",
                "zoho_crm",
                "get",
                None
            )
            page_data = page_response['data'] if page_response else []
            if not page_data:
                break
            self.campaign_candidates.extend(page_data)
        print(f"\tTotal Candidates Assigned: {len(self.campaign_candidates)}")

    def get_request(self):
        self.request = api_request(
            f"https://www.zohoapis.com/crm/v2/Requests/{self.campaign['Request']['id']}",
            "zoho_crm",
            "get",
            None
        )['data'][0]
        print(f"\tRequest Details Collected Successfully")

    def get_submissions(self):
        page = 0
        while True:
            page += 1
            page_response = api_request(
                f"https://www.zohoapis.com/crm/v2/Requests/{self.campaign['Request']['id']}/Candidates7?page={page}",
                "zoho_crm",
                "get",
                None
            )
            page_data = page_response['data'] if page_response else []
            if not page_data:
                break
            self.request_submissions.extend(page_data)
        print(f"\tTotal Submissions assigned to a Request: {len(self.request_submissions)}")

    def get_candidate_details(self):
        candidate_ids = []
        for candidate in self.campaign_candidates:
            candidate_ids.append(candidate['Developer_Participants']['id'])
        candidate_ids_chunks = split_list(candidate_ids)
        for candidate_ids_chunk in candidate_ids_chunks:
            chunk_response = api_request(
                f"https://www.zohoapis.com/crm/v2/Candidates?ids={','.join(candidate_ids_chunk)}",
                "zoho_crm",
                "get",
                None
            )['data']
            for chunk_item in chunk_response:
                self.campaign_candidates_details[chunk_item['id']] = chunk_item
        print(f"\tSuccessfully Collected Details for {len(candidate_ids)} Candidates")

    def get_candidate_submissions(self, candidate_id):
        candidate_submissions = []
        for request_submission in self.request_submissions:
            submission_date = datetime.fromisoformat(request_submission['Created_Time']).date()
            if request_submission['Candidates_for_request']['id'] == candidate_id and submission_date >= self.campaign_date:
                candidate_submissions.append(request_submission)
        return candidate_submissions

    def get_candidate_campaigns(self, candidate_id):
        return api_request(
            f"https://www.zohoapis.com/crm/v2/Candidates/{candidate_id}/Marketing_Activities16",
            "zoho_crm",
            "get",
            None
        )['data']

    def get_other_campaign_dates(self, other_campaign_ids):
        other_campaign_dates = []
        for other_campaign_id in other_campaign_ids:
            for campaign in self.all_campaigns:
                if campaign['id'] == other_campaign_id:
                    other_campaign_dates.append(datetime.strptime(campaign['Created_Date'], "%Y-%m-%d").date())
                    break
        return other_campaign_dates

    def collect_member_updates(self):
        for campaign_candidate in self.campaign_candidates:
            campaign_candidate_id = campaign_candidate['id']
            candidate_id = campaign_candidate['Developer_Participants']['id']
            candidate_details = self.campaign_candidates_details[candidate_id]
            # CHECK IF IS INTERESTED
            lead_date = datetime.strptime(candidate_details['Lead_Date'], "%Y-%m-%d").date() if candidate_details['Lead_Date'] else None
            is_interested = True if self.campaign_type in ALL_MEMBERS_LEADS else False
            # days_to_become_lead = None
            if not is_interested and lead_date and lead_date > self.campaign_date:
                # days_to_become_lead = (lead_date - self.campaign_date).days
                candidate_campaigns = self.get_candidate_campaigns(candidate_id)
                other_campaigns_ids = []
                for candidate_campaign in candidate_campaigns:
                    if candidate_campaign['Developer_Participant']['id'] == self.campaign['id']:
                        continue
                    other_campaigns_ids.append(candidate_campaign['Developer_Participant']['id'])
                print(f"\tOther Campaigns IDS: {len(other_campaigns_ids)}")
                if not other_campaigns_ids:
                    is_interested = True
                else:
                    other_campaigns_dates = self.get_other_campaign_dates(other_campaigns_ids)
                    # input(f"OTHER CAMPAIGN DATES: {other_campaigns_dates}")
                    sorted_other_campaigns_dates = sorted(other_campaigns_dates)
                    next_campaign_date = None
                    for sorted_other_campaigns_date in sorted_other_campaigns_dates:
                        if sorted_other_campaigns_date > self.campaign_date:
                            next_campaign_date = sorted_other_campaigns_date
                            break
                    if next_campaign_date:
                        self.candidates_with_other_campaigns.append(candidate_id)
                    if not next_campaign_date or (next_campaign_date and next_campaign_date > lead_date >= self.campaign_date):
                        is_interested = True

            candidate_submissions = self.get_candidate_submissions(candidate_id)

            is_replied = True if candidate_submissions else False
            # GET LATEST SUBMISSION RELATED TO THIS REQUEST
            latest_submission = {}
            if len(candidate_submissions) == 1:
                latest_submission = candidate_submissions[0]
            elif len(candidate_submissions) > 1:
                candidate_submission_dates = []
                for candidate_submission in candidate_submissions:
                    candidate_submission_dates.add(datetime.fromisoformat(candidate_submission['Created_Time']).date())
                max_date = max(candidate_submission_dates)
                index_of_max_date = candidate_submission_dates.index(max_date)
                latest_submission = candidate_submissions[index_of_max_date]
            # GET SUBMISSION STATUS
            candidate_status = latest_submission['Candidate_Status'] if latest_submission else None

            submission_status = None
            if candidate_status:
                for key, value in SUBMISSION_STATUSES.items():
                    if candidate_status in value:
                        submission_status = key
                        break
                if not submission_status:
                    submission_status = "Active"

            # GET CLOSE STAGE
            candidate_close_stage = latest_submission['Lost_Stage'] if latest_submission else None
            close_stage = None
            if candidate_close_stage:
                for key, value in CLOSE_STAGES.items():
                    if candidate_close_stage in value:
                        close_stage = key
                        break

            if not submission_status or submission_status == "Active":
                close_stage = None

            is_hired = True if candidate_status in ['HIRED', 'STARTED'] else False
            # GET MEMBER STATUS
            member_status = "Sent"
            if is_hired:
                member_status = "Hired"
            elif is_interested:
                member_status = "Interested"
            elif is_replied:
                member_status = "Responded"
            campaign_step = None
            if 'LinkedIn' in self.campaign_type:
                # get from candidate
                li_steps = candidate_details['Way_1_Cold_Candidates'] if 'Way_1_Cold_Candidates' in candidate_details else []
                if "FU2" in li_steps:
                    campaign_step = "FU2"
                elif "FU1" in li_steps:
                    campaign_step = "FU1"
                elif "Intro" in li_steps:
                    campaign_step = "Intro"
                elif "Invite" in li_steps:
                    campaign_step = "Invite"
            else:
                campaign_step = "Basic Email"
            if is_interested:
                self.total_leads += 1
            candidate_update_data = {
                "id": campaign_candidate_id,
                "Campaign_member_status": member_status,
                "Submission_state": submission_status,
                "Close_stage": close_stage,
                "Campaign_s_step": campaign_step
            }
            print(f"{json.dumps(candidate_update_data, indent=4)}")
            self.campaign_candidates_update_data.append(candidate_update_data)

    def collect_campaign_updates(self):
        request_status = self.request['Status']
        campaign_status = "Finished" if 'Closed' in request_status else "Active"

        campaign_update_data = {
            "id": self.campaign['id'],
            "Number_of_leads": self.total_leads,
            "Campaign_Status": campaign_status,
            "Last_Calculation_Date": self.sync_date
        }
        if self.campaign_type not in ALL_MEMBERS_LEADS:
            campaign_update_data['Total_Sent'] = len(self.campaign_candidates)
        print(f"{json.dumps(campaign_update_data, indent=4)}")
        self.campaign_update_data.append(campaign_update_data)

    def update_campaign_members(self):
        success, errors = 0, 0
        campaign_members_chunks = split_list(self.campaign_candidates_update_data)
        for campaign_members_chunk in campaign_members_chunks:
            post_data = {"data": campaign_members_chunk}
            chunk_response = api_request(
                "https://www.zohoapis.com/crm/v2/Marketing_X_Candidates",
                "zoho_crm",
                "put",
                post_data
            )['data']
            for chunk_item in chunk_response:
                item_status = chunk_item['code']
                if item_status == "SUCCESS":
                    success += 1
                else:
                    errors += 1
        print(f"\tTotal Success: {success}")
        print(f"\tTotal Errors: {errors}")

    def update_campaign(self):
        success, errors = 0, 0
        post_data = {"data": self.campaign_update_data}
        chunk_response = api_request(
            "https://www.zohoapis.com/crm/v2/Marketing_Activities",
            "zoho_crm",
            "put",
            post_data
        )['data']
        for chunk_item in chunk_response:
            item_status = chunk_item['code']
            if item_status == "SUCCESS":
                success += 1
            else:
                errors += 1
        print(f"\tTotal Success: {success}")
        print(f"\tTotal Errors: {errors}")

    def calculate(self):
        print("----------" * 10)
        print(f"Campaign: {self.campaign['Name']}")
        print("\nGetting Assigned Candidates")
        self.get_candidates()
        print("\nGetting Candidates Details")
        self.get_candidate_details()
        print("\nGetting Request Details")
        self.get_request()
        print("\nGetting Submissions Related to Request")
        self.get_submissions()
        print(f"\nTotal Candidates Assigned: {len(self.campaign_candidates)}")
        print(f"\nTotal Submissions for Request Available: {len(self.request_submissions)}")
        print("\nCollecting Member Updates")
        self.collect_member_updates()
        print("\nCollecting Campaign Updates")
        self.collect_campaign_updates()
        print("\nUpdating Campaign Members")
        self.update_campaign_members()
        print("\nUpdating Campaign ")
        self.update_campaign()

        print("\nCandidates with newer Campaigns:")
        print(self.candidates_with_other_campaigns)


def main():
    all_campaigns = []
    active_campaigns = []
    page = 0
    while True:
        page += 1
        page_response = api_request(
            f"https://www.zohoapis.com/crm/v2/Marketing_Activities?cvid=1576533000411634266&page={page}",
            "zoho_crm",
            "get",
            None
        )
        page_data = page_response['data'] if page_response else []
        if not page_data:
            break
        for campaign in page_data:
            all_campaigns.append(campaign)
            if campaign['Campaign_Status'] == "Active":
                active_campaigns.append(campaign)

    for active_campaign in active_campaigns:
        # if active_campaign['Campaign_Type'] in ["Email Campaign", "Platform Campaign"]:
        #     continue
        # if active_campaign['id'] != "1576533000409968483":
        #     continue
        calculator = CgtCampaignCalculator(active_campaign, all_campaigns)
        calculator.calculate()


main()

