import logging

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.colors as col
import matplotlib.ticker as tck
import matplotlib.cm as cm
import xarray as xr
import numpy as np

from os import path
from PIL import Image
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


#####################
### Fonts & stuff ###
#####################

font            = {'family': 'DejaVu Serif'            }
small_font      = {'family': 'DejaVu Serif', 'size': 8 }
legend_settings = {'family': 'DejaVu Serif', 'size': 10}
code_font       = {'family': 'Courier New'             }


#####################
### Main function ###
#####################

def visualize_topography(workspace, data_file, grid_file, output_dir):

    logging.info(f"Starting the visualization of topography data")

    ##################################
    ### Get and transform the data ###
    ##################################

    # Read NetCDF files (field values and grid data)
    logging.info(f"Reading EXTPAR file: {data_file}")
    icon_output_dataset = xr.open_dataset(data_file)

    logging.info(f"Reading grid file: {grid_file}")
    grid_dataset = xr.open_dataset(grid_file)

    dpi = 560

    # Get the necessary data
    grid_coords    = grid_dataset.coords
    grid_data_vars = grid_dataset.data_vars

    vertex_longitudes = np.rad2deg(grid_coords["vlon"].values)
    vertex_latitudes  = np.rad2deg(grid_coords["vlat"].values)

    vertices_of_cells = grid_data_vars["vertex_of_cell"].T.values - 1 
    cells_of_vertices = grid_data_vars["cells_of_vertex"].T.values - 1

    n_vertices = len(cells_of_vertices)

    topography_variable_name = "topography_c"
    topography_variable      = icon_output_dataset[topography_variable_name]
    topography_data          = topography_variable.values[:]
    topography_long_name     = topography_variable.attrs["long_name"].capitalize()
    topography_units         = topography_variable.attrs["units"]

    fr_land_variable_name = "FR_LAND"
    fr_land_data = icon_output_dataset[fr_land_variable_name].values

    topography_data_min  = topography_data.min()
    topography_data_max  = topography_data.max()

    topography_data[np.logical_and(fr_land_data == 0., topography_data == 0.)] = None

    # Add vertices at boundaries to allow for correct wrapping of triangular mesh around (periodic) boundaries
    vertices_at_boundary_mask = (vertex_longitudes == -180.0) | (vertex_longitudes == 180.0)
    if any(vertices_at_boundary_mask):

        logging.info("Create new vertices at the boundaries to account for periodicity")

        cells_at_boundary = np.unique(cells_of_vertices[vertices_at_boundary_mask].flatten())
        index_to_delete   = np.argwhere(cells_at_boundary == -1)
        cells_at_boundary = np.delete(cells_at_boundary, index_to_delete)

        tmp_longitudes = []
        tmp_latitudes  = [] 
        new_vertex     = n_vertices
        for cell in cells_at_boundary:
            vertices = vertices_of_cells[cell].copy()

            for i, vertex in enumerate(vertices):

                if vertex_longitudes[vertex] < 0.0:
                    tmp_longitudes.append(vertex_longitudes[vertex] + 360.0)
                    tmp_latitudes.append(vertex_latitudes[vertex])

                    vertices_of_cells[cell][i] = new_vertex

                    new_vertex += 1

        vertex_longitudes = np.append(vertex_longitudes, np.asarray(tmp_longitudes))
        vertex_latitudes  = np.append(vertex_latitudes, np.asarray(tmp_latitudes))


    ################################
    ### Plot the requested field ###
    ################################

    logging.info(f"Plotting {topography_variable_name}")

    # Create figure and axis
    fig = plt.figure(figsize=(16, 9), dpi=dpi)
    ax = plt.axes(projection=ccrs.PlateCarree())

    figure_title = f"{topography_long_name} ({topography_variable_name})"

    ax.set_title(figure_title, **font)

    # Draw custom map on axis and lines delimiting coasts
    ax.coastlines(linewidth=0.5)

    terrain_cmap = cm.terrain
    cmap = col.LinearSegmentedColormap.from_list('modified_terrain', terrain_cmap(np.arange(60,256)))
    cmap.set_bad(color='lightblue')

    plotting_options = {
        'antialiaseds' : False,
        'edgecolors'   : 'none',
        'rasterized'   : True,
        'alpha'        : None
    }

    # Plot the triangular mesh with the faces colored according to the requested field
    collection = ax.tripcolor( vertex_longitudes, vertex_latitudes, topography_data,
                    triangles = vertices_of_cells,
                    cmap      = cmap,
                    vmin      = topography_data_min,
                    vmax      = topography_data_max,
                    transform = ccrs.PlateCarree(),
                    **plotting_options
    )

    # Draw gridlines at specific longitudes and latitudes
    gridlines = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=0.5, color='black', alpha=1., linestyle='solid')
    gridlines.top_labels   = False
    gridlines.left_labels  = False
    gridlines.xformatter   = LONGITUDE_FORMATTER
    gridlines.yformatter   = LATITUDE_FORMATTER
    gridlines.xlabel_style = small_font
    gridlines.ylabel_style = small_font

    # Create colorbar with transparency
    colorbar_formatter = tck.ScalarFormatter(useMathText=True)
    colorbar_formatter.set_powerlimits((0, 0))

    colorbar = plt.colorbar(collection, shrink=0.3, format=colorbar_formatter)
    colorbar.set_label(f"{topography_long_name} ({topography_units})", **font)
    colorbar.ax.yaxis.get_offset_text().set_font(small_font)
    plt.setp(colorbar.ax.yaxis.get_ticklabels(), **font)

    # Save and close the figure
    output_filepath = path.join(output_dir, "topography.png")
    logging.info(f"Saving plot to {output_filepath}")

    fig.savefig(output_filepath, bbox_inches='tight', dpi=dpi)

    plt.close(fig)

    # Add the Zonda logo to the plot
    logging.info(f"Adding Zonda logo to {output_filepath}")

    zonda_logo = Image.open(f"{workspace}/img/zonda_logo.png")
    plot_image = Image.open(output_filepath)

    plot_image_width, plot_image_height = plot_image.size
    zonda_logo_width, zonda_logo_height = zonda_logo.size

    # Resize the logo
    scaling_factor = 3.5

    zonda_logo_width  = int(zonda_logo_width / scaling_factor)
    zonda_logo_height = int(zonda_logo_height / scaling_factor)

    zonda_logo = zonda_logo.resize((zonda_logo_width, zonda_logo_height))

    # Convert to RGBA if needed (i.e. add alpha channel)
    if zonda_logo.mode != 'RGBA':
        zonda_logo = zonda_logo.convert('RGBA')

    # Add the logo
    border_offset = 15
    plot_image.paste( zonda_logo,
                      ( plot_image_width  - zonda_logo_width  - border_offset,
                        plot_image_height - zonda_logo_height - border_offset ),
                      zonda_logo
    )

    plot_image.save(output_filepath)

    logging.info(f"Topography plot completed")