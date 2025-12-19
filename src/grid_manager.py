import os
import logging
from zonda_rotgrid.core import create_rotated_grid, create_latlon_grid
from utilities import shell_command, convert_to_fortran_bool, domain_label, compute_resolution_from_rnbk



class GridManager:

    def __init__(self, config, workspace_path, output_manager, namelist_filename="nml_gridgen", use_apptainer=False):
        self.config = config
        self.workspace_path = workspace_path
        self.output_manager = output_manager

        self.namelist_filename = namelist_filename
        self.use_apptainer = use_apptainer

        self.zonda_config = self.config["zonda"]
        self.basegrid_config = self.config["basegrid"]
        self.domains_config = self.config["domains"]

        n_domains = len(self.domains_config)
        self.grid_dirs = [None] * n_domains 
        self.grid_filenames = [None] * n_domains 

        self.icontools_dir = os.path.join(self.workspace_path, "icontools")
        for domain_config in self.domains_config:
            if "icontools" in domain_config:
                os.makedirs(self.icontools_dir, exist_ok=True)
                logging.info(f"Created directory \"{self.icontools_dir}\".")
                break

        self.namelist_filepath = os.path.join(self.icontools_dir, self.namelist_filename)

        if self.use_apptainer:
            self.icontools_container_image = os.path.join(self.workspace_path, "icon_tools.sif")
        else:
            icontools_tag = self.zonda_config.get("icontools_tag", "latest")
            self.icontools_container_image = f"execute:{icontools_tag}"

    def write_icon_gridgen_namelist(self, nesting_group, primary_grid_source):
        logging.info("Writing ICON gridgen namelist.")

        # TODO: For primary_grid_source == input_grid the parent_id and domain_id may need to be adapted if the
        #       nesting_group doesn't start from domain_id == 1.
        # Ensure the first domain has parent_id = 0
        if self.domains_config[0]["icontools"]["parent_id"] != 0:
            self.domains_config[0]["icontools"]["parent_id"] = 0
            logging.warning("Domain 1 has parent_id not set to 0. Resetting it to 0.")

        # Create parent_id comma-separated list
        parent_id = ",".join(str(self.domains_config[domain_id-1]["icontools"]["parent_id"]) for domain_id in nesting_group)

        # Set hardcoded entries
        initial_refinement = True
        lspring_dynamics = True
        maxit = 2000
        beta_spring = 0.9

        # TODO: Move the Zonda parameters on the frontend to the top and add keep_basegrid_files and outfile there.
        #       Maybe rename outfile to request_name.

        # Create the ICON gridgen namelist content
        namelist = []

        namelist.append("&gridgen_nml")
        namelist.append(f"  parent_id          = {parent_id}            ! This list defines parent-nest relations")
        namelist.append(f"  initial_refinement = {convert_to_fortran_bool(initial_refinement)}")
        namelist.append("")

        # Base grid settings
        namelist.append(f"  basegrid%grid_root   = {self.basegrid_config['grid_root']}")
        namelist.append(f"  basegrid%grid_level  = {self.basegrid_config['grid_level']}")
        namelist.append(f"  basegrid%icopole_lon = {self.basegrid_config['icopole_lon']}")
        namelist.append(f"  basegrid%icopole_lat = {self.basegrid_config['icopole_lat']}")
        namelist.append(f"  basegrid%icorotation = {self.basegrid_config['icorotation']}")
        namelist.append("")

        # Tuning parameters
        namelist.append(f"  lspring_dynamics   = {convert_to_fortran_bool(lspring_dynamics)}")
        namelist.append(f"  maxit              = {maxit}")
        namelist.append(f"  beta_spring        = {beta_spring}")
        namelist.append(f"  bdy_indexing_depth = {self.basegrid_config.get('bdy_indexing_depth', 14)}")
        namelist.append("")
        
        # Set centre and subcentre
        namelist.append(f"  centre    = {self.basegrid_config.get('centre', 78)}")
        namelist.append(f"  subcentre = {self.basegrid_config.get('subcentre', 255)}")
        namelist.append("")

        for domain_id in nesting_group:
            icontools_config = self.domain_config["icontools"]

            lwrite_parent = (domain_id == 1)

            namelist.append(f"  dom({domain_id})%outfile             = \"{self.basegrid_config['outfile']}\" ")
            namelist.append(f"  dom({domain_id})%lwrite_parent       = {convert_to_fortran_bool(lwrite_parent)}")
            namelist.append(f"  dom({domain_id})%region_type         = {icontools_config['region_type']}")
            namelist.append(f"  dom({domain_id})%number_of_grid_used = {icontools_config.get('number_of_grid_used', 0)}")
            namelist.append("")

            # Circular domain
            if icontools_config["region_type"] == 2:
                namelist.append(f"  dom({domain_id})%center_lon = {icontools_config['center_lon']}")
                namelist.append(f"  dom({domain_id})%center_lat = {icontools_config['center_lat']}")
                namelist.append(f"  dom({domain_id})%radius     = {icontools_config['radius']}")
                namelist.append("")

            # Regional domain
            elif icontools_config["region_type"] == 3:
                namelist.append(f"  dom({domain_id})%center_lon = {icontools_config['center_lon']}")
                namelist.append(f"  dom({domain_id})%center_lat = {icontools_config['center_lat']}")
                namelist.append(f"  dom({domain_id})%hwidth_lon = {icontools_config['hwidth_lon']}")
                namelist.append(f"  dom({domain_id})%hwidth_lat = {icontools_config['hwidth_lat']}")
                namelist.append("")

                namelist.append(f"  dom({domain_id})%lrotate  = {convert_to_fortran_bool(icontools_config['lrotate'])}")
                namelist.append(f"  dom({domain_id})%pole_lon = {icontools_config.get('pole_lon', -180.0)}")
                namelist.append(f"  dom({domain_id})%pole_lat = {icontools_config.get('pole_lat', 90.0)}")
                namelist.append("")

        namelist.append("/")
        namelist.append("")

        # Write the namelist content to a file
        with open(self.namelist_filepath, "w") as file:
            file.write("\n".join(namelist))
        logging.info(f"Namelist written to \"{self.namelist_filepath}\".")


    def run_icon_gridgen(self):
        logging.info("Running ICON gridgen.")

        if self.use_apptainer:
            container_cmd = [
                "apptainer", "exec",
                "--pwd", "/work",
                "--bind", f"{self.icontools_dir}:/work",
                "--env", "LD_LIBRARY_PATH=/home/dwd/software/lib",
                self.icontools_container_image
            ]
        else:
            container_cmd = [
                "podman", "run",
                "-w", "/work",
                "-u", "0",
                "-v", f"{self.icontools_dir}:/work",
                "-e", "LD_LIBRARY_PATH=/home/dwd/software/lib",
                "-t", self.icontools_container_image
            ]

        shell_command(
            *container_cmd,
            "/home/dwd/icontools/icongridgen",
            "--nml", f"/work/{self.namelist_filename}"
        )

        logging.info("Grid generation completed.")


    def generate_icon_grids(self, nesting_group, grid_sources):
        logging.info("Generating ICON grids.")

        primary_grid_source = grid_sources[nesting_group[0]]
        match primary_grid_source:

            case "icontools":
                self.write_gridgen_namelist(nesting_group, primary_grid_source)

                self.run_icon_gridgen()

                for domain_id in nesting_group:
                    domain_idx = domain_id - 1

                    self.grid_dirs[domain_idx] = self.icontools_dir
                    self.grid_filenames[domain_idx] = f"{self.output_manager.outfile}_{domain_label(domain_id)}.nc"

            case "input_grid":
                if len(nesting_group) == 1:  # TODO: This section will probably need to be adapted for v2.0
                    domain_id = nesting_group[0]
                    domain_idx = domain_id - 1
                    input_grid_path = os.path.abspath(self.zonda_config.get("input_grid_path"))

                    if os.path.isfile(input_grid_path):
                        self.grid_dirs[domain_idx] = os.path.dirname(input_grid_path)
                        self.grid_filenames[domain_idx] = os.path.basename(input_grid_path)

                        logging.info( f"An input grid was provided for domain {domain_id} at \"{input_grid_path}\" "
                                      f"and the generation of additional nests was not requested, thus the grid "
                                      f"generation step is skipped for domain {domain_id}!\n"
                                      f"For this reason the \"basegrid\", \"icontools\", and \"icontools_tag\" entries "
                                      f"in the JSON config are ignored." )
                    else:
                        logging.error( f"The provided input grid does not exist: \"{input_grid_path}\". "
                                       f"Please provide the correct path." )
                        raise FileNotFoundError(f"\"{input_grid_path}\" not found!")
                else:
                    pass # TODO: Add this in v2.0; Pass input grid to icontools to add nests

            case _:
                logging.error("No valid grid generation method could be selected!")


    def generate_latlon_grids(self, nesting_group):
        logging.info("Generating lat-lon grids.")

        for domain_id in nesting_group:
            domain_idx = domain_id - 1
            domain_config = self.domains_config[domain_idx]
            icontools_config = domain_config["icontools"]

            # Only rectangular domains are supported
            if icontools_config["region_type"] == 3:
                lrotate = icontools_config.get("lrotate", False)

                center_lat = icontools_config["center_lat"]
                center_lon = icontools_config["center_lon"]
                hwidth_lat = icontools_config["hwidth_lat"]
                hwidth_lon = icontools_config["hwidth_lon"]

                n = self.basegrid_config["grid_root"]
                k = self.basegrid_config["grid_level"] + domain_id
                grid_spacing = compute_resolution_from_rnbk(n, k)

                grid_filename_base = self.grid_filenames[domain_idx].removesuffix(".nc")
                latlon_grid_filename_suffix = "_rotated" if lrotate else ""
                latlon_grid_filepath = os.path.join(self.output_manager.output_dir, f"{grid_filename_base}_latlon{latlon_grid_filename_suffix}.nc")

                if lrotate:
                    pole_lat = icontools_config["pole_lat"]
                    pole_lon = icontools_config["pole_lon"]

                    create_rotated_grid( grid_spacing,
                                         center_lat,
                                         center_lon,
                                         hwidth_lat,
                                         hwidth_lon,
                                         pole_lat,
                                         pole_lon,
                                         0,
                                         latlon_grid_filepath )

                    logging.info(f"Rotated lat-lon grid for domain {domain_id} stored in \"{latlon_grid_filepath}\".")
                else:
                    create_latlon_grid( grid_spacing,
                                        center_lat,
                                        center_lon,
                                        hwidth_lat,
                                        hwidth_lon,
                                        0,
                                        latlon_grid_filepath )

                    logging.info(f"Lat-lon grid for domain {domain_id} stored in \"{latlon_grid_filepath}\".")
            else:
                logging.info( f"Domain {domain_id} is not rectangular (i.e., region_type = 3).\n"
                              "Skipping generation of lat-lon grid!" )