# terrainHydrology

This is a terrain generator inspired by 2013 paper "Terrain Generation Using Procedural Models Based on Hydrology". It is developed by Laith Siriani and Zachariah Wat.

![Example Terrain](example/out/out-color.png)

## About

Most ontogenetic approaches to procedural terrain (Perlin noise, midpoint displacement, etc) produce results that, although generally better than man-made maps, are nonetheless unnatural. Real terrain contains very few local minima, and is not evenly fractal at all scales. Teleological algorithms can help, but may not be performant, especially when simulating small-scale processes over large maps.

The approach described in Genevaux et al is an ontogenetic approach that is meant to more closely approximate features of terrain on a sub-regional scale. On this scale, terrain is strongly shaped by the flow of water---even in dry landscapes. Thus, the approach of this algorithm is to generate the hydrological network first, and then generate terrain features from that. The approach is reasonably fast (or, at least, it can be) compared to an equivalent teleological approach, and the results are fairly convincing. Moreover, the user is allowed a great deal of control over the output by controlling the shoreline and the slope of rivers and the surrounding terrain.

## Usage

The workflow for using this program begins with the preparation of inputs. This consists of 2 maps and 1 ESRI shapefile that demarcate the shape of the landmass and the general nature of the terrain.

Then, the terrain is generated. The result of this process is a SQL database that describes the terrain. This database is intended to be read directly. It can be queried directly, but can also be imported into GIS software, such as QGIS, which can not only display the data in maps, but can perform any other kind of GIS data task.

However, this program also includes 2 subcommands that can export this database into other formats, such as ESRI shapefiles and GeoTIFF digital elevation models.

### `hydrology-visualize.py`

![A portion of the terrain visualized. The edges of the hydrology graph are weighted for flow. Cells are colored according to the cell node's elevation.](example/out/visualize.jpg)

This script will visualize certain components of the data model. This can be useful for debugging or adding new features.

The background can either be an outline of the shore, or the cells can be color coded for the Voronoi cell ID, or color coded for the height of the cell node's elevation.

The terrain primitives can be displayed as well as the interpolated paths of the rivers.

The hydrology network can be visualized. The edges can be weighted according to river flow, if desired.

Switch | Notes
------ | -----
`-xl`, `--lower-x` | x lower bound
`-yl`, `--lower-y` | y lower bound
`-xu`, `--upper-x` | x upper bound
`-yu`, `--upper-y` | y upper bound
`--river-heights` | river height cells as background
`--voronoi-cells` | voronoi cells as background
`--terrain-primitives` | show terrain primitives
`--river-paths` | show rivers
`--hydrology-network` | show hydrology network
`--hydrology-network-flow` | show hydrology network with
`-o` | The path+name of the image to write

### `hydrology-riverout.py`

This script will read the data model and write an ESRI shapefile that shows the paths of the rivers over the terrain.

Switch | Notes
------ | -----
`-i` | The file that contains the data model you wish to interpret
`--lat` | This is the center latitude of the output shapefile
`--lon` | This is the center longitude of the output shapefile
`-o` | The path and name of the output shapefile

Note that an ESRI shapefile actually consists of multiple files. For example, if you specify the name `example`, this script will write the files `example.shp`, `example.shx`, `example.dbf`, and `example.prj`. These files should be kept together.

### `hydrology-nodeout.py`

This script will read the data model and write an ESRI shapefile that depicts all the nodes in the hydrology network, along with their associated data.

Switch | Notes
------ | -----
`-i` | The file that contains the data model you wish to interpret
`--lat` | This is the center latitude of the output shapefile
`--lon` | This is the center longitude of the output shapefile
`-o` | The path and name of the output shapefile

Note that an ESRI shapefile actually consists of multiple files. For example, if you specify the name `example`, this script will write the files `example.shp`, `example.shx`, `example.dbf`, and `example.prj`. These files should be kept together.

### Example

```
src/hydrology.py -g example/in/gamma.png -s example/in/riverslope.png -t example/in/terrainslope.png -ri 100 -p 50 -o example/out/data
```

```
src/hydrology-render.py -i example/out/data --lat 43.2 --lon -103.8 -ro 500 -o example/out/
```

```
src/hydrology-visualize.py -i example/out/data -g example/in/gamma.png -xl 60000 -xu 100000 -yl 60000 -yu 120000 --river-heights --hydrology-network-flow -o example/out/visualize.jpg
```

## Documentation

Documentation for developers and "power users" can be found in the `doc` directory. Documentation is powered by Sphinx.

To generate the documentation, install Sphinx and run

> make html

or

> make pdf

For HTML documentation, you will need to install the readthedocs.org theme.

To generate PDF documentation, you will need the LaTeX toolchain.

## Native module

There are two native modules that can greatly accelerate the process of generating terrain. One module is designed to generate the river network. The other is designed to compute the elevations of terrain primitives. Both modules use OpenMP to perform their computations in parallel, and both must be compiled. They were developed on Fedora and have been tested on Ubuntu. In the `src` directory, use `make buildRivers` and `make terrainPrimitives` to build the module, and use the `--accelerate` flag to use them.

### Dependencies for the native module

#### Libraries

To compile the module, you will need the OpenCV library and the necessary header files. On Ubuntu (and hopefully other Debian-based systems), you can use

> `apt install libopencv-dev`
> `apt install libgeos-dev`

On Fedora and RPM-based distributions, these commands should suffice

> `dnf install opencv-devel`
> `dnf install geos-devel`

You will also need OpenMP. It seems to come with Ubuntu and Fedora, but it's also widely available in package repositories.

#### Google Test

To build the test binary, you will need the Google Test repository in the `src/tst` directory. Use `git clone` to clone the `googletest` repository into `src/tst` (the repository is hosted on GitHub).

### Documentation for the native module

Documentation for the native module is powered by Doxygen. To generate the documentation, go to the `doc-native` directory and run

> `doxygen`

## General dependencies and citations

### Standard repositories

These Python dependencies should be available through most package managers.

* Scipy
* Matplotlib
* OpenCV
* Networkx
* Shapely
* tqdm
* Rasterio

NOTE: I had trouble getting Scipy to work on a fresh Ubuntu install. I fixed it by uninstalling it with `apt` and reinstalling it with `pip`.

### Poisson.py

Poisson.py is a modified version of the Possion.py in this repository:

> [https://github.com/bartwronski/PoissonSamplingGenerator](PoissonSamplingGenerator)

### Original paper

The original paper is cited as follows:

> Jean-David Genevaux, Eric Galin, Eric Guérin, Adrien Peytavie, Bedrich Benes. Terrain Generation Using Procedural Models Based on Hydrology. ACM Transactions on Graphics, Association for Computing Machinery, 2013, 4, 32, pp.143:1-143:13. ￿10.1145/2461912.2461996￿. ￿hal-01339224￿