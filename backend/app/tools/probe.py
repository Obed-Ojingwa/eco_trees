import argparse
import json
import sys

from app.integrations.xtradot_bank import client


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a bank sandbox endpoint from the API environment.")
    parser.add_argument("method", choices=("GET", "POST"))
    parser.add_argument("path", help="Path relative to BANK_API_BASE, e.g. /banks")
    parser.add_argument("--body", help="Optional JSON request body")
    args = parser.parse_args()

    body = json.loads(args.body) if args.body else None
    response = client.request(args.method, args.path, json_body=body)
    print(f"status: {response.status_code}")
    safe_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"set-cookie", "authorization", "x-api-key"}
    }
    print(f"headers: {json.dumps(safe_headers, sort_keys=True)}")
    try:
        print(f"body: {json.dumps(response.json(), indent=2)}")
    except ValueError:
        print(f"body: {response.text[:4000]}")
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main())
