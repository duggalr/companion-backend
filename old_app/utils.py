import requests

def get_user_information(token):
    url = f"https://dev-2qo458j0ehopg3ae.us.auth0.com/userinfo"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    return response
