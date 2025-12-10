import json
import argparse
import os
import shutil
import logging
import subprocess
import glob
import zipfile
from math import sqrt, pow, pi
from zonda_rotgrid.core import create_rotated_grid, create_latlon_grid
from visualize_data import visualize_topography

def move_files(src_pattern, dest_dir, prefix="",blacklist={}):
    for file in glob.glob(src_pattern):
        if os.path.basename(file) in blacklist:
            logging.info(f"Skipping {file}")
            continue
        dest_file = os.path.join(dest_dir, prefix + os.path.basename(file))
        logging.info(f"Move {file} to {dest_file}")
        shutil.move(file, dest_file)


def move_extpar(output_dir, namelist_dir, grid_files, extpar_dirs):
    for i, exptar_dir in enumerate(extpar_dirs):
        # Move logfiles
        move_files(os.path.join(exptar_dir, "*.log"), os.path.join(output_dir, 'logs'), f"{dom_id_to_str(i)}_")
        # Move external parameter files
        grid_file_base = os.path.splitext(grid_files[i])[0]  # Drop the suffix ".nc"
        move_files(os.path.join(exptar_dir, "external_parameter.nc"), output_dir, f"{grid_file_base}_")
        move_files(os.path.join(exptar_dir, "topography.png"), output_dir, f"{grid_file_base}_")
        # Create directories for each domain
        domain_dir = os.path.join(namelist_dir, dom_id_to_str(i))
        os.makedirs(os.path.join(domain_dir), exist_ok=True)
        move_files(os.path.join(exptar_dir, "INPUT_*"), domain_dir)
        move_files(os.path.join(exptar_dir, "namelist.py"), domain_dir)
        move_files(os.path.join(exptar_dir, "config.json"), domain_dir)


def move_icontools(workspace, output_dir, namelist_dir, keep_base_grid):
    # too big for high-res grids
    blacklist = {} if keep_base_grid else {'base_grid.nc', 'base_grid.html'}
    # Move .nc files
    move_files(os.path.join(workspace, 'icontools', '*.nc'), os.path.join(output_dir), blacklist=blacklist)
    # Move .html files
    move_files(os.path.join(workspace, 'icontools', '*.html'), output_dir, blacklist=blacklist)
    # Move namelist file
    move_files(os.path.join(workspace, 'icontools', 'nml_gridgen'), namelist_dir)


def create_zip(zip_file_path, source_dir):
    logging.info(f"Creating zip file {zip_file_path}")
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)


def move_output(workspace, grid_files, extpar_dirs, outfile, keep_base_grid, icontools_active):
    logging.info(f"move_output called with workspace: {workspace}, grid_files: {grid_files}, extpar_dirs: {extpar_dirs}, outfile: {outfile}, keep_base_grid: {keep_base_grid}, icontools_active: {icontools_active}")
    
    output_dir = os.path.join(workspace, 'output')
    log_dir = os.path.join(output_dir, 'logs')
    namelist_dir = os.path.join(output_dir, 'namelists')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(namelist_dir, exist_ok=True)

    # Move extpar files
    move_extpar(output_dir, namelist_dir, grid_files, extpar_dirs)

    # Move icontools files
    if icontools_active:
        move_icontools(workspace, output_dir, namelist_dir, keep_base_grid)

    # Create a zip file
    zip_file_path = os.path.join(workspace, f"zonda_output_{outfile}.zip")
    create_zip(zip_file_path, output_dir)
    logging.info(f"Output zip file created at {zip_file_path}")


