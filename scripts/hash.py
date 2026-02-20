import hashlib
import argparse
from datetime import datetime



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hash current time and create a file with the hash value")
    parser.add_argument("--hash-file", type=str, required=True, help="Hash file")

    args = parser.parse_args()

    # Get the current time as a string
    current_time = datetime.now().isoformat()

    # Create a hash from the current time
    hash = hashlib.sha256(current_time.encode()).hexdigest()

    with open(args.hash_file, "w") as file:
        file.write(hash)
