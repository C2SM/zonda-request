import os
import hashlib
import argparse
import shutil

# Create the parser
parser = argparse.ArgumentParser(description="Hash Build ID and create a file with the hash value.")

# Add the arguments
parser.add_argument('--build-id', type=str, required=True, help='The build ID')
parser.add_argument('--hash-file', type=str, required=True, help='Hash file')

# Parse the arguments
args = parser.parse_args()

# Compute the SHA256 hash of BUILD_ID
hash = hashlib.sha256(args.build_id.encode()).hexdigest()

with open(args.hash_file, 'w') as f:
    f.write(hash)
