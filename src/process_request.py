import json
import argparse
import os
import logging
from output_manager import OutputManager
from grid_manager import GridManager
from extpar_manager import ExtparManager
from utilities import load_config
from visualize_data import visualize_topography



def create_nesting_groups(config, grid_sources):
    logging.info("Creating nesting groups.")

    domains_config = config["domains"]

    nesting_groups = []

    for domain_config in domains_config:
        domain_id = domain_config["domain_id"]
        domain_idx = domain_id - 1

        # ATTENTION:
        # The condition below should be added to the if only if more valid grid sources are added, but for now
        # let's assume "input_grid" and "icontools" are the only possible ones.
        # ... and ((grid_sources[domain_idx-1] == "input_grid") or (grid_sources[domain_idx-1] == "icontools")):
        if (len(nesting_groups) > 0) and (grid_sources[domain_idx] == "icontools"):
            nesting_groups[-1].append(domain_id)
        else:
            nesting_groups.append([domain_id])

    return nesting_groups

def main(config_path, workspace_path, extpar_raw_data_path, use_apptainer):

    logging.info( f"Starting main process with\n"
                  f"  config_path: {config_path}\n"
                  f"  workspace_path: {workspace_path}\n"
                  f"  extpar_raw_data_path: {extpar_raw_data_path}\n"
                  f"  use_apptainer: {use_apptainer}" )

    if use_apptainer:
        logging.warning("Apptainer is being used, thus the extpar_tag and icontools_tag entries in the config file are ignored!")

    config = load_config(config_path)

    output_manager = OutputManager(config, workspace_path)
    grid_manager = GridManager(config, workspace_path, output_manager, use_apptainer=use_apptainer)
    extpar_manager = ExtparManager(config, workspace_path, extpar_raw_data_path, use_apptainer=use_apptainer)

    nesting_groups = create_nesting_groups(config, grid_manager.grid_sources)

    for nesting_group_idx, nesting_group in enumerate(nesting_groups):

        primary_grid_source = grid_manager.grid_sources[nesting_group[0]]

        # Keeping the base grid only makes sense when icontools is the grid source of the first domain
        if nesting_group_idx == 0 and primary_grid_source == "icontools":
            keep_basegrid_files = config["basegrid"].get("keep_basegrid_files", False)
        else:
            keep_basegrid_files = False  # No basegrid files if the grid is provided by the user or it's not the first domain

        try:
            ### GRID GENERATION ###
            grid_manager.generate_icon_grids(nesting_group)

            ### EXTPAR ###
            extpar_manager.run_extpar(nesting_group, grid_manager.grid_dirs, grid_manager.grid_filenames)
        except Exception:
            output_manager.move_output(grid_manager, extpar_manager, keep_basegrid_files)
            output_manager.move_zonda_config()
            output_manager.zip_output()
            raise

        ### LAT-LON GRID GENERATION ###
        try:
            grid_manager.generate_latlon_grids(nesting_group)
        except Exception as e:
            logging.warning( "An error occurred during the generation of the lat-lon grids for domains "
                             f"{', '.join([str(domain_id) for domain_id in nesting_group])}.\n"
                             f"{repr(e)}\n"
                             "Skipping generation of lat-lon grids!" )

        ### TOPOGRAPHY VISUALIZATION ###
        try:
            for domain_id in nesting_group:
                domain_idx = domain_id - 1

                if grid_manager.grid_sources[domain_idx] == "icontools":
                    icontools_config = config["domains"][domain_idx]["icontools"]

                    grid_filepath = os.path.join(grid_manager.grid_dirs[domain_idx], grid_manager.grid_filenames[domain_idx])
                    extpar_filepath = os.path.join(extpar_manager.extpar_dirs[domain_idx], extpar_manager.extpar_filename)

                    visualize_topography(icontools_config, workspace_path, grid_filepath, extpar_filepath, extpar_manager.extpar_dirs[domain_idx])
                else:
                    logging.warning(f"An input grid was provided for domain {domain_id}. Skipping visualization of topography!")
        except Exception as e:
            logging.warning( "An error occurred during the visualization of topography data for domains "
                             f"{', '.join([str(domain_id) for domain_id in nesting_group])}.\n"
                             f"{repr(e)}\n"
                             "Skipping the visualization!" )

        ### MOVE OUTPUT ###
        output_manager.move_output(grid_manager, extpar_manager, keep_basegrid_files)

    output_manager.move_zonda_config()
    output_manager.zip_output()

    logging.info("Process completed.")



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
