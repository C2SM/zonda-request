import os
import shutil
import time
import argparse



def stage_for_deletion(path, dry_run, exclude):
    if path in exclude:
        print(f"Skip \"{path}\".")
        return

    if not dry_run:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)

    print(f"Delete \"{path}\".")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete files older than a certain age")
    parser.add_argument("--path", type=str, required=True, help="Path to the directory to clean")
    parser.add_argument("--threshold", type=int, required=True, help="The file age threshold (in days)")
    parser.add_argument("--dry-run", action="store_true", help="Only print the files that would be deleted, without actually deleting them")
    parser.add_argument("--exclude", nargs="*", default=[], help="Directories not to be deleted")

    args = parser.parse_args()

    directory = args.path

    # The file age threshold (in seconds)
    threshold = args.threshold * 24 * 3600  # Convert days to seconds

    current_time = time.time()

    for element in os.listdir(directory):
        path = os.path.join(directory, element)

        # If the file is older than the threshold, delete it
        if os.path.getmtime(path) < current_time - threshold:
            stage_for_deletion(path, args.dry_run, args.exclude)
