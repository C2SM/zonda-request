import os
import argparse
import shutil
import glob
import zipfile

def move_files(src_pattern, dest_dir, prefix=""):
    for file in glob.glob(src_pattern):
        dest_file = os.path.join(dest_dir, prefix + os.path.basename(file))
        print(f"Moving {file} to {dest_file}")
        shutil.move(file, dest_file)

def move_extpar(workspace, dest):
    i = 1
    for domain in sorted(glob.glob(os.path.join(workspace, 'extpar_*'))):
        # Move logfiles
        move_files(os.path.join(domain, "*.log"), os.path.join(dest, 'logs'), f"DOM_{i}_")
        # Move external parameter file
        move_files(os.path.join(domain, "external_parameter*.nc"), dest, f"DOM_{i}_")
        i += 1

def move_icontools(workspace, dest):
    # Move .nc files
    move_files(os.path.join(workspace, 'icontools', '*.nc'), os.path.join(dest))
    # Move .html files
    move_files(os.path.join(workspace, 'icontools', '*.html'), dest)

def move_zip(destination, zip_file, hash):
    folder = os.path.join(destination, hash)
    # Create the directory
    os.makedirs(folder, exist_ok=True)
    print(f"Created directory {folder}")

    # Move the zip file to the directory
    shutil.move(zip_file, folder)
    print(f"Moved {zip_file} to {folder}")

def create_zip(zip_file_path, source_dir):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Archive artifacts to a unique folder.")

    # Add the arguments
    parser.add_argument('--destination', type=str, required=True, help='The destination folder to store the zip file')
    parser.add_argument('--hash-file', type=str, required=True, help='Hash file')
    parser.add_argument('--workspace', type=str, required=True, help='The workspace folder')

    # Parse the arguments
    args = parser.parse_args()

    with open(args.hash_file, 'r') as f:
        hash = f.read().strip()

    output_dir = os.path.join(args.workspace, 'output')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Move extpar files
    move_extpar(args.workspace, output_dir)

    # Move icontools files
    move_icontools(args.workspace, output_dir)

    # Create a zip file
    zip_file_path = os.path.join(args.workspace, 'output.zip')
    create_zip(zip_file_path, output_dir)

    # Move the zip file to the destination
    move_zip(args.destination, zip_file_path, hash)

if __name__ == "__main__":
    main()
