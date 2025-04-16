import json
import argparse
import os
import shutil
import logging
import subprocess
import glob
import zipfile

def move_files(src_pattern, dest_dir, prefix="",blacklist={}):
    for file in glob.glob(src_pattern):
        if os.path.basename(file) in blacklist:
            logging.info(f"Skipping {file}")
            continue
        dest_file = os.path.join(dest_dir, prefix + os.path.basename(file))
        logging.info(f"Move {file} to {dest_file}")
        shutil.move(file, dest_file)


def move_extpar(dest, grid_files, extpar_dirs):
    for i, exptar_dir in enumerate(extpar_dirs):
        # Move logfiles
        move_files(os.path.join(exptar_dir, "*.log"), os.path.join(dest, 'logs'), f"{dom_id_to_str(i)}_")
        # Move external parameter file
        grid_file_base = os.path.splitext(grid_files[i])[0]  # Drop the suffix ".nc"
        move_files(os.path.join(exptar_dir, "external_parameter.nc"), dest, f"{grid_file_base}_")

def move_icontools(workspace, dest, keep_base_grid):
    # too big for high-res grids
    blacklist = {} if keep_base_grid else {'base_grid.nc', 'base_grid.html'}
    # Move .nc files
    move_files(os.path.join(workspace, 'icontools', '*.nc'), os.path.join(dest), blacklist=blacklist)
    # Move .html files
    move_files(os.path.join(workspace, 'icontools', '*.html'), dest, blacklist=blacklist)


def create_zip(zip_file_path, source_dir):
    logging.info(f"Creating zip file {zip_file_path}")
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

def move_output(workspace, grid_files, extpar_dirs, keep_base_grid):

    output_dir = os.path.join(workspace, 'output')
    log_dir = os.path.join(output_dir, 'logs')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    logging.info(f"Output directory: {output_dir}")

    # Move extpar files
    move_extpar(output_dir, grid_files, extpar_dirs)

    # Move icontools files
    move_icontools(workspace, output_dir, keep_base_grid)

    # Create a zip file
    zip_file_path = os.path.join(workspace, 'output.zip')

    
    create_zip(zip_file_path, output_dir)

def run_extpar(workspace, config_path, grid_files, extpar_tag):
    extpar_dirs = []
    config = load_config(config_path)

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

        shell_cmd(
            "podman", "run",
            "-e", "OMP_NUM_THREADS=32",
            "-v", "/net/co2/c2sm-data/extpar-input-data:/data",
            "-v", f"{workspace}/icontools:/grid",
            "-v", f"{extpar_dir}:/work",
            f"extpar:{extpar_tag}",
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

def run_gridgen(wrk_dir):
    shell_cmd("podman", "run", "-w", "/work", "-u", "0", "-v", f"{wrk_dir}:/work", "-e", "LD_LIBRARY_PATH=/home/dwd/software/lib", "-t", "execute:latest-master", "/home/dwd/icontools/icongridgen", "--nml", "/work/nml_gridgen")
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
        output = e.stderr
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
    namelist.append(f"  lspring_dynamics = .{str(config.get('lspring_dynamics',True)).upper()}.")
    namelist.append(f"  maxit = {config.get('maxit', 500)}")
    namelist.append(f"  beta_spring = {config.get('beta_spring', 0.9)}")
    namelist.append("")
    
    # centre and subcentre
    namelist.append(f"  centre = {config.get('centre',78)}")
    namelist.append(f"  subcentre = {config.get('subcentre',255)}")
    namelist.append("")

    grid_files = []
    for i, domain in enumerate(domains):
        icontools = domain["icontools"]
        lwrite_parent = i == 0
        namelist.append(f"  dom({i+1})%outfile             = \"{basegrid['outfile']}\" ")
        namelist.append(f"  dom({i+1})%lwrite_parent       = .{str(lwrite_parent).upper()}.")
        namelist.append(f"  dom({i+1})%region_type         = {icontools['region_type']}")
        namelist.append(f"  dom({i+1})%number_of_grid_used = {icontools.get('number_of_grid_used',0)}")
        namelist.append("")

        # local domain
        if icontools["region_type"] == 3:
            namelist.append(f"  dom({i+1})%center_lon   = {icontools.get('center_lon',0.0)}")
            namelist.append(f"  dom({i+1})%center_lat   = {icontools.get('center_lat',0.0)}")
            namelist.append(f"  dom({i+1})%hwidth_lon   = {icontools.get('hwidth_lon',0.0)}")
            namelist.append(f"  dom({i+1})%hwidth_lat   = {icontools.get('hwidth_lat',0.0)}")
            namelist.append("")

            namelist.append(f"  dom({i+1})%lrotate      = .{str(icontools.get('lrotate', True)).upper()}.")
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

def run_icontools(workspace, config):
    logging.info(f"Number of domains: {len(config['domains'])}")

    icontools_dir = os.path.join(workspace, 'icontools')
    os.makedirs(icontools_dir, exist_ok=True)
    logging.info(f"Created directory: {icontools_dir}")

    grid_files = write_gridgen_namelist(config, icontools_dir)

    run_gridgen(icontools_dir)

    return grid_files

def pull_extpar_image(config):
    tag = config['extpar_tag']
    shell_cmd("podman", "pull", f"docker.io/c2sm/extpar:{tag}")
    logging.info("Pull extpar image completed")
    return tag

def main(workspace, config_path):
    logging.info(f"Starting main process with workspace: {workspace} and config_path: {config_path}")
    
    # Load config and write namelist
    config = load_config(config_path)

    grid_files = run_icontools(workspace, config)

    extpar_tag = pull_extpar_image(config['zonda'])

    extpar_dirs = run_extpar(workspace, config_path, grid_files, extpar_tag)
    
    keep_base_grid = config['basegrid']['keep_basegrid_files']
    move_output(workspace, grid_files, extpar_dirs, keep_base_grid)

    logging.info("Process completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument('--workspace', type=str, required=True, help="Path to the workspace directory")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")
    parser.add_argument('--logfile', type=str, help="Path to the log file")

    args = parser.parse_args()

    # setup logger
    format = "%(asctime)s - %(levelname)s - %(message)s"
    if args.logfile:
        logging.basicConfig(filename=args.logfile, format=format, level=logging.INFO)
    else:
        logging.basicConfig(format=format, level=logging.INFO)

    workspace = os.path.abspath(args.workspace)
    config = os.path.abspath(args.config)

    main(workspace, config)
