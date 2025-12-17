import json
import argparse
import os
import logging
import subprocess
from math import sqrt, pow, pi
from output_manager import OutputManager
from zonda_rotgrid.core import create_rotated_grid, create_latlon_grid
from visualize_data import visualize_topography


def run_extpar(config, workspace_path, extpar_raw_data_path, nesting_group, grid_dirs, grid_filenames, extpar_tag, use_apptainer):
    logging.info(f"Call run_extpar with the following arguments:\n"
                 f"workspace_path: {workspace_path}\n"
                 f"extpar_raw_data_path: {extpar_raw_data_path}\n"
                 f"grid_dirs: {grid_dirs}\n"
                 f"grid_filenames: {grid_filenames}\n"
                 f"extpar_tag: {extpar_tag}\n"
                 f"use_apptainer: {use_apptainer}")

    logging.info("Configuration")
    logging.info(config)

    domains_config = config["domains"]

    # Create the EXTPAR directories
    extpar_dirs = []

    try:
        num_threads = os.environ["OMP_NUM_THREADS"]
        logging.info(f"Using {num_threads} OpenMP threads")
    except KeyError:
        num_threads = 1
        logging.warning('OMP_NUM_THREADS not set -> '
                        f'using OMP_NUM_THREADS = {num_threads} instead')

    try:
        netcdf_filetype = os.environ["NETCDF_OUTPUT_FILETYPE"]
        logging.info(f'Using {netcdf_filetype} file format')
    except:
        netcdf_filetype = "NETCDF4"
        logging.warning('NETCDF_OUTPUT_FILETYPE not set -> falling back to NetCDF 4')

    for domain_id in nesting_group:
        domain_idx = domain_id - 1  # TODO: We may have to do this differently to not assume nesting groups are always in order from 1 to n_domains
        domain_config = domains_config[domain_idx]
        extpar_dir = os.path.join(workspace_path, f"extpar_{domain_label(domain_id)}")
        os.makedirs(extpar_dir, exist_ok=True)
        logging.info(f"Processing in {extpar_dir}")

        # Extract the EXTPAR part of the domain and save it as a domain-specific config.json
        domain_extpar_config = {"extpar": domain_config["extpar"]}
        domain_extpar_config_path = os.path.join(extpar_dir, 'config.json')
        with open(domain_extpar_config_path, 'w') as f:
            json.dump(domain_extpar_config, f, indent=4)
        logging.info(f"Domain-specific config.json written to {domain_extpar_config_path}")

        # os.chdir(extpar_dir)  # TODO: Remove this, I don't think it's needed, but it should be checked

        logging.info(f"Running {'apptainer' if use_apptainer else 'podman'} command for extpar in {extpar_dir}")

        if use_apptainer:
            container_cmd = [
                "apptainer", "exec",
                "--env", f"OMP_NUM_THREADS={num_threads}",
                "--env", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                "--bind", f"{extpar_raw_data_path}:/data",
                "--bind", f"{grid_dirs[domain_idx]}:/grid",
                "--bind", f"{extpar_dir}:/work",
                f"{workspace_path}/extpar.sif"
            ]
        else:
            container_cmd = [
                "podman", "run",
                "-e", f"OMP_NUM_THREADS={num_threads}",
                "-e", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                "-v", f"{extpar_raw_data_path}:/data",
                "-v", f"{grid_dirs[domain_idx]}:/grid",
                "-v", f"{extpar_dir}:/work",
                f"extpar:{extpar_tag}"
            ]

        shell_cmd(
            *container_cmd,
            "python3", "-m", "extpar.WrapExtpar",
            "--run-dir", "/work",
            "--raw-data-path", "/data/linked_data",
            "--account", "none",
            "--no-batch-job",
            "--host", "docker",
            "--input-grid", f"/grid/{grid_filenames[domain_idx]}",
            "--extpar-config", "/work/config.json")

        extpar_dirs.append(extpar_dir)

    # os.chdir(workspace_path)  # TODO: Remove this, I don't think it's needed, but it should be checked
    logging.info("Extpar completed")
    return extpar_dirs


def run_icon_gridgen(icontools_dir, namelist_filename, icontools_container_image, use_apptainer):
    logging.info("Running ICON gridgen.")

    if use_apptainer:
        shell_cmd("apptainer", "exec", "--pwd", "/work", "--bind", f"{icontools_dir}:/work", "--env", "LD_LIBRARY_PATH=/home/dwd/software/lib", icontools_container_image, "/home/dwd/icontools/icongridgen", "--nml", f"/work/{namelist_filename}")
    else:
        shell_cmd("podman", "run", "-w", "/work", "-u", "0", "-v", f"{icontools_dir}:/work", "-e", "LD_LIBRARY_PATH=/home/dwd/software/lib", "-t", icontools_container_image, "/home/dwd/icontools/icongridgen", "--nml", f"/work/{namelist_filename}")

    logging.info("Grid generation completed.")


