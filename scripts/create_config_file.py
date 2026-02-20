import argparse
import json
import re
from report import GitHubRepo



def extract_json_from_issue(issue_body):
    match = re.search(r"```json(.*?)```", issue_body, re.DOTALL)

    if match:
        json_snippet = match.group(1).strip()

        try:
            # Check for errors in the JSON file
            json_config_str = json.dumps(json.loads(json_snippet), indent=4)
        except Exception:
            raise

        return json_config_str
    else:
        raise ValueError("No JSON content found in the issue body.")


def write_config_file(config_filename, json_config_str):
    with open(config_filename, "w") as file:
        file.write(json_config_str)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create config file and validate JSON input")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
    parser.add_argument("--auth-token", type=str, required=True)
    parser.add_argument("--issue-id-file", type=str, required=True)

    args = parser.parse_args()
    config_filename = args.config

    with open(args.issue_id_file, "r") as file:
        issue_id = file.read()

    repository = GitHubRepo( group = "c2sm",
                             repo = "zonda-request",
                             auth_token = args.auth_token )

    json_config_str = extract_json_from_issue(repository.get_issue(issue_id)).strip()

    write_config_file(config_filename, json_config_str)
