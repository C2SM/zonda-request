import hashlib
import argparse



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hash a build ID and create a file with the hash value")
    parser.add_argument("--build-id", type=str, required=True, help="Unique-ish value to hash, e.g. the GitHub Actions run ID")
    parser.add_argument("--hash-file", type=str, required=True, help="Hash file")

    args = parser.parse_args()

    # Truncated to 16 hex chars: still non-guessable for a capability URL
    # with a 7-day expiry, and far more usable than a 64-char SHA-256.
    hash = hashlib.sha256(args.build_id.encode()).hexdigest()[:16]

    with open(args.hash_file, "w") as file:
        file.write(hash)
