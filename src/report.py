import requests
import argparse
import json

class GitHubRepo:

    def __init__(self, group: str, repo: str, auth_token: str = None) -> None:
        self.group: str = group
        self.repo: str = repo
        self.auth_token: str = auth_token
        self.headers = {'Content-Type': 'application/json'}
        self.headers['Authorization'] = 'token ' + self.auth_token

    def comment(self, issue_id: str, text: str) -> None:
        url = f'https://api.github.com/repos/{self.group}/{self.repo}/issues/{issue_id}/comments'

        requests.post(url, headers=self.headers, json={'body': text})

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
    parser.add_argument('--issue_id_file', type=str, required=True)
    parser.add_argument('--hash-file', type=str, required=True)
    parser.add_argument('--keyword-file', type=str, required=True)

    # Create a mutually exclusive group for the --abort and --failure arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--failure', action='store_true')
    group.add_argument('--abort', action='store_true')

    args = parser.parse_args()

    repo = GitHubRepo(group='c2sm',
                      repo='extpar-request',
                      auth_token=args.auth_token)

    with open(args.hash_file, 'r') as f:
        hash = f.read()

    with open(args.issue_id_file, 'r') as f:
        issue_id = f.read()

    with open(args.keyword_file, 'r') as f:
        keywords = json.load(f)
        PR_DELETE = keywords['PR_DELETE']
        PR_FAIL = keywords['PR_FAIL']
        PR_ABORT = keywords['PR_ABORT']
        PR_SUCCESS = keywords['PR_SUCCESS']


    url = f'https://data.iac.ethz.ch/extpar-request/{hash}'

    print(repo.get_issue(issue_id=issue_id))

    repo.comment(issue_id=issue_id, text=f'{url}')

    if args.failure:
        repo.comment(issue_id=issue_id, text=PR_FAIL)
        add_label = 'failed'
    elif args.abort:
        repo.comment(issue_id=issue_id, text=PR_ABORT)
        add_label = 'aborted'
    else:
        repo.comment(issue_id=issue_id, text=PR_SUCCESS)
        add_label = 'completed'

    repo.update_labels(issue_id=issue_id, remove_label='submitted', add_label=add_label)
    repo.comment(issue_id=issue_id, text=PR_DELETE)

