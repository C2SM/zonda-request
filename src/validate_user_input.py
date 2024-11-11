import argparse
import json

def validate_user_input(comment_body):
    # Add your validation logic here
    print(comment_body)

def convert_to_json(comment_body):
    # Convert the dictionary back to a JSON string
    json_str = json.dumps(json.loads(comment_body), indent=4)

    # Write the JSON string to a file
    with open('config.json', 'w') as f:
        f.write(json_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate user input")
    parser.add_argument("--comment_body", type=str, help="User input from the comment body.")
    args = parser.parse_args()

    comment = args.comment_body.replace('\\r\\n', ' ').replace('submit request', '').replace('\\', '')

    # Validate the user input
    validate_user_input(comment)

    convert_to_json(comment)
