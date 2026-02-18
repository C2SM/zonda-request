import argparse
import os
import logging
from output_manager import OutputManager
from grid_manager import GridManager
from extpar_manager import ExtparManager
from utilities.utilities import load_config, LOG_PADDING_INFO, LOG_PADDING_WARNING, LOG_INDENTATION_STR
from visualization.visualize_data import visualize_topography



def create_nesting_groups(config, grid_sources):
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

def main(config_path, workspace_path, extpar_raw_data_path, zonda_log_filename, use_apptainer):

    logging.info( f"Start main process with\n"
                  f"{LOG_PADDING_INFO}  config_path: {config_path}\n"
                  f"{LOG_PADDING_INFO}  workspace_path: {workspace_path}\n"
                  f"{LOG_PADDING_INFO}  extpar_raw_data_path: {extpar_raw_data_path}\n"
                  f"{LOG_PADDING_INFO}  zonda_log_filename: {zonda_log_filename}\n"
                  f"{LOG_PADDING_INFO}  use_apptainer: {use_apptainer}" )

    logging.info(f"{LOG_INDENTATION_STR}Load configuration from \"{config_path}\".")
    config = load_config(config_path)
    config_filename = os.path.basename(config_path)

    if use_apptainer:
        logging.warning(f"Apptainer is being used, the extpar_tag and icontools_tag entries in the config file {config_filename} are ignored!")

    output_manager = OutputManager(config, workspace_path, config_filename, zonda_log_filename)
    grid_manager = GridManager(config, workspace_path, output_manager, use_apptainer=use_apptainer)
    extpar_manager = ExtparManager(config, workspace_path, extpar_raw_data_path, use_apptainer=use_apptainer)

    logging.info(f"{LOG_INDENTATION_STR}Create nesting groups from grid sources: {grid_manager.grid_sources}.")
    nesting_groups = create_nesting_groups(config, grid_manager.grid_sources)
    n_nesting_groups = len(nesting_groups)

    for nesting_group_idx, nesting_group in enumerate(nesting_groups):
        logging.info(f"{LOG_INDENTATION_STR}Work on nesting group {nesting_group_idx+1} of {n_nesting_groups}.")

        primary_grid_source = grid_manager.grid_sources[nesting_group[0]]

        # Keeping the base grid only makes sense when icontools is the grid source of the first domain
        if nesting_group_idx == 0 and primary_grid_source == "icontools":
            keep_basegrid_files = config["basegrid"].get("keep_basegrid_files", False)
        else:
            keep_basegrid_files = False  # No basegrid files if the grid is provided by the user or it's not the first domain

        try:
            ### GRID GENERATION ###
            grid_manager.generate_icon_grids(nesting_group, logging_indentation_level=2)

            ### EXTPAR ###
            extpar_manager.run_extpar(nesting_group, grid_manager.grid_dirs, grid_manager.grid_filenames, logging_indentation_level=2)
        except Exception:
            output_manager.move_output(grid_manager, extpar_manager, keep_basegrid_files, logging_indentation_level=1)
            output_manager.move_zonda_files(logging_indentation_level=1)
            output_manager.zip_output(logging_indentation_level=1)
            raise

        ### LAT-LON GRID GENERATION ###
        try:
            grid_manager.generate_latlon_grids(nesting_group, logging_indentation_level=2)
        except Exception as e:
            logging.warning( "An error occurred during the generation of the lat-lon grids for domains "
                             f"{', '.join([str(domain_id) for domain_id in nesting_group])}.\n"
                             f"{repr(e)}\n"
                             f"{LOG_PADDING_WARNING}Skipping generation of lat-lon grids!" )

        ### TOPOGRAPHY VISUALIZATION ###
        try:
            for domain_id in nesting_group:
                domain_idx = domain_id - 1

                logging.info(f"{LOG_INDENTATION_STR*2}Visualization of EXTPAR fields for domain {domain_id}.")
                if grid_manager.grid_sources[domain_idx] == "icontools":
                    icontools_config = config["domains"][domain_idx]["icontools"]

                    grid_filepath = os.path.join(grid_manager.grid_dirs[domain_idx], grid_manager.grid_filenames[domain_idx])
                    extpar_filepath = os.path.join(extpar_manager.extpar_dirs[domain_idx], "external_parameter.nc")

                    visualize_topography(icontools_config, workspace_path, grid_filepath, extpar_filepath, extpar_manager.extpar_dirs[domain_idx], logging_indentation_level=3)
                else:
                    logging.warning(f"An input grid was provided for domain {domain_id}. Skipping visualization of EXTPAR fields!")
        except Exception as e:
            logging.warning( "An error occurred during the visualization of topography data for domains "
                             f"{', '.join([str(domain_id) for domain_id in nesting_group])}.\n"
                             f"{repr(e)}\n"
                             "{LOG_PADDING_WARNING}Skipping the visualization!" )

        ### MOVE OUTPUT ###
        output_manager.move_output(grid_manager, extpar_manager, keep_basegrid_files, logging_indentation_level=2)

    output_manager.move_zonda_files(logging_indentation_level=1)
    output_manager.zip_output(logging_indentation_level=1)

    logging.info("Process completed.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
    parser.add_argument("--workspace", type=str, required=True, help="Path to the workspace directory")
    parser.add_argument("--extpar-raw-data", type=str, required=True, help="Path to the EXTPAR raw input data")
    parser.add_argument("--logfile", type=str, help="Path to the log file")
    parser.add_argument("--apptainer", action=argparse.BooleanOptionalAction, default=False, help="Use apptainer instead of podman to run containers")

    args = parser.parse_args()

    logger_format = "%(asctime)s - %(levelname)s - %(message)s"
    if args.logfile:
        logging.basicConfig(filename=args.logfile, filemode='w', format=logger_format, level=logging.INFO)
    else:
        logging.basicConfig(format=logger_format, level=logging.INFO)

    config_path = os.path.abspath(args.config)
    workspace_path = os.path.abspath(args.workspace)
    extpar_raw_data_path = os.path.abspath(args.extpar_raw_data)

    zonda_log_filename = os.path.basename(args.logfile)

    use_apptainer = args.apptainer

    main(config_path, workspace_path, extpar_raw_data_path, zonda_log_filename, use_apptainer)