def run_extpar(workspace, config_path, extpar_rawdata_path, grid_files, grid_dir, extpar_tag, use_apptainer):
    logging.info(f"Call run_extpar with the following arguments:\n"
                 f"workspace: {workspace}\n"
                 f"config_path: {config_path}\n"
                 f"extpar_rawdata_path: {extpar_rawdata_path}\n"
                 f"grid_files: {grid_files}\n"
                 f"grid_dir: {grid_dir}\n"
                 f"extpar_tag: {extpar_tag}\n"
                 f"use_apptainer: {use_apptainer}")
    # Create the EXTPAR directories
    extpar_dirs = []
    config = load_config(config_path)
    logging.info("Configuration loaded")
    logging.info(config)

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

    for i, domain in enumerate(config["domains"]):
        extpar_dir = os.path.join(workspace, f"extpar_{dom_id_to_str(i)}")
        os.makedirs(extpar_dir, exist_ok=True)
        logging.info(f"Processing in {extpar_dir}")

        # Extract the EXTPAR part of the domain and save it as a domain-specific config.json
        domain_extpar_config = {"extpar": domain["extpar"]}
        domain_config_path = os.path.join(extpar_dir, 'config.json')
        with open(domain_config_path, 'w') as f:
            json.dump(domain_extpar_config, f, indent=4)
        logging.info(f"Domain-specific config.json written to {domain_config_path}")

        os.chdir(extpar_dir)

        logging.info(f"Running {'apptainer' if use_apptainer else 'podman'} command for extpar in {extpar_dir}")

        if use_apptainer:
            container_cmd = [
                "apptainer", "exec",
                "--env", f"OMP_NUM_THREADS={num_threads}",
                "--env", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                "--bind", f"{extpar_rawdata_path}:/data",
                "--bind", f"{grid_dir}:/grid",
                "--bind", f"{extpar_dir}:/work",
                f"{workspace}/extpar.sif"
            ]
        else:
            container_cmd = [
                "podman", "run",
                "-e", f"OMP_NUM_THREADS={num_threads}",
                "-e", f"NETCDF_OUTPUT_FILETYPE={netcdf_filetype}",
                "-v", f"{extpar_rawdata_path}:/data",
                "-v", f"{grid_dir}:/grid",
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
            "--input-grid", f"/grid/{grid_files[i]}",
            "--extpar-config", "/work/config.json")

        extpar_dirs.append(extpar_dir)

    os.chdir(workspace)
    logging.info("Extpar completed")
    return extpar_dirs


def run_gridgen(workspace, icontools_dir, icontools_tag, use_apptainer):
    if use_apptainer:
        shell_cmd("apptainer", "exec", "--pwd", "/work", "--bind", f"{icontools_dir}:/work", "--env", "LD_LIBRARY_PATH=/home/dwd/software/lib", f"{workspace}/icon_tools.sif", "/home/dwd/icontools/icongridgen", "--nml", "/work/nml_gridgen")
    else:
        shell_cmd("podman", "run", "-w", "/work", "-u", "0", "-v", f"{icontools_dir}:/work", "-e", "LD_LIBRARY_PATH=/home/dwd/software/lib", "-t", f"execute:{icontools_tag}", "/home/dwd/icontools/icongridgen", "--nml", "/work/nml_gridgen")
    logging.info("Gridgen completed")


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


def load_config(config_file):
    logging.info(f"Loading configuration from {config_file}")
    with open(config_file, 'r') as f:
        config = json.load(f)
    logging.info("Configuration loaded successfully")
    return config


def write_gridgen_namelist(config, wrk_dir):
    logging.info("Writing gridgen namelist")
    icontools_tag = config["zonda"]["icontools_tag"]
    basegrid = config["basegrid"]
    domains = config["domains"]
    
    # Ensure the first domain has parent_id = 0
    domains[0]["icontools"]["parent_id"] = 0
    
    # Set default values
    parent_id = ",".join(str(domain["icontools"]["parent_id"]) for domain in domains)
    initial_refinement = True

    # Create the namelist content
    namelist = []
    namelist.append("&gridgen_nml")
    namelist.append(f"  parent_id           = {parent_id}            ! This list defines parent-nest relations")
    namelist.append(f"  initial_refinement = .{str(initial_refinement).upper()}.")
    namelist.append("")

    # base grid
    namelist.append(f"  basegrid%grid_root   = {basegrid['grid_root']}")
    namelist.append(f"  basegrid%grid_level  = {basegrid['grid_level']}")
    namelist.append(f"  basegrid%icopole_lon = {basegrid['icopole_lon']}")
    namelist.append(f"  basegrid%icopole_lat = {basegrid['icopole_lat']}")
    namelist.append(f"  basegrid%icorotation = {basegrid['icorotation']}")
    namelist.append("")

    # tuning parameters
    namelist.append(f"  lspring_dynamics = .TRUE.")
    namelist.append(f"  maxit = 2000")
    namelist.append(f"  beta_spring = 0.9")
    namelist.append(f"  bdy_indexing_depth = {basegrid.get('bdy_indexing_depth',14)}")
    namelist.append("")
    
    # centre and subcentre
    namelist.append(f"  centre = {basegrid.get('centre',78)}")
    namelist.append(f"  subcentre = {basegrid.get('subcentre',255)}")
    namelist.append("")

    grid_files = []
    for i, domain in enumerate(domains):
        icontools = domain["icontools"]
        lwrite_parent = i == 0
        namelist.append(f"  dom({i+1})%outfile             = \"{basegrid['outfile']}\" ")
        namelist.append(f"  dom({i+1})%lwrite_parent       = .{str(lwrite_parent).upper()}.")
        namelist.append(f"  dom({i+1})%region_type         = {icontools['region_type']}")
        namelist.append(f"  dom({i+1})%number_of_grid_used = {icontools.get('number_of_grid_used',0)}")

        if icontools_tag == "master":
            namelist.append(f"  dom({i+1})%lsmoothed           = .{str(icontools.get('lsmoothed', True)).upper()}.")

        namelist.append("")

        # local domain
        if icontools["region_type"] == 3:
            namelist.append(f"  dom({i+1})%center_lon   = {icontools.get('center_lon',0.0)}")
            namelist.append(f"  dom({i+1})%center_lat   = {icontools.get('center_lat',0.0)}")
            namelist.append(f"  dom({i+1})%hwidth_lon   = {icontools.get('hwidth_lon',0.0)}")
            namelist.append(f"  dom({i+1})%hwidth_lat   = {icontools.get('hwidth_lat',0.0)}")
            namelist.append("")

            namelist.append(f"  dom({i+1})%lrotate      = .{str(icontools.get('lrotate', False)).upper()}.")
            namelist.append(f"  dom({i+1})%pole_lon     = {icontools.get('pole_lon',-180.0)}")
            namelist.append(f"  dom({i+1})%pole_lat     = {icontools.get('pole_lat', 90.0)}")
            namelist.append("")

        # circular domain
        if icontools["region_type"] == 2:
            namelist.append(f"  dom({i+1})%center_lon   = {icontools.get('center_lon',0.0)}")
            namelist.append(f"  dom({i+1})%center_lat   = {icontools.get('center_lat',0.0)}")
            namelist.append(f"  dom({i+1})%radius       = {icontools.get('radius',0.0)}")
            namelist.append("")
        
        grid_files.append(f"{basegrid['outfile']}_{dom_id_to_str(i)}.nc")

    namelist.append("/")
    namelist.append("")

    # Write the namelist content to a file
    namelist_filename = os.path.join(wrk_dir, 'nml_gridgen')
    with open(namelist_filename, 'w') as f:
        f.write("\n".join(namelist))
    logging.info(f"Namelist written to {namelist_filename}")

    return grid_files


