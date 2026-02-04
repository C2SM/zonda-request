import os
import shutil
import glob
import zipfile
import logging
from utilities import domain_label, LOG_INDENTATION_STR


class OutputManager:

    def __init__( self, config, workspace_path, config_filename, zonda_log_filename,
                  output_dirname="output",
                  data_dirname="data",
                  visualizations_dirname="visualizations",
                  logs_dirname="logs",
                  namelists_dirname="namelists",
                  zip_file_prefix="zonda_output_" ):

        self.config = config
        self.workspace_path = workspace_path
        self.config_filename = config_filename
        self.zonda_log_filename = zonda_log_filename

        self.outfile = self.config["basegrid"]["outfile"]
        self.domains_config = self.config["domains"]

        self.visualizations_dirname = visualizations_dirname

        self.output_dir = os.path.join(self.workspace_path, output_dirname)
        self.data_dir = os.path.join(self.output_dir, data_dirname)
        self.logs_dir = os.path.join(self.output_dir, logs_dirname)
        self.namelists_dir = os.path.join(self.output_dir, namelists_dirname)

        self.zip_filepath = os.path.join(self.workspace_path, f"{zip_file_prefix}{self.outfile}.zip")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.namelists_dir, exist_ok=True)

        for domain_config in self.domains_config:
            domain_id = domain_config["domain_id"]

            data_domain_dir = os.path.join(self.data_dir, domain_label(domain_id))
            logs_domain_dir = os.path.join(self.logs_dir, domain_label(domain_id))
            namelists_domain_dir = os.path.join(self.namelists_dir, domain_label(domain_id))
            
            os.makedirs(data_domain_dir, exist_ok=True)
            os.makedirs(os.path.join(data_domain_dir, self.visualizations_dirname), exist_ok=True)

            os.makedirs(logs_domain_dir, exist_ok=True)
            os.makedirs(namelists_domain_dir, exist_ok=True)


    def move_files(self, source_dir_pattern, destination_dir, prefix="", suffix="", blacklist={}, copy=False, logging_indentation_level=0):
        for source_file in glob.glob(source_dir_pattern):
            if os.path.basename(source_file) in blacklist:
                logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Skipping {source_file} because it's blacklisted.")
                continue

            filename = os.path.basename(source_file)
            is_hidden_file = filename.startswith(".")
            tmp = filename.split(".", 2 if is_hidden_file else 1)
            if is_hidden_file:
                tmp.pop(0)

            destination_filename = f"{"." if is_hidden_file else ""}{prefix}{tmp[0]}{suffix}"
            if len(tmp) >= 2:
                destination_filename += f".{tmp[1]}"

            destination_filepath = os.path.join(destination_dir, destination_filename)

            if copy:
                logging.info( f"{LOG_INDENTATION_STR*logging_indentation_level}Copy {source_file}\n"
                              f"{" " * len(LOG_INDENTATION_STR*logging_indentation_level)}  to {destination_filepath}." )
                shutil.copy(source_file, destination_filepath)
            else:
                logging.info( f"{LOG_INDENTATION_STR*logging_indentation_level}Move {source_file}\n"
                              f"{" " * len(LOG_INDENTATION_STR*logging_indentation_level)}  to {destination_filepath}." )
                shutil.move(source_file, destination_filepath)


    def move_icontools_output(self, grid_manager, keep_basegrid_files, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Move ICON Tools output.")

        if keep_basegrid_files:
            self.move_files(os.path.join(grid_manager.icontools_dir, "base_grid.*"), self.data_dir, logging_indentation_level=logging_indentation_level+1)

        for domain_config in self.domains_config:
            domain_id = domain_config["domain_id"]

            current_domain_label = domain_label(domain_id)

            data_domain_dir = os.path.join(self.data_dir, current_domain_label)
            self.move_files(os.path.join(grid_manager.icontools_dir, f"*{current_domain_label}*.nc"), data_domain_dir, logging_indentation_level=logging_indentation_level+1)

            visualizations_dir = os.path.join(data_domain_dir, self.visualizations_dirname)
            self.move_files(os.path.join(grid_manager.icontools_dir, f"*{current_domain_label}*.html"), visualizations_dir, logging_indentation_level=logging_indentation_level+1)

        self.move_files(os.path.join(grid_manager.icontools_dir, grid_manager.namelist_filename), self.namelists_dir, logging_indentation_level=logging_indentation_level+1)


    def move_extpar_output(self, extpar_manager, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Move EXTPAR output.")

        for domain_idx, extpar_dir in enumerate(extpar_manager.extpar_dirs):

            current_domain_label = domain_label(domain_idx+1)

            data_domain_dir = os.path.join(self.data_dir, current_domain_label)
            self.move_files(os.path.join(extpar_dir, "external_parameter.nc"), data_domain_dir, prefix=f"{self.outfile}_{current_domain_label}_", logging_indentation_level=logging_indentation_level+1)

            visualizations_dir = os.path.join(data_domain_dir, self.visualizations_dirname)
            self.move_files(os.path.join(extpar_dir, "*.png"), visualizations_dir, prefix=f"{self.outfile}_{current_domain_label}_", logging_indentation_level=logging_indentation_level+1)

            logs_domain_dir = os.path.join(self.logs_dir, current_domain_label)
            self.move_files(os.path.join(extpar_dir, "*.log"), logs_domain_dir, logging_indentation_level=logging_indentation_level+1)

            namelists_domain_dir = os.path.join(self.namelists_dir, current_domain_label)
            self.move_files(os.path.join(extpar_dir, "INPUT_*"), namelists_domain_dir, logging_indentation_level=logging_indentation_level+1)
            self.move_files(os.path.join(extpar_dir, "namelist.py"), namelists_domain_dir, logging_indentation_level=logging_indentation_level+1)
            self.move_files(os.path.join(extpar_dir, extpar_manager.extpar_config_filename), namelists_domain_dir, logging_indentation_level=logging_indentation_level+1)


    def move_zonda_files(self, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Move Zonda files.")

        self.move_files(os.path.join(self.workspace_path, self.config_filename), self.output_dir, copy=True, logging_indentation_level=logging_indentation_level+1)
        self.move_files(os.path.join(self.workspace_path, self.zonda_log_filename), self.logs_dir, copy=True, logging_indentation_level=logging_indentation_level+1)


    def move_output(self, grid_manager, extpar_manager, keep_basegrid_files, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Move output.")

        self.move_icontools_output(grid_manager, keep_basegrid_files, logging_indentation_level=logging_indentation_level+1)
        self.move_extpar_output(extpar_manager, logging_indentation_level=logging_indentation_level+1)


    def zip_output(self, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Create zip file (no compression): \"{self.zip_filepath}\".")

        with zipfile.ZipFile(self.zip_filepath, 'w', zipfile.ZIP_STORED) as zip_file:
            for root, _, filenames in os.walk(self.output_dir):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    archive_filepath = os.path.relpath(filepath, self.output_dir)
                    zip_file.write(filepath, archive_filepath)

