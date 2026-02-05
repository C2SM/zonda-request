import argparse
import json
import re
from report import GitHubRepo

def validate_user_input(comment_body):
    # Use regex to extract JSON content between ```json and ```
    match = re.search(r'```json(.*?)```', comment_body, re.DOTALL)
    if match:
        json_content = match.group(1).strip()
        print(json_content)
        return json_content
    raise ValueError('No JSON content found in the comment body')

def convert_to_json(comment_body):
    # Convert the dictionary back to a JSON string
    json_str = json.dumps(json.loads(comment_body), indent=4)
    print(json_str)

    # Write the JSON string to a file
    with open('config.json', 'w') as f:
        f.write(json_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate user input")
    parser.add_argument('--auth_token', type=str, required=False)
    parser.add_argument('--issue_id_file', type=str, required=True)

    args = parser.parse_args()

    with open(args.issue_id_file, 'r') as f:
        issue_id = f.read()

    repo = GitHubRepo(group='c2sm',
                      repo='zonda-request',
                      auth_token=args.auth_token)

    comment = validate_user_input(repo.get_issue(issue_id)).replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"').replace('\\\\', '\\').replace('submit request', '').strip()

    convert_to_json(comment)
