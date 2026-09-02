import os
import time
import requests
import argparse
import json
import jwt


def installation_token(app_id, key_path, installation_id):
    with open(os.path.expanduser(key_path), "r") as file:
        key = file.read()

    # The issued-at time is backdated to tolerate clock skew; the expiration stays below GitHub's 10-minute limit for App JWTs.
    now = int(time.time())
    assertion = jwt.encode({"iat": now - 60, "exp": now + 540, "iss": app_id}, key, algorithm="RS256")

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers={"Authorization": f"Bearer {assertion}", "Accept": "application/vnd.github+json"})
    response.raise_for_status()

    return response.json()["token"]


class GitHubRepo:

    def __init__(self, group, repo, auth_token=None):
        self.group = group
        self.repo = repo
        self.auth_token = auth_token
        self.headers = {"Content-Type": "application/json"}
        self.headers["Authorization"] = f"token {self.auth_token}"

        self.repo_api_url = f"https://api.github.com/repos/{self.group}/{self.repo}"

    def comment(self, issue_id, text):
        url = f"{self.repo_api_url}/issues/{issue_id}/comments"

        requests.post(url, headers=self.headers, json={"body": text})

    def remove_labels(self, issue_id, labels):
        for label in labels:
            url = f"{self.repo_api_url}/issues/{issue_id}/labels/{label}"

            requests.delete(url, headers=self.headers)

    def add_labels(self, issue_id, labels):
        if labels:
            url = f"{self.repo_api_url}/issues/{issue_id}/labels"

            requests.post(url, headers=self.headers, json={"labels": labels})

    def get_issue(self, issue_id):
        url = f"{self.repo_api_url}/issues/{issue_id}"

        issue = requests.get(url, headers=self.headers)
        return issue.json()["body"]



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
    parser.add_argument("--auth-token", type=str, required=False)
    parser.add_argument("--app-id", type=str, required=False, default=os.environ.get("ZONDA_APP_ID"))
    parser.add_argument("--app-key", type=str, required=False, default=os.environ.get("ZONDA_APP_KEY", "~/.config/zonda/bot.pem"))
    parser.add_argument("--installation-id", type=str, required=False, default=os.environ.get("ZONDA_APP_INSTALLATION_ID"))
    parser.add_argument("--issue-id-file", type=str, required=True)
    parser.add_argument("--hash-file", type=str, required=True)

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--success", action="store_true")
    group.add_argument("--failure", action="store_true")
    group.add_argument("--aborted", action="store_true")
    group.add_argument("--invalid", action="store_true")

    args = parser.parse_args()

    if not args.invalid:
        config_path = os.path.abspath(args.config)
        with open(config_path, "r") as file:
            config = json.load(file)

        config_str = json.dumps(config, indent=2)
        config_collapsible = (
            f"\n\n"
            f"<details>\n\n"
            f"<summary>Expand to see the JSON config for this request.</summary>\n\n"
            f"```json\n"
            f"{config_str}\n"
            f"```\n\n"
            f"</details>"
        )

    with open(args.issue_id_file, "r") as file:
        issue_id = file.read()

    with open(args.hash_file, "r") as file:
        hash = file.read()

    output_url = f"https://data.iac.ethz.ch/zonda/{hash}"

    if args.success:
        request_name = config["zonda"]["request_name"]
        comment = (
            f"Your data is ready for up to 7 days under this [link]({output_url}).\n\n"
            f"You can also download it using the following commands:\n"
            f"```bash\n"
            f"wget {output_url}/zonda_output_{request_name}.zip\n"
            f"unzip zonda_output_{request_name}.zip -d zonda_output_{request_name}\n"
            f"```"
            f"{config_collapsible}"
        )
        label = "completed"

    elif args.failure:
        comment = (
            f"Something went wrong. Please check the [logfiles]({output_url}) for more information.\n\n"
            f"If desired, you can rerun this request by writing a comment containing (only) the string **rerun request**. "
            f"Note that you can edit the JSON snippet in the description before rerunning if you want to apply changes/correct errors."
            f"{config_collapsible}"
        )
        label = "failed"

    elif args.aborted:
        comment = (
            f"Your request has been aborted. Please check the [logfiles]({output_url}) for more information.\n\n"
            f"If desired, you can rerun this request by writing a comment containing (only) the string **rerun request**. "
            f"Note that you can edit the JSON snippet in the description before rerunning if you want to apply changes/correct errors."
            f"{config_collapsible}"
        )
        label = "aborted"

    elif args.invalid:
        comment = (
            f"The provided JSON snippet is invalid. Please make sure that there is no syntax error in your JSON.\n\n"
            f"Common problems are:\n\n"
            f"- The string `PASTE_YOUR_REQUEST_HERE` was not replaced correctly with the JSON snippet. Note that the "
            f"JSON code-block (\\`\\`\\`json ... \\`\\`\\`) must not be removed.\n"
            f"- Syntax errors in the JSON snippet. E.g., commas after the last entry of a JSON object ({{...}}) or array ([...]).\n\n"
            f"Note that you can edit the JSON snippet in the description to fix the errors and then rerun the request by commenting "
            f"\"**rerun request**\"."
        )
        label = "invalid"

    else:
        raise ValueError("No valid report status was selected!")

    # Generated here rather than passed in, so the token is no more than an hour old when the detached report runs.
    auth_token = args.auth_token
    if not auth_token:
        if not (args.app_id and args.installation_id):
            parser.error("either --auth-token, or --app-id and --installation-id (also settable via ZONDA_APP_ID and ZONDA_APP_INSTALLATION_ID) is required")
        auth_token = installation_token(args.app_id, args.app_key, args.installation_id)

    repository = GitHubRepo( group = "c2sm",
                             repo = "zonda-request",
                             auth_token = auth_token )

    repository.comment(issue_id=issue_id, text=comment)

    repository.remove_labels(issue_id=issue_id, labels=["submitted"])
    repository.add_labels(issue_id=issue_id, labels=[label])
