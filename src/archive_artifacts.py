import os
import argparse
import shutil
import glob
import json

def move_zip(destination, zip_file, hash):
    folder = os.path.join(destination, hash)
    # Create the directory
    os.makedirs(folder, exist_ok=True)
    print(f"Created directory {folder}")

    # Move the zip file to the directory
    shutil.move(zip_file, folder)
    print(f"Moved {zip_file} to {folder}")

def move_logs(source_dir, destination, hash):
    folder = os.path.join(destination, hash)
    # Create the directory
    os.makedirs(folder, exist_ok=True)
    print(f"Created directory {folder}")

    # Move the logs
    for file in glob.glob(os.path.join(source_dir, '**/*.log')):
        dest_file = os.path.join(folder, os.path.basename(file))
        shutil.move(file, dest_file)
        print(f"Moved {file} to {dest_file}")

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Archive artifacts to a unique folder.")

    # Add the arguments
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser.add_argument('--destination', type=str, required=True, help='The destination folder to store the zip file')
    parser.add_argument('--hash-file', type=str, required=True, help='Hash file')
    parser.add_argument('--workspace', type=str, required=True, help='The workspace folder')
    parser.add_argument('--success', action='store_true', help='If the job was successful')

    # Parse the arguments
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    with open(config_path, 'r') as f:
        config = json.load(f)

    with open(args.hash_file, 'r') as f:
        hash = f.read().strip()

    output_dir = os.path.join(args.workspace, 'output')
    outfile = config['basegrid']['outfile']

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Move the zip file to the destination
    if args.success:
        move_zip(args.destination, os.path.join(args.workspace, f"zonda_output_{outfile}.zip"), hash)
    else:
        move_logs(output_dir, args.destination, hash)

if __name__ == "__main__":
    main()