def dom_id_to_str(dom_id):
    return f"DOM{dom_id+1:02d}"


def run_icontools(workspace, config, icontools_tag, use_apptainer):
    logging.info(f"Number of domains: {len(config['domains'])}")

    icontools_dir = os.path.join(workspace, 'icontools')
    os.makedirs(icontools_dir, exist_ok=True)
    logging.info(f"Created directory: {icontools_dir}")

    grid_files = write_gridgen_namelist(config, icontools_dir)

    run_gridgen(workspace, icontools_dir, icontools_tag, use_apptainer)

    return grid_files


def pull_extpar_image(config):
    tag = config['extpar_tag']
    if tag != "latest":
        shell_cmd("podman", "pull", f"docker.io/c2sm/extpar:{tag}")
        logging.info("Pull extpar image completed")
    else:
        logging.info("Using latest extpar tag (it must already be present on the system)")
    return tag


def run_rotgrid(workspace, config, grid_files):
    logging.info("Creating lat-lon grid")
    basegrid = config['basegrid']
    domains = config['domains']

    # Ensure the output directory exists
    output_dir = os.path.join(workspace, 'output')
    os.makedirs(output_dir, exist_ok=True)

    for i, domain in enumerate(domains):
        icontools = domain['icontools']

        # Only rectangular domains are supported
        if icontools.get('region_type') == 3:

            lrotate = icontools.get('lrotate', False)

            center_lat = icontools['center_lat']
            center_lon = icontools['center_lon']
            hwidth_lat = icontools['hwidth_lat']
            hwidth_lon = icontools['hwidth_lon']

            n = basegrid['grid_root']
            k = basegrid['grid_level'] + 1 + i
            grid_spacing = compute_resolution_from_rnbk(n, k)

            grid_file_base = grid_files[i].removesuffix('.nc')
            output_filename_suffix = "_rotated" if lrotate else ""
            output_path_full = os.path.join(output_dir, f'{grid_file_base}_latlon{output_filename_suffix}.nc')

            if lrotate:
                pole_lat = icontools['pole_lat']
                pole_lon = icontools['pole_lon']

                create_rotated_grid( grid_spacing,
                                     center_lat,
                                     center_lon,
                                     hwidth_lat,
                                     hwidth_lon,
                                     pole_lat,
                                     pole_lon,
                                     0,
                                     output_path_full )

                logging.info(f'Rotated lat-lon grid for {dom_id_to_str(i)} stored in {output_path_full}')
            else:
                create_latlon_grid( grid_spacing,
                                    center_lat,
                                    center_lon,
                                    hwidth_lat,
                                    hwidth_lon,
                                    0,
                                    output_path_full )

                logging.info(f'Lat-lon grid for {dom_id_to_str(i)} stored in {output_path_full}')
        else:
            logging.info(f'{dom_id_to_str(i)} is not rectangular (i.e., region_type = 3) -> Skipping generation of lat-lon grid!')


