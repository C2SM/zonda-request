import os
import logging

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.colors as col
import matplotlib.ticker as tck
import matplotlib.cm as cm
import xarray as xr
import numpy as np
import warnings

from PIL import Image
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.io import DownloadWarning

from utilities.utilities import LOG_INDENTATION_STR

warnings.filterwarnings("ignore", category=DownloadWarning)



class VisualizationManager:

    def __init__(self, config, workspace_path, dpi=560, plots_format="png"):

        self.config = config
        self.workspace_path = workspace_path

        self.dpi = dpi
        self.plots_format = plots_format

        self.domains_config = self.config["domains"]

        self.zonda_logo_filepath = f"{self.workspace_path}/img/zonda_logo.png"

        self.font            = {"family": "DejaVu Serif"            }
        self.small_font      = {"family": "DejaVu Serif", "size": 8 }
        self.code_font       = {"family": "Courier New"             }
        self.legend_settings = {"family": "DejaVu Serif", "size": 10}

        self.variables_to_mask_over_water = [
            "topography_c"
        ]


    def visualize_extpar_variables(self, extpar_plots_config, icontools_config, grid_filepath, extpar_filepath, output_dir, logging_indentation_level=0):
        logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Visualization of EXTPAR variables.")

        ##################################
        ### Get and transform the data ###
        ##################################

        # Read NetCDF files (field values and grid data)
        logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)}Read EXTPAR file: \"{extpar_filepath}\".")
        extpar_dataset = xr.open_dataset(extpar_filepath)

        logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)}Read grid file: \"{grid_filepath}\".")
        grid_dataset = xr.open_dataset(grid_filepath)

        # Get the necessary data
        grid_coords = grid_dataset.coords
        grid_data_vars = grid_dataset.data_vars

        vertex_longitudes = np.rad2deg(grid_coords["vlon"].values)
        vertex_latitudes = np.rad2deg(grid_coords["vlat"].values)

        vertices_of_cells = grid_data_vars["vertex_of_cell"].T.values - 1 
        cells_of_vertices = grid_data_vars["cells_of_vertex"].T.values - 1

        n_vertices = len(cells_of_vertices)

        region_type = icontools_config["region_type"]
        data_crossing_dateline = False
        if (region_type == 2):
            center_lon = icontools_config.get("center_lon", 0.0)
            radius = icontools_config.get("radius", 0.0)

            if (abs(center_lon) + radius > 180.0):
                data_crossing_dateline = True

                offset_percentage = 0.1
                x_offset = 2.0 * radius * offset_percentage
                y_offset = x_offset

        elif (region_type == 3):
            center_lon = icontools_config.get("center_lon", 0.0)
            hwidth_lon = icontools_config.get("hwidth_lon", 0.0)
            hwidth_lat = icontools_config.get("hwidth_lat", 0.0)

            if (abs(center_lon) + hwidth_lon > 180.0):
                data_crossing_dateline = True

                offset_percentage = 0.1
                x_offset = 2.0 * hwidth_lon * offset_percentage
                y_offset = 2.0 * hwidth_lat * offset_percentage

        if (data_crossing_dateline):
            vertex_longitudes_360 = np.where(vertex_longitudes < 0.0, vertex_longitudes + 360.0, vertex_longitudes)
            vertex_longitudes_360_min = np.min(vertex_longitudes_360)
            vertex_longitudes_360_max = np.max(vertex_longitudes_360)

            vertex_latitudes_min = np.min(vertex_latitudes)
            vertex_latitudes_max = np.max(vertex_latitudes)

        # Add vertices at boundaries to allow for correct wrapping of triangular mesh around (periodic) boundaries
        boundary_degrees = 180.0
        delta_degrees = 0.1
        vertex_longitudes_abs = np.abs(vertex_longitudes)
        vertices_at_boundary_mask = (vertex_longitudes_abs >= boundary_degrees - delta_degrees) & (vertex_longitudes_abs <= boundary_degrees)
        if any(vertices_at_boundary_mask):

            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)}Create new vertices at the boundaries to account for periodicity.")

            cells_at_boundary = np.unique(cells_of_vertices[vertices_at_boundary_mask].flatten())
            index_to_delete = np.argwhere(cells_at_boundary == -1)
            cells_at_boundary = np.delete(cells_at_boundary, index_to_delete)

            tmp_longitudes = []
            tmp_latitudes = []
            new_vertex = n_vertices
            for cell in cells_at_boundary:
                vertices = vertices_of_cells[cell].copy()

                for i, vertex in enumerate(vertices):

                    if vertex_longitudes[vertex] < 0.0:
                        tmp_longitudes.append(vertex_longitudes[vertex] + 360.0)
                        tmp_latitudes.append(vertex_latitudes[vertex])

                        vertices_of_cells[cell][i] = new_vertex

                        new_vertex += 1

            vertex_longitudes = np.append(vertex_longitudes, np.asarray(tmp_longitudes))
            vertex_latitudes = np.append(vertex_latitudes, np.asarray(tmp_latitudes))

        ################################
        ### Plot the requested field ###
        ################################

        for variable_config in extpar_plots_config:
            variable_name = variable_config["variable_name"]

            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)}Plot \"{variable_name}\".")

            indices_per_dim = variable_config.copy()
            indices_per_dim.pop("variable_name")
            variable = extpar_dataset[variable_name].isel(**indices_per_dim)

            data = variable.values[:]
            data_ndim = data.ndim
            if data_ndim != 1:
                logging.error( f"The visualization of EXTPAR variables only supports 1D data/slices (i.e. only the cells dimension)! "
                               f"The data/slice for variable \"{variable_name}\" has {data_ndim} dimensions. "
                               f"Please select a specific index for each additional dimension via the "
                               f"\"extpar_plots\" entry in the JSON config." )
                raise ValueError( f"The visualization of EXTPAR variables only supports 1D data/slices! "
                                  f"The data/slice for variable \"{variable_name}\" has {data_ndim} dimensions." )

            long_name = variable.attrs["long_name"].capitalize()
            units = variable.attrs["units"]

            data_min = data.min()
            data_max = data.max()

            # Mask data over water cells based on land fraction values
            if variable_name in self.variables_to_mask_over_water:
                fr_land_variable_name = "FR_LAND"
                fr_land_data = extpar_dataset[fr_land_variable_name].values

                data[np.logical_and(fr_land_data == 0., data == 0.)] = None

            # Create figure and axis
            fig = plt.figure(figsize=(16, 9), dpi=self.dpi)

            if (data_crossing_dateline):
                ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=180))

                x_min = max(vertex_longitudes_360_min - x_offset, 0.0)
                x_max = min(vertex_longitudes_360_max + x_offset, 360.0)
                y_min = max(vertex_latitudes_min - y_offset, -90.0)
                y_max = min(vertex_latitudes_max + y_offset, 90.0)
                ax.set_extent([x_min, x_max, y_min, y_max], crs=ccrs.PlateCarree())
            else:
                ax = plt.axes(projection=ccrs.PlateCarree())

            figure_title = f"{long_name} ({variable_name})"
            ax.set_title(figure_title, **self.font)

            # Draw custom map on axis and lines delimiting coasts
            ax.coastlines(linewidth=0.5)

            terrain_colormap = cm.terrain
            colormap = col.LinearSegmentedColormap.from_list("modified_terrain", terrain_colormap(np.arange(60,256)))
            colormap.set_bad(color="lightblue")

            plotting_options = {
                "antialiaseds": False,
                "edgecolors": "none",
                "rasterized": True,
                "alpha": None
            }

            # Plot the triangular mesh with the faces colored according to the requested field
            collection = ax.tripcolor( vertex_longitudes, vertex_latitudes, data,
                                       triangles = vertices_of_cells,
                                       cmap = colormap,
                                       vmin = data_min,
                                       vmax = data_max,
                                       transform = ccrs.PlateCarree(),
                                       **plotting_options
            )

            # Draw gridlines at specific longitudes and latitudes
            gridlines = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=0.5, color="black", alpha=1., linestyle="solid")
            gridlines.top_labels = False
            gridlines.left_labels = False
            gridlines.xformatter = LONGITUDE_FORMATTER
            gridlines.yformatter = LATITUDE_FORMATTER
            gridlines.xlabel_style = self.small_font
            gridlines.ylabel_style = self.small_font

            # Create colorbar with transparency
            colorbar_formatter = tck.ScalarFormatter(useMathText=True)
            colorbar_formatter.set_powerlimits((0, 0))

            colorbar = plt.colorbar(collection, shrink=0.3, format=colorbar_formatter)
            colorbar.set_label(f"{long_name} ({units})", **self.font)
            colorbar.ax.yaxis.get_offset_text().set_font(self.small_font)
            plt.setp(colorbar.ax.yaxis.get_ticklabels(), **self.font)

            # Save and close the figure
            output_filepath = os.path.join(output_dir, f"{variable_name}.{self.plots_format}")

            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+2)}Save plot to \"{output_filepath}\".")
            fig.savefig(output_filepath, bbox_inches="tight", dpi=self.dpi)

            plt.close(fig)

            # Add the Zonda logo to the plot
            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+2)}Add Zonda logo to \"{output_filepath}\".")

            zonda_logo = Image.open(self.zonda_logo_filepath)
            plot_image = Image.open(output_filepath)

            plot_image_width, plot_image_height = plot_image.size
            zonda_logo_width, zonda_logo_height = zonda_logo.size

            # Resize the logo
            scaling_factor = 3.5

            zonda_logo_width = int(zonda_logo_width / scaling_factor)
            zonda_logo_height = int(zonda_logo_height / scaling_factor)

            zonda_logo = zonda_logo.resize((zonda_logo_width, zonda_logo_height))

            # Convert to RGBA if needed (i.e. add alpha channel)
            if zonda_logo.mode != "RGBA":
                zonda_logo = zonda_logo.convert("RGBA")

            # Add the logo
            border_offset = 15
            plot_image.paste( zonda_logo,
                              ( plot_image_width  - zonda_logo_width  - border_offset,
                                plot_image_height - zonda_logo_height - border_offset ),
                              zonda_logo
            )

            plot_image.save(output_filepath)

            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+2)}Plot completed.")


    def visualize_data(self, nesting_group, grid_sources, grid_dirs, grid_filenames, extpar_dirs, logging_indentation_level=0):
        for domain_id in nesting_group:
            domain_idx = domain_id - 1

            logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Visualization of data for domain {domain_id}.")

            if grid_sources[domain_idx] == "icontools":
                domain_config = self.domains_config[domain_idx]
                icontools_config = domain_config["icontools"]
                extpar_plots_config = domain_config.get("extpar_plots", [])

                if len(extpar_plots_config) > 0:
                    grid_filepath = os.path.join(grid_dirs[domain_idx], grid_filenames[domain_idx])
                    extpar_filepath = os.path.join(extpar_dirs[domain_idx], "external_parameter.nc")

                    self.visualize_extpar_variable(extpar_plots_config, icontools_config, grid_filepath, extpar_filepath, extpar_dirs[domain_idx], logging_indentation_level=logging_indentation_level+1)
                else:
                    logging.warning(f"No EXTPAR variable was requested for visualization for domain {domain_id}. Skipping visualization of EXTPAR variables!")
            else:
                logging.warning(f"An input grid was provided for domain {domain_id}. Skipping visualization of EXTPAR variables!")