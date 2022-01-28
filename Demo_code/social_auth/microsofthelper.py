from decouple import config
from linkedin import linkedin
import os
import requests, json


def get_auth_token(token):
    try:
        MICROSOFT_ME_URL = os.environ.get("MICROSOFT_ME_URL")

        headers = {
            'authorization': "Bearer " + token,
            'content-type': "application/json",
        }
        response = requests.get(MICROSOFT_ME_URL, headers=headers)

        return response.json()

        response.raise_for_status()
    except HTTPError as http_error:
        print('HTTP error occurred:', http_error)
        return http_error
    except Exception as err:
        print('Other error occurred:', err)
        return err
