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

from utilities.utilities import LOG_INDENTATION_STR, compute_resolution_from_rnbk

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


    def visualize_extpar_variables(self, extpar_plots_config, grid_filepath, extpar_filepath, grid_resolution, output_dir, logging_indentation_level=0):
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
        grid_data_vars = grid_dataset.data_vars

        longitude_vertices = np.rad2deg(grid_data_vars["longitude_vertices"].values)
        latitude_vertices = np.rad2deg(grid_data_vars["latitude_vertices"].values)
        longitude_centers = np.rad2deg(grid_data_vars["lon_cell_centre"].values)

        vertices_of_cells = grid_data_vars["vertex_of_cell"].T.values - 1 
        cells_of_vertices = grid_data_vars["cells_of_vertex"].T.values - 1

        n_vertices = len(cells_of_vertices)

        data_crossing_dateline = False

        # Add vertices at boundaries to allow for correct wrapping of triangular mesh around (periodic) boundaries
        boundary_degrees = 180.0
        delta_degrees = 3.0 * grid_resolution
        longitude_vertices_abs = np.abs(longitude_vertices)
        vertices_at_boundary_mask = (longitude_vertices_abs >= boundary_degrees - delta_degrees)
        if any(vertices_at_boundary_mask):
            logging.info(f"{LOG_INDENTATION_STR*(logging_indentation_level+1)}Create new vertices at the boundaries to account for periodicity.")

            cells_at_boundary = np.unique(cells_of_vertices[vertices_at_boundary_mask].flatten())
            index_to_delete = np.argwhere(cells_at_boundary == -1)
            cells_at_boundary = np.delete(cells_at_boundary, index_to_delete)

            tmp_longitudes = []
            tmp_latitudes = []
            new_vertex = n_vertices
            for cell in cells_at_boundary:
                vertices_of_current_cell = vertices_of_cells[cell].copy()

                for i, vertex in enumerate(vertices_of_current_cell):
                    if abs(longitude_vertices[vertex] - longitude_centers[cell]) > 180.0:
                        tmp_longitudes.append(longitude_vertices[vertex] + np.sign(longitude_centers[cell]) * 360.0)
                        tmp_latitudes.append(latitude_vertices[vertex])

                        vertices_of_cells[cell][i] = new_vertex

                        new_vertex += 1

                        if not data_crossing_dateline:
                            data_crossing_dateline = True

            longitude_vertices = np.append(longitude_vertices, np.asarray(tmp_longitudes))
            latitude_vertices = np.append(latitude_vertices, np.asarray(tmp_latitudes))

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
                logging.error( f"The visualization of EXTPAR variables only supports 1D data/slices (i.e., only the cells dimension)! "
                               f"The data/slice for variable \"{variable_name}\" has {data_ndim} dimensions. "
                               f"Please select a specific index for each additional dimension via the "
                               f"\"extpar_plots\" entry in the JSON config." )
                raise ValueError( f"The visualization of EXTPAR variables only supports 1D data/slices! "
                                  f"The data/slice for variable \"{variable_name}\" has {data_ndim} dimensions." )

            long_name = variable.attrs.get("long_name", variable_name).capitalize()
            units = variable.attrs.get("units", "")

            data_min = data.min()
            data_max = data.max()

            # Mask data over water cells based on land fraction values
            if variable_name in self.variables_to_mask_over_water:
                fr_land_variable_name = "FR_LAND"
                fr_land_data = extpar_dataset[fr_land_variable_name].values

                data[np.logical_and(fr_land_data == 0., data == 0.)] = None

            # Create figure and axis
            fig = plt.figure(figsize=(16, 9), dpi=self.dpi)

            if data_crossing_dateline:
                ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=180))

                longitude_vertices_360 = np.where(longitude_vertices < 0.0, longitude_vertices + 360.0, longitude_vertices)

                longitude_vertices_360_min = np.min(longitude_vertices_360)
                longitude_vertices_360_max = np.max(longitude_vertices_360)
                domain_width = abs(longitude_vertices_360_max - longitude_vertices_360_min)
                x_offset = 0.1 * domain_width

                latitude_vertices_min = np.min(latitude_vertices)
                latitude_vertices_max = np.max(latitude_vertices)
                domain_height = abs(latitude_vertices_max - latitude_vertices_min)
                y_offset = 0.1 * domain_height

                x_min = max(longitude_vertices_360_min - x_offset, 0.0)
                x_max = min(longitude_vertices_360_max + x_offset, 360.0)
                y_min = max(latitude_vertices_min - y_offset, -90.0)
                y_max = min(latitude_vertices_max + y_offset, 90.0)

                ax.set_extent([x_min, x_max, y_min, y_max], crs=ccrs.PlateCarree())
            else:
                ax = plt.axes(projection=ccrs.PlateCarree())

            indices_str = ""
            if indices_per_dim:
                indices_str = " with " + ", ".join(f"{key}={value}" for key, value in indices_per_dim.items())

            figure_title = f"{long_name} ({variable_name}{indices_str})"
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
            collection = ax.tripcolor( longitude_vertices, latitude_vertices, data,
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
            units_str = f"({units})" if units else ""
            colorbar.set_label(f"{units_str}", **self.small_font)
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

            # Convert to RGBA if needed (i.e., add alpha channel)
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


    def visualize_data(self, nesting_group, grid_dirs, grid_filenames, extpar_dirs, logging_indentation_level=0):
        for domain_id in nesting_group:
            domain_idx = domain_id - 1

            logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level}Visualization of data for domain {domain_id}.")

            extpar_dir = extpar_dirs[domain_idx]

            if extpar_dir is not None:
                domain_config = self.domains_config[domain_idx]
                extpar_plots_config = domain_config.get("extpar_plots", [])

                if len(extpar_plots_config) > 0:
                    grid_filepath = os.path.join(grid_dirs[domain_idx], grid_filenames[domain_idx])
                    extpar_filepath = os.path.join(extpar_dir, "external_parameter.nc")

                    globals_config = self.config["globals"]
                    n = globals_config["grid_root"]
                    k = globals_config["grid_level"] + domain_idx
                    grid_resolution = compute_resolution_from_rnbk(n, k, units="deg")

                    self.visualize_extpar_variables(extpar_plots_config, grid_filepath, extpar_filepath, grid_resolution, extpar_dir, logging_indentation_level=logging_indentation_level+1)
                else:
                    logging.warning(f"No EXTPAR variable was requested for visualization for domain {domain_id}. Skipping visualization of EXTPAR variables!")
            else:
                logging.warning(f"No EXTPAR directory was found for domain {domain_id}, likely because the EXTPAR step was skipped. Skipping visualization of EXTPAR variables!")