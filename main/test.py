import json
import requests

url = "http://127.0.0.1:5000"


def main():
    # create_repo()
    # get_content()
    set_content()

def create_repo():
    r = requests.post(
        url + "/create_repo",
        json={ "name": "rito" }
    )
    print_response(r)


def get_content():
    r = requests.post(
        url + "/get_content",
        json={
            "repo": "rito",
            "sha": "a553b6a18a9926b8ed0b3242bef39fd40e59600c"
        },
    )
    print_response(r)


def set_content():
    r = requests.post(
        url + "/set_content",
        json={
            "repo": "rito",
            "branch": "main",
            "elements": [
                {
                    "address": "resource.google_storage_bucket.blufrm_test"
                }
            ]
        },
    )
    print_response(r)


def print_response(r):
    try:
        print(json.dumps(r.json(), indent=2, sort_keys=True))
    except requests.exceptions.JSONDecodeError:
        print(r.content.decode())


if __name__ == "__main__":
    main()
