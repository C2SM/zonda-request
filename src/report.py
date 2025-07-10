import requests
import argparse

class GitHubRepo:

    def __init__(self, group: str, repo: str, commit_sha: str = None, build_url: str = None, auth_token: str = None) -> None:
        self.group: str = group
        self.repo: str = repo
        self.commit_sha: str = commit_sha
        self.build_url: str = build_url
        self.auth_token: str = auth_token
        self.headers = {'Content-Type': 'application/json'}
        self.headers['Authorization'] = 'token ' + self.auth_token

    def comment(self, issue_id: str, text: str) -> None:
        url = f'https://api.github.com/repos/{self.group}/{self.repo}/issues/{issue_id}/comments'

        requests.post(url, headers=self.headers, json={'body': text})

    def commit_status(self, status: str, context: str, message: str) -> None:
        url = f'https://api.github.com/repos/{self.group}/{self.repo}/statuses/{self.commit_sha}'

        requests.post(url, headers=self.headers, json={'state': status, 'context': context, 'description': message, 'target_url': self.build_url})

    def update_labels(self, issue_id, remove_label, add_label):

        if remove_label:
            url = f'https://api.github.com/repos/{self.group}/{self.repo}/issues/{issue_id}/labels/{remove_label}'
            requests.delete(url, headers=self.headers)
        if add_label:
            url = f'https://api.github.com/repos/{self.group}/{self.repo}/issues/{issue_id}/labels'
            requests.post(url, headers=self.headers, json={'labels': [add_label]})
    
    def get_issue(self, issue_id: str) -> dict:
        url = f'https://api.github.com/repos/{self.group}/{self.repo}/issues/{issue_id}'
        response = requests.get(url, headers=self.headers)
        return response.json()['body']



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth_token', type=str, required=False)
    parser.add_argument('--commit_sha', type=str, required=False)
    parser.add_argument('--build_url', type=str, required=False)
    parser.add_argument('--jenkins_job_name', type=str, required=True)
    parser.add_argument('--issue_id_file', type=str, required=True)
    parser.add_argument('--hash-file', type=str, required=True)

    # Create a mutually exclusive group for the --abort and --failure arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--failure', action='store_true')
    group.add_argument('--abort', action='store_true')

    args = parser.parse_args()

    is_daily_testsuite = ('zonda-main' in args.jenkins_job_name)
    if is_daily_testsuite and (args.commit_sha is None or args.build_url is None):
        parser.error("--jenkins_job_name=*zonda-main* requires --commit_sha and --build_url for the status report to GitHub.")

    repo = GitHubRepo(group='c2sm',
                      repo='zonda-request',
                      commit_sha=args.commit_sha,
                      build_url=args.build_url,
                      auth_token=args.auth_token)

    with open(args.hash_file, 'r') as f:
        hash = f.read()

    with open(args.issue_id_file, 'r') as f:
        issue_id = f.read()

    url = f'https://data.iac.ethz.ch/zonda/{hash}'

    fail_comment = f"Something went wrong. Please check the [logfiles]({url}) for more information."
    abort_comment = f"Your request has been aborted. Please check the [logfiles]({url}) for more information."
    success_comment = (
        f"Your data is ready for up to 7 days under this [link]({url}).\n\n"
        f"You can also download it using the following commands:\n"
        f"```bash\n"
        f"wget {url}/output.zip\n"
        f"unzip output.zip -d zonda_output\n"
        f"```"
    )

    fail_status_msg = "Testsuite failed!"
    abort_status_msg = "Testsuite aborted!"
    success_status_msg = "Testsuite completed successfully!"

    daily_testsuite_context = 'Daily Testsuite of main on Jenkins'

    if args.failure:
        repo.comment(issue_id=issue_id, text=fail_comment)
        add_label = 'failed'

        if is_daily_testsuite:
            repo.commit_status( status  = 'failure',
                                context = daily_testsuite_context,
                                message = fail_status_msg )
    elif args.abort:
        repo.comment(issue_id=issue_id, text=abort_comment)
        add_label = 'aborted'

        if is_daily_testsuite:
            repo.commit_status( status  = 'failure',
                                context = daily_testsuite_context,
                                message = abort_status_msg )
    else:
        repo.comment(issue_id=issue_id, text=success_comment)
        add_label = 'completed'

        if is_daily_testsuite:
            repo.commit_status( status  = 'success',
                                context = daily_testsuite_context,
                                message = success_status_msg )

    repo.update_labels(issue_id=issue_id, remove_label='submitted', add_label=add_label)
