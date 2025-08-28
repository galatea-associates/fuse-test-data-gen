import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload


class GoogleDriveConnector():
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, root_folder_id, current_time_string):
        creds = self.build_creds()
        self.service = build('drive', 'v3', credentials=creds)
        self.root_folder_id = root_folder_id
        self.current_time_string = current_time_string

    def build_creds(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens,
        # and is created automatically when the authorization flow completes
        # for the first time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return creds

    def create_folder(self, folder_name, parent_folder_id):
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        return self.service.files().create(body=folder_metadata, fields='id')\
                   .execute().get('id')

    def get_folder_id(self, folder_name, parent_folder_id):
        q = """mimeType='application/vnd.google-apps.folder'
               and name='{0}' and trashed=false"""

        if parent_folder_id is not None:
            q += " and parents in '{0}'".format(parent_folder_id)

        folders = self.service.files()\
                      .list(q=q.format(folder_name),
                            spaces='drive',
                            fields='nextPageToken, files(id, name)',
                            ).execute().get('files', [])

        return folders[0].get('id') if len(folders) > 0 else None

    def get_file_id(self, file_name, parent_folder_id):
        q = "name='{0}' and trashed=false"

        if parent_folder_id is not None:
            q += " and parents in '{0}'".format(parent_folder_id)

        files = self.service.files()\
                    .list(q=q.format(file_name),
                          spaces='drive',
                          fields='nextPageToken, files(id, name)',
                          ).execute().get('files', [])

        return files[0].get('id') if len(files) > 0 else None

    def create_file(self, file_path, file_name, google_folder_id):
        file_location = os.path.join(file_path, file_name)
        file_metadata = {
            'name': file_name,
            'parents': [google_folder_id]
            }

        media = MediaFileUpload(file_location, resumable=True)
        request = self.service.files().create(media_body=media,
                                              body=file_metadata)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print("Uploaded %d%%." % int(status.progress() * 100))

    def update_file(self, file_path, file_name, file_id):
        file_location = os.path.join(file_path, file_name)
        media_body = MediaFileUpload(file_location, resumable=True)
        self.service.files().update(fileId=file_id,
                                    media_body=media_body).execute()

    def delete_folder(self, folder_id):
        """ For testing purposes only """
        try:
            self.service.files().delete(fileId=folder_id).execute()
        except Exception as e:
            print(f'error deleting folder: {e}')
