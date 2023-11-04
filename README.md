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

### Example

Generate a terrain:

```
./hydrology2.py generate --lat 0.0 --lon 0.0 -g example/coastline.shp -s example/riverslope.png -t example/terrainslope.png -ri 93.6 -p 25 --accelerate -o example-out/data
```

Export ridge primitives as an ESRI shapefile:

```
/hydrology2.py export --input example-out/data --lat 0.0 --lon 0.0 --output-ridge-primitive example-out/ridgeprimitives
```

## Native module

There are two native modules that can greatly accelerate the process of generating terrain. One module is designed to generate the river network. The other is designed to compute the elevations of terrain primitives. Both modules use OpenMP to perform their computations in parallel, and both must be compiled. They were developed on Fedora and have been tested on Ubuntu. In the `src` directory, use `make buildRivers` and `make terrainPrimitives` to build the module, and use the `--accelerate` flag to use them.

## Citations

### Poisson.py

Poisson.py is a modified version of the Possion.py in this repository:

> [https://github.com/bartwronski/PoissonSamplingGenerator](PoissonSamplingGenerator)

### Original paper

The original paper is cited as follows:

> Jean-David Genevaux, Eric Galin, Eric Guérin, Adrien Peytavie, Bedrich Benes. Terrain Generation Using Procedural Models Based on Hydrology. ACM Transactions on Graphics, Association for Computing Machinery, 2013, 4, 32, pp.143:1-143:13. ￿10.1145/2461912.2461996￿. ￿hal-01339224￿