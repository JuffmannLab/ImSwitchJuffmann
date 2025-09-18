import requests

request = "http://192.168.0.177/api/simple"

if __name__ == "__main__":

    try:
        response = requests.get(request)
        response.raise_for_status()  # raises an error if HTTP response is 4xx or 5xx

        # Try to parse JSON
        data = response.json()
        print("Response JSON:", data)

    except requests.exceptions.RequestException as e:
        print("HTTP Request failed:", e)

    except ValueError:
        print("Response is not valid JSON. Raw response:")
        print(response.text)


    url = "http://192.168.0.177/api/flags"

    payload = {
        "remote": True,
        "HVon": False,
        "checkRatio": False,
        "calibrate": False,
        "reset": False
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises error if the request failed (HTTP 4xx/5xx)

        print("Response status code:", response.status_code)

        # If response is JSON
        try:
            print("Response JSON:", response.json())
        except ValueError:
            print("Non-JSON response:", response.text)

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)