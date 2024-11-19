import json
import argparse

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def write_global_namelist(config):
    # Set default values
    parent_id = 0
    lwrite_parent = True
    initial_refinement = True
    basegrid_grid_root = config.get('grid_root')
    basegrid_grid_level = config.get('grid_level')
    dom_outfile = config.get('outfile', 'icon_global')
    dom_region_type = config.get('region_type', 1)

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
    with open('icontools/nml_gridgen', 'w') as f:
        f.write(namelist_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract settings from config file")
    parser.add_argument('--config', type=str, required=True, help="Path to the configuration file")

    args = parser.parse_args()

    config = load_config(args.config)
    config = config['icontools']

    if config["region_type"] == 1:
        write_global_namelist(config)
    else:
        print("Region type not supported")

    grid_level = config.get('grid_level')
    grid_root = config.get('grid_root')
    region_type = config.get('region_type')
    outfile = config.get('outfile')