def shell_cmd(bin, *args):
    '''
    wrapper to launch an external programme on the system

    bin is the executable to run
    *args are the arguments for bin, need to be convertable to string
    stdout/stderr of bin is written to logfile
    '''

    #convert *args to string
    arg_list = []
    arg_list.insert(0, str(bin))
    for arg in args:
        if arg:  # Prevents empty strings from being written into list
            arg_list.append(str(arg))

    args_for_logger = ' '.join(arg_list)

    logging.info(f'shell command: {args_for_logger}')
    logging.info('')

    try:
        process = subprocess.run(arg_list,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 check=True,
                                 universal_newlines=True)
        output = process.stdout + process.stderr
    except FileNotFoundError:
        logging.warning(f'Problems with shell command: {args_for_logger} \n'
                        '-> it appears your shell does not know this command')

        logging.error('Shell command failed', exc_info=True)
        raise

    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr
        logging.warning(f'Problems with shell command: {args_for_logger} \n'
                        '-> the output returned to the shell is:')
        logging.warning(f'{output}')

        logging.error('Shell command failed', exc_info=True)
        raise

    logging.info('Output:')
    logging.info(f'{output}')

    return output


def load_config(config_file): # TODO: Maybe put this into an io_utilities file
    logging.info(f"Loading configuration from {config_file}")
    with open(config_file, 'r') as f:
        config = json.load(f)
    logging.info("Configuration loaded successfully")
    return config

def convert_to_fortran_bool(boolean_value):
    return f".{str(boolean_value).upper()}."


def write_gridgen_namelist(config, nesting_group, primary_grid_source, icontools_dir, namelist_filename):
    logging.info("Writing ICON gridgen namelist.")

    basegrid_config = config["basegrid"]
    domains_config = config["domains"]

    # TODO: For primary_grid_source == input_grid the parent_id and domain_id may need to be adapted if the
    #       nesting_group doesn't start from domain_id == 1.
    # Ensure the first domain has parent_id = 0
    if domains_config[0]["icontools"]["parent_id"] != 0:
        domains_config[0]["icontools"]["parent_id"] = 0
        logging.warning("Domain 1 has parent_id not set to 0. Resetting it to 0.")

    # Create parent_id comma-separated list
    # TODO: We may have to do this differently to not assume nesting groups are always in order from 1 to n_domains
    parent_id = ",".join(str(domains_config[domain_id-1]["icontools"]["parent_id"]) for domain_id in nesting_group)

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
    namelist.append(f"  basegrid%grid_root   = {basegrid_config['grid_root']}")
    namelist.append(f"  basegrid%grid_level  = {basegrid_config['grid_level']}")
    namelist.append(f"  basegrid%icopole_lon = {basegrid_config['icopole_lon']}")
    namelist.append(f"  basegrid%icopole_lat = {basegrid_config['icopole_lat']}")
    namelist.append(f"  basegrid%icorotation = {basegrid_config['icorotation']}")
    namelist.append("")

    # Tuning parameters
    namelist.append(f"  lspring_dynamics   = {convert_to_fortran_bool(lspring_dynamics)}")
    namelist.append(f"  maxit              = {maxit}")
    namelist.append(f"  beta_spring        = {beta_spring}")
    namelist.append(f"  bdy_indexing_depth = {basegrid_config.get('bdy_indexing_depth', 14)}")
    namelist.append("")
    
    # Set centre and subcentre
    namelist.append(f"  centre    = {basegrid_config.get('centre', 78)}")
    namelist.append(f"  subcentre = {basegrid_config.get('subcentre', 255)}")
    namelist.append("")

    for domain_id in nesting_group:
        domain_config = domains_config[domain_id-1]  # TODO: We may have to do this differently to not assume nesting groups are always in order from 1 to n_domains
        icontools_config = domain_config["icontools"]

        lwrite_parent = (domain_id == 1)

        namelist.append(f"  dom({domain_id})%outfile             = \"{basegrid_config['outfile']}\" ")
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
    namelist_filepath = os.path.join(icontools_dir, namelist_filename)
    with open(namelist_filepath, "w") as file:
        file.write("\n".join(namelist))
    logging.info(f"Namelist written to \"{namelist_filepath}\".")


def domain_label(domain_id):
    return f"DOM{domain_id:02d}"


def pull_extpar_image(config):
    tag = config['extpar_tag']
    if tag != "latest":
        shell_cmd("podman", "pull", f"docker.io/c2sm/extpar:{tag}")
        logging.info("Pull extpar image completed")
    else:
        logging.info("Using latest extpar tag (it must already be present on the system)")
    return tag


