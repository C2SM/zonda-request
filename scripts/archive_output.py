import os
import argparse
import shutil
import json



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive artifacts to a unique folder")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
    parser.add_argument("--workspace", type=str, required=True, help="The workspace folder")
    parser.add_argument("--destination", type=str, required=True, help="The destination folder to store the zip file")
    parser.add_argument("--logfile", type=str, help="Path to the log file")
    parser.add_argument("--hash-file", type=str, required=True, help="Hash file")

    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    with open(config_path, "r") as file:
        config = json.load(file)

    with open(args.hash_file, "r") as file:
        hash = file.read().strip()

    outfile = config["basegrid"]["outfile"]

    hashed_destination_dir = os.path.join(args.destination, hash)
    os.makedirs(hashed_destination_dir, exist_ok=True)

    zip_filepath = os.path.join(args.workspace, f"zonda_output_{outfile}.zip")
    try:
        shutil.move(zip_filepath, hashed_destination_dir)
    except FileNotFoundError:
        print(f"Warning: zip file not found at \"{zip_filepath}\". Skipping move.")

    try:
        shutil.copy(args.logfile, hashed_destination_dir)
    except FileNotFoundError:
        print(f"Warning: log-file not found at \"{args.logfile}\". Skipping copy.")
