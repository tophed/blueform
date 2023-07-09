import json
import requests

url = "http://localhost:5001"


def main():
    # plan()
    apply()


def plan():
    r = requests.post(
        url + "/plan",
        json={
            "plan_id": "abc",
            "workspace": "default",
            "repo": "rito",
            "ref": "main",
            "meta":{
                "uid": "def"
            }
        },
    )
    print_response(r)


def apply():
    r = requests.post(
        url + "/apply",
        json={"plan_id": "abc"},
    )
    print_response(r)


def print_response(r):
    print(json.dumps(r.json(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
