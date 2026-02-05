import os
import shutil
import time
import argparse

def stage_for_deletion(filepath, dry_run, exclude):
    if filepath in exclude:
        print(f"Skip {filepath}")
        return
    if not dry_run:
        if os.path.isdir(filepath):
            shutil.rmtree(filepath)
        elif os.path.isfile(filepath):
            os.remove(filepath)
    print(f"Delete {filepath}")

# Create the parser
parser = argparse.ArgumentParser(description="Delete files older than a certain age")

# Add the arguments
parser.add_argument('--path', type=str, required=True, help='The directory path')
parser.add_argument('--threshold', type=int, required=True, help='The file age threshold (in days)')
parser.add_argument('--dry-run', action='store_true', help='Only print the files that would be deleted, without actually deleting them')
parser.add_argument('--exclude', nargs='*', default=[], help='Directories not to be deleted')

# Parse the arguments
args = parser.parse_args()

# The directory to check
directory = args.path

# The file age threshold (in seconds)
threshold = args.threshold * 24 * 3600  # Convert days to seconds

# The current time
now = time.time()

# Check each file in the directory
for filename in os.listdir(directory):
    # Get the full path of the file
    filepath = os.path.join(directory, filename)

    # If the file is older than the threshold, delete it
    if os.path.getmtime(filepath) < now - threshold:
        stage_for_deletion(filepath, args.dry_run, args.exclude)