def run_rotgrid(config, workspace_path, nesting_group, grid_filenames):
    logging.info("Creating lat-lon grid")
    basegrid_config = config['basegrid']
    domains_config = config['domains']

    # Ensure the output directory exists
    output_dir = os.path.join(workspace_path, 'output')
    os.makedirs(output_dir, exist_ok=True)

    for domain_id in nesting_group:
        domain_idx = domain_id - 1
        domain_config = domains_config[domain_idx]
        icontools_config = domain_config['icontools']

        # Only rectangular domains are supported
        if icontools_config["region_type"] == 3:

            lrotate = icontools_config.get('lrotate', False)

            center_lat = icontools_config['center_lat']
            center_lon = icontools_config['center_lon']
            hwidth_lat = icontools_config['hwidth_lat']
            hwidth_lon = icontools_config['hwidth_lon']

            n = basegrid_config['grid_root']
            k = basegrid_config['grid_level'] + domain_id
            grid_spacing = compute_resolution_from_rnbk(n, k)

            grid_file_base = grid_filenames[domain_idx].removesuffix('.nc')
            output_filename_suffix = "_rotated" if lrotate else ""
            output_path_full = os.path.join(output_dir, f'{grid_file_base}_latlon{output_filename_suffix}.nc')

            if lrotate:
                pole_lat = icontools_config['pole_lat']
                pole_lon = icontools_config['pole_lon']

                create_rotated_grid( grid_spacing,
                                     center_lat,
                                     center_lon,
                                     hwidth_lat,
                                     hwidth_lon,
                                     pole_lat,
                                     pole_lon,
                                     0,
                                     output_path_full )

                logging.info(f'Rotated lat-lon grid for {domain_label(domain_id)} stored in {output_path_full}')
            else:
                create_latlon_grid( grid_spacing,
                                    center_lat,
                                    center_lon,
                                    hwidth_lat,
                                    hwidth_lon,
                                    0,
                                    output_path_full )

                logging.info(f'Lat-lon grid for {domain_label(domain_id)} stored in {output_path_full}')
        else:
            logging.info(f'{domain_label(domain_id)} is not rectangular (i.e., region_type = 3) -> Skipping generation of lat-lon grid!')


def compute_resolution_from_rnbk(n, k):
    earth_radius = 6371.0
    return earth_radius * sqrt(pi / 5) / (n * pow(2, k))


def create_nesting_groups(config):
    logging.info("Creating nesting groups.")

    domains_config = config["domains"]
    zonda_config = config["zonda"]  # TODO: Remove this in v2.0

    nesting_groups = []
    grid_sources = []

    input_grid_path = zonda_config.get("input_grid_path")  # TODO: Remove this in v2.0

    valid_grid_sources = ["input_grid", "icontools"]  # TODO: Use an Enum or anyway pull them outside

    for domain_config in domains_config:
        domain_id = domain_config["domain_id"]

        if (domain_id == 1) and (input_grid_path is not None):  # TODO: Remove this in v2.0
            grid_sources.append("input_grid")
            continue

        for grid_source in valid_grid_sources:
            if grid_source in domain_config:
                grid_sources.append(grid_source)

                # ATTENTION:
                # The condition below should be added to the if only if more valid grid sources are added, but for now
                # let's assume "input_grid" and "icontools" are the only possible ones.
                # ... and ((grid_sources[-2] == "input_grid") or (grid_sources[-2] == "icontools")):
                if (len(grid_sources) > 1) and (grid_source == "icontools"):  # TODO: Can we make it independent of the grid_source name, i.e. icontools in this case?
                    nesting_groups[-1].append(domain_id)
                else:
                    nesting_groups.append([domain_id])

                break
        else:
            logging.error(f"No valid grid generation method defined in config for domain {domain_id}!")
            raise KeyError(f"Missing one of these entries in JSON config: {valid_grid_sources}!")

    return nesting_groups, grid_sources


def generate_grids(config, workspace_path, nesting_group, grid_sources, use_apptainer):
    logging.info("Generating grid files.")

    zonda_config = config["zonda"]

    primary_grid_source = grid_sources[nesting_group[0]]
    match primary_grid_source:
        case "icontools":
            icontools_dir = os.path.join(workspace_path, "icontools")
            os.makedirs(icontools_dir, exist_ok=True)
            logging.info(f"Created directory: {icontools_dir}")

            if use_apptainer:
                icontools_container_image = os.path.join(workspace_path, "icon_tools.sif")
            else:
                icontools_tag = zonda_config.get("icontools_tag", "latest")
                icontools_container_image = f"execute:{icontools_tag}"

            namelist_filename = "nml_gridgen"
            write_gridgen_namelist(config, nesting_group, primary_grid_source, icontools_dir, namelist_filename)

            run_icon_gridgen(icontools_dir, namelist_filename, icontools_container_image, use_apptainer)

            grid_dirs_nesting_group = [icontools_dir] * len(nesting_group)
            grid_filenames_nesting_group = [
                f"{config['basegrid']['outfile']}_{domain_label(domain_id)}.nc"
                for domain_id in nesting_group
            ]

        case "input_grid":
            if len(nesting_group) == 1:  # TODO: This section will probably need to be adapted for v2.0
                domain_id = nesting_group[0]
                input_grid_path = os.path.abspath(zonda_config.get("input_grid_path"))

                if os.path.isfile(input_grid_path):
                    grid_dirs_nesting_group = [os.path.dirname(input_grid_path)]
                    grid_filenames_nesting_group = [os.path.basename(input_grid_path)]

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

    return grid_dirs_nesting_group, grid_filenames_nesting_group


