import json
import argparse
import os
import shutil

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config


def write_gridgen_namelist(config,wrk_dir):
    # Set default values
    parent_id = 0
    lwrite_parent = True
    initial_refinement = True

    # Create the namelist content
    namelist = []
    namelist.append("&gridgen_nml")
    namelist.append(f"  parent_id           = {parent_id}            ! This list defines parent-nest relations")
    namelist.append(f"  initial_refinement = .{str(initial_refinement).upper()}.")
    namelist.append("")

    # base grid
    namelist.append(f"  basegrid%grid_root   = {config.get('grid_root')}")
    namelist.append(f"  basegrid%grid_level  = {config.get('grid_level')}")
    namelist.append(f"  basegrid%icopole_lon = {config.get('icopole_lon', 0.0)}")
    namelist.append(f"  basegrid%icopole_lat = {config.get('icopole_lat', 90)}")
    namelist.append(f"  basegrid%icorotation = {config.get('icorotation', 0.0)}")

    # tuning parameters
    namelist.append(f"  lspring_dynamics = .{str(config.get('lspring_dynamics',False)).upper()}.")
    namelist.append(f"  maxit = {config.get('maxit', 500)}")
    namelist.append(f"  beta_spring = {config.get('beta_spring', 0.9)}")
    namelist.append("")
    
    # centre and subcentre
    namelist.append(f"  centre = {config.get('centre',78)}")
    namelist.append(f"  subcentre = {config.get('subcentre',255)}")
    namelist.append("")

    # dom
    namelist.append(f"  dom(1)%lwrite_parent = .{str(lwrite_parent).upper()}.")
    namelist.append(f"  dom(1)%outfile = \"{config.get('outfile')}\"")
    namelist.append(f"  dom(1)%region_type  = {config.get('region_type')}")
    namelist.append(f"  dom(1)%number_of_grid_used    = {config.get('number_of_grid_used',0)}")
    namelist.append("")

    # local region
    if config["region_type"] == 3:
        namelist.append(f"  dom(1)%center_lon   = {config.get('center_lon',0.0)}")
        namelist.append(f"  dom(1)%center_lat   = {config.get('center_lat',0.0)}")
        namelist.append(f"  dom(1)%hwidth_lon   = {config.get('hwidth_lon',0.0)}")
        namelist.append(f"  dom(1)%hwidth_lat   = {config.get('hwidth_lat',0.0)}")
        namelist.append("")

        namelist.append(f"  dom(1)%lrotate      = .{str(config.get('lrotate', True)).upper()}.")
        namelist.append(f"  dom(1)%pole_lon = {config.get('pole_lon',-180.0)}")
        namelist.append(f"  dom(1)%pole_lat = {config.get('pole_lat', 90.0)}")
        namelist.append("")
        
    namelist.append("/")
    namelist.append("")

    # Write the namelist content to a file
    with open(os.path.join(wrk_dir,'nml_gridgen'), 'w') as f:
        f.write("\n".join(namelist))

    # write filename to grid.txt for extpar
    with open(os.path.join(wrk_dir,'grid.txt'), 'w') as f:
        f.write(f"{config.get('outfile')}_DOM01.nc")

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

    write_gridgen_namelist(config, icontools_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup workspace and generate namelist")
    parser.add_argument('--workspace', type=str, required=True, help="Path to the workspace directory")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")

    args = parser.parse_args()

    main(args.workspace, args.config)
