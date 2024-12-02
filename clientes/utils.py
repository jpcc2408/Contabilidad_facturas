import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_google_sheets_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def sync_sheet_data():
    try:
        creds = get_google_sheets_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        SPREADSHEET_ID = 'Z6v3s3Yied4quKzkYwiEgd'
        RANGE_NAME = 'CLIENTE!A:G'
        
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        
        values = result.get('values', [])
        print("Data retrieved:", values)
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False