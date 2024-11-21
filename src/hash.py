import hashlib
import argparse
from datetime import datetime

# Create the parser
parser = argparse.ArgumentParser(description="Hash Build ID and create a file with the hash value.")
parser.add_argument('--hash-file', type=str, required=True, help='Hash file')

# Parse the arguments
args = parser.parse_args()

# Get the current time as a string
current_time = datetime.now().isoformat()

# Create a hash from the current time
hash = hashlib.sha256(current_time.encode()).hexdigest()

with open(args.hash_file, 'w') as f:
    f.write(hash)
