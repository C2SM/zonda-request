import os
import argparse
import shutil
import glob
import zipfile

def copy_files(src_pattern, dest_dir, prefix=""):
    for file in glob.glob(src_pattern):
        dest_file = os.path.join(dest_dir, prefix + os.path.basename(file))
        print(f"Copying {file} to {dest_file}")
        shutil.copy(file, dest_file)

def copy_extpar(workspace, dest):
    i = 1
    for domain in sorted(glob.glob(os.path.join(workspace, 'extpar_*'))):
        # Copy logfiles
        copy_files(os.path.join(domain, "*.log"), os.path.join(dest,'logs'), f"DOM_{i}_")
        # Copy external parameter file
        copy_files(os.path.join(domain, "external_parameter*.nc"), dest, f"DOM_{i}_")
        i += 1

        
def copy_icontools(workspace, dest):
    # Copy .nc files
    copy_files(os.path.join(workspace, 'icontools', '*.nc'), os.path.join(dest))
     # Copy .html files
    copy_files(os.path.join(workspace, 'icontools', '*.html'), dest)

def copy_zip(destination, zip_file, hash):
    folder = os.path.join(destination, hash)
    # Create the directory
    os.makedirs(folder, exist_ok=True)
    print(f"Created directory {folder}")

    # Copy the zip file to the directory
    shutil.copy(zip_file, folder)
    print(f"Copied {zip_file} to {folder}")

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
        hash = f.read()

    # Copy icontools and extpar files to the output directory
    output_dir = os.path.join(args.workspace, 'output')
    copy_icontools(args.workspace, output_dir)
    copy_extpar(args.workspace, output_dir)

    # Create a zip file
    zip_file = os.path.join(args.workspace, 'output.zip')
    create_zip(zip_file, output_dir)
    copy_zip(args.destination, zip_file, hash)

if __name__ == '__main__':
    main()
