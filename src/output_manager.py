import os
import shutil
import glob
import zipfile
import logging
from utilities import domain_label


class OutputManager:

    def __init__(self, config, workspace_path, output_dirname="output", logs_dirname="logs", namelists_dirname="namelists", zip_file_prefix="zonda_output_"):
        self.config = config
        self.workspace_path = workspace_path
        self.outfile = self.config["basegrid"]["outfile"]

        self.output_dir = os.path.join(self.workspace_path, output_dirname)
        self.logs_dir = os.path.join(self.output_dir, logs_dirname)
        self.namelists_dir = os.path.join(self.output_dir, namelists_dirname)

        self.zip_filepath = os.path.join(self.workspace_path, f"{zip_file_prefix}{self.outfile}.zip")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.namelists_dir, exist_ok=True)


    def move_files(self, source_dir_pattern, destination_dir, prefix="", suffix="", blacklist={}):
        for source_file in glob.glob(source_dir_pattern):
            if os.path.basename(source_file) in blacklist:
                logging.info(f"Skipping {source_file}.")
                continue

            filename = os.path.basename(source_file)
            is_hidden_file = filename.startswith(".")
            tmp = filename.split(".", 2 if is_hidden_file else 1)
            destination_filename = f"{"." if is_hidden_file else ""}{prefix}{tmp[0+is_hidden_file]}{suffix}.{tmp[1+is_hidden_file]}"

            destination_filepath = os.path.join(destination_dir, destination_filename)

            logging.info(f"Move {source_file} to {destination_filepath}.")
            shutil.move(source_file, destination_filepath)


    def move_icontools_output(self, icontools_dir, keep_basegrid_files):
        blacklist = {} if keep_basegrid_files else {"base_grid.nc", "base_grid.html"}

        self.move_files(os.path.join(icontools_dir, "*.nc"), self.output_dir, blacklist=blacklist)  # TODO: Separate icontools folder per nesting group
        self.move_files(os.path.join(icontools_dir, "*.html"), self.output_dir, blacklist=blacklist)
        self.move_files(os.path.join(icontools_dir, "nml_gridgen"), self.namelists_dir)  # TODO: The name of the namelist file is actually set in GridManager, so this should be passed or this function placed in GridManager. Maybe have GridManager and ExtparManager provide a list of output, logs, namelists files (or file patterns) bundled in a dictionary and then pass them to move_output, which simply moves them to the right location.


    def move_extpar_output(self, extpar_dirs):
        for i, exptar_dir in enumerate(extpar_dirs):

            # TODO: Create subfolders for the different domains also for logs and normal output (keep the domain label suffix?).
            #       Create them in the __init__ method if possible.
            self.move_files(os.path.join(exptar_dir, "external_parameter.nc"), self.output_dir, prefix=f"{self.outfile}_{domain_label(i+1)}_")
            self.move_files(os.path.join(exptar_dir, "topography.png"), self.output_dir, prefix=f"{self.outfile}_{domain_label(i+1)}_")

            self.move_files(os.path.join(exptar_dir, "*.log"), self.logs_dir, prefix=f"{domain_label(i+1)}_")

            domain_dir = os.path.join(self.namelists_dir, domain_label(i+1))
            os.makedirs(os.path.join(domain_dir), exist_ok=True)  # TODO: Actually create the extpar_dirs and the icontools dir in the __init__ method here instead of just before running EXTPAR and icontools
            self.move_files(os.path.join(exptar_dir, "INPUT_*"), domain_dir)
            self.move_files(os.path.join(exptar_dir, "namelist.py"), domain_dir)
            self.move_files(os.path.join(exptar_dir, "extpar-config.json"), domain_dir)


    def move_output(self, icontools_dir, extpar_dirs, keep_basegrid_files):  # TODO: we could put extpar_dirs and keep_basegrid_files in __init__ so move_output doesn't require any args
        self.move_icontools_output(icontools_dir, keep_basegrid_files)
        self.move_extpar_output(extpar_dirs)


    def zip_output(self):
        logging.info(f"Creating zip file {self.zip_filepath}.")

        with zipfile.ZipFile(self.zip_filepath, 'w', zipfile.ZIP_STORED) as zip_file:
            for root, _, filenames in os.walk(self.output_dir):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    archive_filepath = os.path.relpath(filepath, self.output_dir)
                    zip_file.write(filepath, archive_filepath)

        logging.info(f"Output zip file created at {self.zip_filepath}.")

