import os
import requests
import argparse
import json

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

    def update_commit_status(self, commit_sha, status, context, message, build_url):
        url = f"{self.repo_api_url}/statuses/{commit_sha}"

        requests.post(url, headers=self.headers, json={"state": status, "context": context, "description": message, "target_url": build_url})

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
    parser.add_argument("--issue-id-file", type=str, required=True)
    parser.add_argument("--hash-file", type=str, required=True)
    parser.add_argument("--jenkins-job-name", type=str, required=True)
    parser.add_argument("--commit-sha", type=str, required=False)
    parser.add_argument("--build-url", type=str, required=False)

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

    is_daily_testsuite = "zonda-main" in args.jenkins_job_name
    commit_sha = args.commit_sha
    build_url = args.build_url
    if is_daily_testsuite and (commit_sha is None or build_url is None):
        parser.error("--jenkins-job-name=\"zonda-main\" requires --commit-sha and --build-url for the status report to GitHub.")

    output_url = f"https://data.iac.ethz.ch/zonda/{hash}"

    if args.success:
        outfile = config["basegrid"]["outfile"]
        comment = (
            f"Your data is ready for up to 7 days under this [link]({output_url}).\n\n"
            f"You can also download it using the following commands:\n"
            f"```bash\n"
            f"wget {output_url}/zonda_output_{outfile}.zip\n"
            f"unzip zonda_output_{outfile}.zip -d zonda_output_{outfile}\n"
            f"```"
            f"{config_collapsible}"
        )
        status_message = "Testsuite completed successfully!"
        label = "completed"
        status = "success"

    elif args.failure:
        comment = (
            f"Something went wrong. Please check the [logfiles]({output_url}) for more information.\n\n"
            f"If desired, you can rerun this request by writing a comment containing (only) the string **rerun request**. "
            f"Note that you can edit the JSON snippet in the description before rerunning if you want to apply changes/correct errors."
            f"{config_collapsible}"
        )
        status_message = "Testsuite failed!"
        label = "failed"
        status = "failure"

    elif args.aborted:
        comment = (
            f"Your request has been aborted. Please check the [logfiles]({output_url}) for more information.\n\n"
            f"If desired, you can rerun this request by writing a comment containing (only) the string **rerun request**. "
            f"Note that you can edit the JSON snippet in the description before rerunning if you want to apply changes/correct errors."
            f"{config_collapsible}"
        )
        status_message = "Testsuite aborted!"
        label = "aborted"
        status = "failure"

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
        status_message = "Invalid JSON config!"
        label = "invalid"
        status = "failure"

    else:
        raise ValueError("No valid report status was selected!")

    repository = GitHubRepo( group = "c2sm",
                             repo = "zonda-request",
                             auth_token = args.auth_token )

    repository.comment(issue_id=issue_id, text=comment)

    if is_daily_testsuite:
        daily_testsuite_context = "Daily Testsuite of main on Jenkins"

        repository.update_commit_status( commit_sha = commit_sha,
                                         status = status,
                                         context = daily_testsuite_context,
                                         message = status_message,
                                         build_url = build_url )

    repository.remove_labels(issue_id=issue_id, labels=["submitted"])
    repository.add_labels(issue_id=issue_id, labels=[label])