def compute_resolution_from_rnbk(n, k):
    earth_radius = 6371.0
    return earth_radius * sqrt(pi / 5) / (n * pow(2, k))


def main(workspace, config_path, extpar_rawdata_path, use_apptainer):
    logging.info(f"Starting main process with\n"
                 f"  workspace: {workspace}\n"
                 f"  config_path: {config_path}\n"
                 f"  extpar_rawdata_path: {extpar_rawdata_path}\n"
                 f"  use_apptainer: {use_apptainer}")
    
    # Load config and write namelist
    config = load_config(config_path)
    zonda = config['zonda']

    if use_apptainer:
        logging.warning("You are using apptainer, thus the extpar_tag and icontools_tag entries in the config file are ignored!")

    input_grid_path = zonda.get("input_grid_path")
    icontools_active = input_grid_path is None

    if icontools_active:
        icontools_tag = zonda.get('icontools_tag', 'master')

        grid_dir = os.path.join(workspace, 'icontools')
        grid_files = run_icontools(workspace, config, icontools_tag, use_apptainer)

        outfile = config['basegrid']['outfile']
    else:
        input_grid_path = os.path.abspath(input_grid_path)

        if os.path.isfile(input_grid_path):
            grid_dir = os.path.dirname(input_grid_path)
            grid_files = [os.path.basename(input_grid_path)]

            outfile = os.path.splitext(grid_files[0])[0]

            logging.warning(f'You provided an input grid at "{input_grid_path}", thus the grid generation step is skipped!\n'
                            'Note that the "basegrid", "icontools", and "icontools_tag" entries in the JSON config are ignored.')
        else:
            logging.error(f'The provided input grid is not a file: "{input_grid_path}". Please provide the path to NetCDF file.')
            raise FileNotFoundError(f'"{input_grid_path}" is not a file')

    extpar_tag = zonda['extpar_tag'] if use_apptainer else pull_extpar_image(zonda)

    extpar_dirs = run_extpar(workspace, config_path, extpar_rawdata_path, grid_files, grid_dir, extpar_tag, use_apptainer)

    if icontools_active:
        try:
            run_rotgrid(workspace, config, grid_files)
        except Exception as e:
            logging.warning("An error occurred during the generation of the rotated lat-lon grid.\n"
                            f"{repr(e)}\n"
                            "Skipping generation of rotated lat-lon grid!")

        try:
            for i, grid_file in enumerate(grid_files):
                grid_filepath = os.path.join(grid_dir, grid_file)
                extpar_filepath = os.path.join(extpar_dirs[i], "external_parameter.nc")

                icontools_config = config['domains'][i]['icontools']

                visualize_topography(icontools_config, workspace, extpar_filepath, grid_filepath, extpar_dirs[i])
        except Exception as e:
            logging.warning("An error occurred during the visualization of topography data.\n"
                            f"{repr(e)}\n"
                            "Skipping the visualization!")
    else:
        logging.warning("An input grid was provided. Skipping generation of rotated lat-lon grid and visualization of topography!")

    if icontools_active:
        keep_base_grid = config['basegrid']['keep_basegrid_files']
    else:
        keep_base_grid = False  # Likely no basegrid files if the grid is provided by the user

    move_output(workspace, grid_files, extpar_dirs, outfile, keep_base_grid, icontools_active)

    logging.info("Process completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser.add_argument('--workspace', type=str, required=True, help="Path to the workspace directory")
    parser.add_argument('--extpar-rawdata', type=str, required=True, help="Path to the EXTPAR raw input data")
    parser.add_argument('--logfile', type=str, help="Path to the log file")
    parser.add_argument('--apptainer', action=argparse.BooleanOptionalAction, default=False, help="Use apptainer instead of podman to run containers")

    args = parser.parse_args()

    # setup logger
    format = "%(asctime)s - %(levelname)s - %(message)s"
    if args.logfile:
        logging.basicConfig(filename=args.logfile, filemode='w', format=format, level=logging.INFO)
    else:
        logging.basicConfig(format=format, level=logging.INFO)

    workspace = os.path.abspath(args.workspace)
    config = os.path.abspath(args.config)
    extpar_rawdata_path = os.path.abspath(args.extpar_rawdata)

    use_apptainer = args.apptainer

    main(workspace, config, extpar_rawdata_path, use_apptainer)
