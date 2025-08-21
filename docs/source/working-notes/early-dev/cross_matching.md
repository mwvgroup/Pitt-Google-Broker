# docs/source/working-notes/early-dev/cross_matching.md

## To Do
- [ ] Start with [astroquery](https://astroquery.readthedocs.io/en/latest/)


## Astroquery
<!-- fs -->
[astroquery](https://astroquery.readthedocs.io/en/latest/)
"Astroquery is a set of tools for querying astronomical web forms and databases... All astroquery modules are supposed to follow the same API. In its simplest form, the API involves queries based on coordinates or object names."

### astroquery.xmatch
[XMatch Getting started](https://astroquery.readthedocs.io/en/latest/xmatch/xmatch.html#module-astroquery.xmatch)
[XMatchClass](https://astroquery.readthedocs.io/en/latest/api/astroquery.xmatch.XMatchClass.html#astroquery.xmatch.XMatchClass.query)
XMatch uses the CDS xMatch service: [CDS xMatch service documentation](http://cdsxmatch.u-strasbg.fr/xmatch/doc/)

### install:
``` bash
conda install -c astropy astroquery
```

<!-- fe Astroquery -->



## Possible XM Tools
<!-- fs -->

- [ ] Start with [astroquery](https://astroquery.readthedocs.io/en/latest/)


### Summary of tools

"Astronomical data fusion tool based on PostgreSQL" would be great, but I can't actually find the software.

[VizieR](http://vizier.u-strasbg.fr/) is a library with 18538 (currently) catalogs available. Other tools (e.g. CDS XMatch Service) use this.

mcatCS is very new, in C++, supposedly fast. Probably not what we want to start with, but may want to consider for future implementation.

Probably the best options (see below for details):
- [The CDS cross-match service](http://cdsxmatch.u-strasbg.fr/) (web app)
- "Pei (2011) and Pei et al. (2011)
- [The Large Survey Database (LSD)](http://research.majuric.org/public/project/lsd/) (python)


### Tools details
<!-- fs -->

- [ ] mcatCS: (multi-band catalog Cross-matching Scheme, 2019)
    + [paper](https://iopscience.iop.org/article/10.1088/1538-3873/ab024c/pdf)
    + [git repo](https://github.com/libingyao/mcatCS)
    + "a distributed cross-matching scheme to efficiently integrate celestial object data from billion-row multi-band astronomical catalogs. It is deployed on a cluster of commodity machines and provides a command-line-based interface to the end user."
    + "experimental results show that the query response speed is 38% to 45% greater than that of MongoDB and 21% to 32% greater than that of PostgreSQL with the HEALPix B-tree index"
    + C++

- [Astronomical data fusion tool based on PostgreSQL](https://arxiv.org/pdf/1609.01079.pdf)
    + __This would be great, but I can't actually find the software__.
    + "In this paper we introduce a cross-match tool that is developed in the _Python_ language, is based on the PostgreSQL database and uses Q3C as the core index, facilitating the cross-match work of massive astronomical data. It provides four different cross- match functions, namely: (I) cross-match of the custom error range; (II) cross-match of catalog errors; (III) cross-match based on the elliptic error range; (IV) _cross-match of the nearest neighbor algorithm_. The resulting cross-matched set provides a good foundation for subsequent data mining and statistics based on multiwavelength data. The most advantageous aspect of this tool is a user-oriented tool applied locally by users. By means of this tool, _users can easily create their own databases, manage their own data and cross-match databases according to their requirements_. In addition, this tool is also able to transfer data from one database into another database. More importantly, it is easy to get started with the tool and it can be used by astronomers without writing any code." (emphasis added)

- [VizieR](http://vizier.u-strasbg.fr/) "VizieR provides the most complete library of published astronomical catalogues --tables and associated data-- with verified and enriched data, accessible via multiple interfaces. Query tools allow the user to select relevant data tables and to extract and format records matching given criteria. Currently, 18538 catalogues are available"
    + __Other tools use this library (e.g. CDS XMatch service)__
    + "operated at CDS, Strasbourg, France, _provides access to the most complete library of published astronomical catalogs and data tables available on line, and is organized in a self-documented database_. Query tools allow the user to select relevant data tables and to extract and format records matching given criteria. However, _cross-matching only supports a small number of records_." quoted from Han+16
    + "TAPVizieR is a new way to access the VizieR database using the ADQL language and the TAP protocol (Landais et al. 2013). The database is based on PostgreSQL and the sky indexation depends on HEALPix. TAPVizieR provides query and cross-match functions. The resulting access is only limited to an owner as recognized by the associated IP address which is saved for no more than 5 days. The execution time of an ADQL query is limited to 5 hours." quoted from Han+16

- [SIMBAD](http://simbad.u-strasbg.fr/simbad/) "is an astronomical database also operated at CDS, Strasbourg, France, which provides _basic data, cross-identifications, bibliography and measurements for astronomical objects outside the solar system_ (Wenger et al. 2000). SIMBAD has many kinds of query modes, such as object name, coordinates and various criteria. SIMBAD also provides links to some other on line services. Users may submit lists of objects and scripts to query. Similar to VizieR, the number of lists cannot be large." quoted from Han+16

- [The NASA Extragalactic Database (NED)](http://www.ned.ipac.caltech.edu/), "managed by NASA, _contains names, positions and a variety of other data on extragalactic objects, as well as bibliographic references to published papers, and notes from catalogs and other publications_. NED may be searched for objects in many ways, including by name, positions, redshifts, types or by object classifications. NED also offers a number of other tools and services. If users want to query a large number of objects, they may submit a NED Batch Job, and retrieve the results at Pick Up Batch Job Results. NED provides another batch query, i.e. one right ascension (RA) and declination (Dec) position or object name per line, with a maximum of 500 positions and/or object names per request." quoted from Han+16

- [The Tool for OPerations on Catalogues And Tables (TOPCAT)](http://www.star.bris.ac.uk/∼mbt/topcat/) "is an interactive graphical viewer and editor for tabular data (Taylor 2005). It offers a variety of ways to view and analyze tables, including a browser for the cell data themselves, viewers for information about table and column metadata, and facilities for sophisticated interactive 1-, 2-, 3- and higher-dimensional visualization, calculating statistics and joining tables using flexible matching algorithms. It is developed in the _Java_ language and is _limited by computer memory when running. When cross-matching very large tables or tables with lots of columns, the computer is inclined to be out of memory_." quoted from Han+16

- [ ] "TOPCAT’s sister package is the __Starlink Tables Infrastructure Library Tool Set (STILTS)__, which is based on STIL, the Starlink Tables Infrastructure Library. STILTS offers many of the same functions as TOPCAT and forms the command-line counterpart of the Graphical User Interface (GUI) table analysis tool TOPCAT. STILTS is _robust, fully documented and designed for efficiency, especially with very large datasets_." quoted from Han+16

- [ ] [The CDS cross-match service](http://cdsxmatch.u-strasbg.fr/xmatch/)
    + [better link](http://cdsxmatch.u-strasbg.fr/)
    + [documentation PDF](http://cdsxmatch.u-strasbg.fr/xmatch/doc/CDSXMatchDoc.pdf)
    + "is a new data fusion and data management tool, which is used to _efficiently cross-identify sources between very large catalogs (all VizieR tables, SIMBAD) or between a user-uploaded list of positions and a large catalog_ (Boch et al. 2012). About the xMatch algorithm, please refer to Pineau et al. (2011). Users interact with the CDS xMatch service through a Web application. Due to _narrow network bandwidth_, it has some limitations, for example, long jobs are aborted if computation exceeds 100 min while short jobs are aborted if computation exceeds 15 min; the search radius is maximized to 120′′ for a simple cross-match; the cone radius is no more than 15 degrees for a cone search; results are saved for no more than 7 days following their submission. Moreover the total size of uploaded tables is limited to 100 MB for anonymous users and 500 MB for registered users." quoted from Han+16

- "The 2MASS catalog server kit, developed by Yamauchi (2011), acts as a high-performance database server for the 2MASS Point Source Catalog and several other all-sky catalogs. This kit uses the open-source PostgreSQL, adopts an orthogonal xyz coordinate system as the database index and applies other techniques (table partitioning, composite expression index and optimization in stored functions) to enable _high-speed search and cross- match of huge catalogs_." quoted from Han+16

- [ ] "Pei (2011) and Pei et al. (2011) developed a highly-efficient large-scale catalog oriented fusion toolset based on MySQL database and HTM index. Zhang et al. (2012) developed a toolkit for _automated database creation and cross-matching tasks, with which users may create their own databases and easily cross-match catalogs_. Although the cross-match speed is quick, it costs a long time to retrieve the cross-matched result. In other words, the second operation of the matched result is necessary before application." quoted from Han+16

- [ ] [The Large Survey Database (LSD)](http://research.majuric.org/public/project/lsd/) "is a _framework for storing, cross-matching, querying and rapidly iterating through large survey datasets_ (catalogs of > 109 rows, > 1 TB) on multi-core machines. It is implemented in _Python_, and written and maintained by Mario Juric. LSD applies nested butterfly HEALPix pixelization and the catalogs are partitioned into cells in space and time. LSD employs LSD/MapReduce as the high-performance programming model." quoted from Han+16

<!-- fe tools details -->

<!-- fe possible XM tools -->


## Notes from paper: Gaia Data Release 1. Cross-match with external catalogues Algorithm and results
<!-- fs -->

Paper:
Gaia Data Release 1. Cross-match with external catalogues Algorithm and results
P.M. Marrese, S. Marinoni, M. Fabrizio, and G. Giuffrid
2017
Marrese+17

XM = cross matching

### Possible Features

Can match one-to-one, one-to-many, or many-to-one. In the case of identifying host galaxy of supernova we probably want one-to-one?

Most basic XM uses position (RA, DEC, redshift?)

Other possible features to XM on (non-exhaustive, taken from Marrese+17):
- data available (positions, epochs, proper motions, parallaxes, photometry, binary, and/or variability characterisation)
- statistics on accuracy and precision of the data available
- photometric depth (magnitude limit) and completeness
- possible systematic errors on any of the data (astrometry and/or photometry) used in the cross-match
- statistics on the availability of the information within a catalogue (for example how many objects have colour information)
- accuracy of photometric transformations between the two catalogues and their applicability limits
- angular resolution of each catalogue and the resolution difference between the two catalogues.

Gaia uses:
> The chosen algorithm is positional and thus uses positions,
position errors, their correlation if known, and proper motions...
> We produced two separate XM outputs: a BestNeighbour ta-
ble which lists each matched Gaia object with its best neighbour and a Neighbourhood table which includes all good neighbours for each matched Gaia object.

Using magnitudes and/or colors can be tricky because
> The use of magnitudes and colours requires transformations between photometric systems that are usually based on synthetic photometry of normal stars. While using the magnitudes would help matching most of the objects in a given catalogue, it would probably worsen the matching of many relatively rare but very interesting objects such as variables, peculiar stars, and non- stellar objects. In addition, in many surveys not all objects have a colour (i.e. a fraction of objects may have been detected in one band only)

Important consideration:
Many of the possible features can improve matching of generic objects at the cost of poor matching for peculiar objects. My guess is that we will deal with many 'peculiar' objects..?


### Techniques

Possible option: http://docs.astropy.org/en/stable/_modules/astropy/coordinates/matching.html

Gaia uses:
> 3. Gaia pre-computed cross-match: details The algorithm we prepared makes use of a plane-sweep technique which requires the catalogues to be sorted by declination, implies the definition of an active list of objects in the external catalogue for each Gaia object, and allows the input data to be read only once, thus making the XM computation faster...
> In addition, we used a filter and refine technique: a first filter is defined by a large radius centred on a given Gaia object and is used to select neighbours and calculate the local surface density, while a second filter is used to select good neighbours among neighbours...
> The selection of the best neighbour among good neighbours is based on a figure of merit.

Figure of merit:
> The figure of merit (FoM) we used evaluates the ratio between two opposite models/hypotheses, the counterpart candidate (i.e. the good neighbour) is a match or it is found by chance.

<!-- fe notes from Gaia paper -->

### MARS Links

[MARS website](https://mars.lco.global/help/)
[Git Repo](https://github.com/LCOGT/ztf-alert-server)
[Las Cumbres Observatory](https://lco.global/)
