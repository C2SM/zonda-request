import os
import hashlib
import argparse
import shutil

# Create the parser
parser = argparse.ArgumentParser(description="Process build ID and HTTPS link")

# Add the arguments
parser.add_argument('--destination', type=str, required=True, help='The destination folder to store the zip file')
parser.add_argument('--zip-file', type=str, required=True, help='Zip file to share with the user')
parser.add_argument('--hash-file', type=str, required=True, help='Hash file')

# Parse the arguments
args = parser.parse_args()

with open(args.hash_file, 'r') as f:
    hash = f.read()

folder = os.path.join(args.destination, hash)
# Create the directory
os.makedirs(folder, exist_ok=True)
print(f"Created directory {folder}")

# Copy the zip file to the directory
shutil.copy(args.zip_file, folder)
