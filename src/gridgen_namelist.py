import json
import argparse
import os
import shutil

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def write_local_namelist(config,wrk_dir):
    # Set default values
    parent_id = 0
    lwrite_parent = True
    initial_refinement = True
    basegrid_grid_root = config.get('grid_root')
    basegrid_grid_level = config.get('grid_level')
    dom_outfile = config.get('outfile')
    dom_region_type = config.get('region_type')
    lrotate = config.get('lrotate', False)

    # Create the namelist content
    namelist = []
    namelist.append("&gridgen_nml")
    namelist.append(f"  parent_id           = {parent_id}            ! This list defines parent-nest relations")
    namelist.append(f"  dom(1)%lwrite_parent = .{str(lwrite_parent).upper()}.")
    namelist.append(f"  basegrid%grid_root   = {basegrid_grid_root}")
    namelist.append(f"  basegrid%grid_level  = {basegrid_grid_level}")
    namelist.append(f"  initial_refinement = .{str(initial_refinement).upper()}.")
    namelist.append(f"  dom(1)%outfile = \"{dom_outfile}\"")
    namelist.append(f"  dom(1)%region_type  = {dom_region_type}")
    namelist.append("")
    namelist.append(f"  dom(1)%center_lon   = {config.get('center_lon')}")
    namelist.append(f"  dom(1)%center_lat   = {config.get('center_lat')}")
    namelist.append(f"  dom(1)%hwidth_lon   = {config.get('hwidth_lon')}")
    namelist.append(f"  dom(1)%hwidth_lat   = {config.get('hwidth_lat')}")
    namelist.append("")

    if lrotate:
        namelist.append(f"  dom(1)%lrotate      = .{str(lrotate).upper()}.")
        namelist.append(f"  dom(1)%pole_lat = {config.get('pole_lat')}")
        namelist.append(f"  dom(1)%pole_lon = {config.get('pole_lon')}")
        
    namelist.append("/")

    # Write the namelist content to a file
    with open(os.path.join(wrk_dir,'nml_gridgen'), 'w') as f:
        f.write("\n".join(namelist))

    # write filename to grid.txt for extpar
    with open(os.path.join(wrk_dir,'grid.txt'), 'w') as f:
        f.write(f'{dom_outfile}_DOM01.nc')

def write_global_namelist(config,wrk_dir):
    # Set default values
    parent_id = 0
    lwrite_parent = True
    initial_refinement = True
    basegrid_grid_root = config.get('grid_root')
    basegrid_grid_level = config.get('grid_level')
    dom_outfile = config.get('outfile')
    dom_region_type = config.get('region_type')

    # Create the namelist content
    namelist_content = f"""&gridgen_nml
  parent_id           = {parent_id}            ! This list defines parent-nest relations
  dom(1)%lwrite_parent = .{str(lwrite_parent).upper()}.
  basegrid%grid_root   = {basegrid_grid_root}
  basegrid%grid_level  = {basegrid_grid_level}
  initial_refinement = .{str(initial_refinement).upper()}.
  dom(1)%outfile = "{dom_outfile}"
  dom(1)%region_type  = {dom_region_type}
/
"""

    # Write the namelist content to a file
    with open(os.path.join(wrk_dir,'nml_gridgen'), 'w') as f:
        f.write(namelist_content)

    # write filename to grid.txt for extpar
    with open(os.path.join(wrk_dir,'grid.txt'), 'w') as f:
        f.write(f'{dom_outfile}_DOM01.nc')

def main(workspace, config_path):
    # Create directories
    extpar_dir = os.path.join(workspace, 'extpar')
    icontools_dir = os.path.join(workspace, 'icontools')
    os.makedirs(extpar_dir, exist_ok=True)
    os.makedirs(icontools_dir, exist_ok=True)

    # Copy config.json to extpar directory
    shutil.copy(config_path, os.path.join(extpar_dir, 'config.json'))

    # Load config and write namelist
    config = load_config(config_path)
    config = config['icontools']

    if config["region_type"] == 1:
        write_global_namelist(config, icontools_dir)
    else:
        write_local_namelist(config, icontools_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument('--workspace', type=str, required=True, help="Path to the workspace directory")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")

    args = parser.parse_args()

    main(args.workspace, args.config)