def main(config_path, workspace_path, extpar_raw_data_path, use_apptainer):

    logging.info( f"Starting main process with\n"
                  f"  config_path: {config_path}\n"
                  f"  workspace_path: {workspace_path}\n"
                  f"  extpar_raw_data_path: {extpar_raw_data_path}\n"
                  f"  use_apptainer: {use_apptainer}" )

    if use_apptainer:
        logging.warning("Apptainer is being used, thus the extpar_tag and icontools_tag entries in the config file are ignored!")

    config = load_config(config_path)
    zonda_config = config["zonda"]
    outfile = config["basegrid"]["outfile"]

    output_manager = OutputManager(workspace_path, outfile)

    nesting_groups, grid_sources = create_nesting_groups(config)

    grid_dirs = []
    grid_filenames = []
    extpar_dirs = []
    for nesting_group in nesting_groups:
        grid_dirs_nesting_group, grid_filenames_nesting_group = generate_grids(config, workspace_path, nesting_group, grid_sources, use_apptainer)

        grid_dirs += grid_dirs_nesting_group
        grid_filenames += grid_filenames_nesting_group

        extpar_tag = zonda_config["extpar_tag"] if use_apptainer else pull_extpar_image(zonda_config)

        extpar_dirs += run_extpar(config, workspace_path, extpar_raw_data_path, nesting_group, grid_dirs, grid_filenames, extpar_tag, use_apptainer)

        primary_grid_source = grid_sources[nesting_group[0]]
        if primary_grid_source == "icontools":
            keep_basegrid_files = config["basegrid"]["keep_basegrid_files"]

            try:
                run_rotgrid(config, workspace_path, nesting_group, grid_filenames)
            except Exception as e:
                logging.warning("An error occurred during the generation of the rotated lat-lon grid.\n"
                                f"{repr(e)}\n"
                                "Skipping generation of rotated lat-lon grid!")

            try:
                for domain_id in nesting_group:
                    domain_idx = domain_id - 1
                    domain_config = config["domains"][domain_idx]

                    grid_filepath = os.path.join(grid_dirs[domain_idx], grid_filenames[domain_idx])
                    extpar_filepath = os.path.join(extpar_dirs[domain_idx], "external_parameter.nc")

                    icontools_config = domain_config["icontools"]

                    visualize_topography(icontools_config, workspace_path, grid_filepath, extpar_filepath, extpar_dirs[domain_idx])
            except Exception as e:
                logging.warning("An error occurred during the visualization of topography data.\n"
                                f"{repr(e)}\n"
                                "Skipping the visualization!")
        else:
            keep_basegrid_files = False  # Likely no basegrid files if the grid is provided by the user

            logging.warning("An input grid was provided. Skipping generation of rotated lat-lon grid and visualization of topography!")

        output_manager.move_output(extpar_dirs, keep_basegrid_files)

    output_manager.zip_output()

    logging.info("Process completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser.add_argument('--workspace', type=str, required=True, help="Path to the workspace directory")
    parser.add_argument('--extpar-raw-data', type=str, required=True, help="Path to the EXTPAR raw input data")
    parser.add_argument('--logfile', type=str, help="Path to the log file")
    parser.add_argument('--apptainer', action=argparse.BooleanOptionalAction, default=False, help="Use apptainer instead of podman to run containers")

    args = parser.parse_args()

    logger_format = "%(asctime)s - %(levelname)s - %(message)s"
    if args.logfile:
        logging.basicConfig(filename=args.logfile, filemode='w', format=logger_format, level=logging.INFO)
    else:
        logging.basicConfig(format=logger_format, level=logging.INFO)

    config_path = os.path.abspath(args.config)
    workspace_path = os.path.abspath(args.workspace)
    extpar_raw_data_path = os.path.abspath(args.extpar_raw_data)

    use_apptainer = args.apptainer

    main(config_path, workspace_path, extpar_raw_data_path, use_apptainer)
