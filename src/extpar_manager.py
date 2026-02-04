import os
import logging
import json
from utilities import shell_command, domain_label, LOG_INDENTATION_STR



class ExtparManager:

    def __init__(self, config, workspace_path, extpar_raw_data_path, use_apptainer=False):
        self.config = config
        self.workspace_path = workspace_path
        self.extpar_raw_data_path = extpar_raw_data_path

        self.use_apptainer = use_apptainer

        self.domains_config = self.config["domains"]

        self.extpar_config_filename = "extpar_config.json"

        self.extpar_dirs = []
        for domain_config in self.domains_config:
            extpar_dir = self.setup_extpar_dir(domain_config, logging_indentation_level=1)
            self.extpar_dirs.append(extpar_dir)

        if self.use_apptainer:
            self.extpar_container_image = os.path.join(self.workspace_path, "extpar.sif")
        else:
            extpar_tag = self.config["zonda"].get("extpar_tag", "latest")
            self.pull_extpar_image(extpar_tag)
            self.extpar_container_image = f"extpar:{extpar_tag}"


    def pull_extpar_image(self, extpar_tag, logging_indentation_level=0):
        if extpar_tag != "latest":
            logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Pull EXTPAR image.")
            shell_command("podman", "pull", f"docker.io/c2sm/extpar:{extpar_tag}", logging_indentation_level=logging_indentation_level+1)
        else:
            logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Using latest EXTPAR tag (it must already be present on the system).")


    def setup_extpar_dir(self, domain_config, logging_indentation_level=0):
        domain_id = domain_config["domain_id"]

        extpar_dir = os.path.join(self.workspace_path, f"extpar_{domain_label(domain_id)}")

        os.makedirs(extpar_dir, exist_ok=True)
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Created directory \"{extpar_dir}\".")

        extpar_config = {"extpar": domain_config["extpar"]}
        extpar_config_filepath = os.path.join(extpar_dir, self.extpar_config_filename)
        with open(extpar_config_filepath, "w") as file:
            json.dump(extpar_config, file, indent=4)
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Domain-specific {self.extpar_config_filename} written to \"{extpar_config_filepath}\".")

        return extpar_dir


    def run_extpar(self, nesting_group, grid_dirs, grid_filenames, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Run EXTPAR.")

        try:
            num_threads = os.environ["OMP_NUM_THREADS"]
            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)} Using {num_threads} OpenMP threads.")
        except KeyError:
            num_threads = 1
            logging.warning("OMP_NUM_THREADS not set -> using OMP_NUM_THREADS = {num_threads} instead.")

        try:
            netcdf_filetype = os.environ["NETCDF_OUTPUT_FILETYPE"]
            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)} Using {netcdf_filetype} file format.")
        except KeyError:
            netcdf_filetype = "NETCDF4"
            logging.warning("NETCDF_OUTPUT_FILETYPE not set -> falling back to NetCDF 4.")

        for domain_id in nesting_group:
            domain_idx = domain_id - 1

            extpar_dir = self.extpar_dirs[domain_idx]

            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)} Running {'apptainer' if self.use_apptainer else 'podman'} command for EXTPAR in {extpar_dir}.")

            if self.use_apptainer:
                container_cmd = [
                    "apptainer", "exec",
                    "--env", f"OMP_NUM_THREADS={num_threads}",
                    "--env", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                    "--bind", f"{self.extpar_raw_data_path}:/data",
                    "--bind", f"{grid_dirs[domain_idx]}:/grid",
                    "--bind", f"{extpar_dir}:/work",
                    self.extpar_container_image
                ]
            else:
                container_cmd = [
                    "podman", "run",
                    "-e", f"OMP_NUM_THREADS={num_threads}",
                    "-e", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                    "-v", f"{self.extpar_raw_data_path}:/data",
                    "-v", f"{grid_dirs[domain_idx]}:/grid",
                    "-v", f"{extpar_dir}:/work",
                    self.extpar_container_image
                ]

            shell_command(
                *container_cmd,
                "python3", "-m", "extpar.WrapExtpar",
                "--run-dir", "/work",
                "--raw-data-path", "/data/linked_data",
                "--account", "none",
                "--no-batch-job",
                "--host", "docker",
                "--input-grid", f"/grid/{grid_filenames[domain_idx]}",
                "--extpar-config", f"/work/{self.extpar_config_filename}",
                logging_indentation_level=logging_indentation_level+2
            )
