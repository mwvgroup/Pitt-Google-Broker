Paper:
Gaia Data Release 1. Cross-match with external catalogues Algorithm and results
P.M. Marrese, S. Marinoni, M. Fabrizio, and G. Giuffrid
2017
Marrese+17

XM = cross matching

## Possible Features

Can match one-to-one, one-to-many, or many-to-one. In the case of identifying host galaxy of supernova we probably want one-to-one.

Most basic XM uses position (RA, DEC, redshift?)

Other possible features to XM on (non-exhaustive, taken from Marrese+17):
- data available (positions, epochs, proper motions, parallaxes, photometry, binary, and/or variability charac- terisation)
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


## Techniques

Gaia uses:
> 3. Gaia pre-computed cross-match: details The algorithm we prepared makes use of a plane-sweep technique which requires the catalogues to be sorted by declination, implies the definition of an active list of objects in the external catalogue for each Gaia object, and allows the input data to be read only once, thus making the XM computation faster...
> In addition, we used a filter and refine technique: a first filter is defined by a large radius centred on a given Gaia object and is used to select neighbours and calculate the local surface density, while a second filter is used to select good neighbours among neighbours...
> The selection of the best neighbour among good neighbours is based on a figure of merit.

Figure of merit:
> The figure of merit (FoM) we used evaluates the ratio between two opposite models/hypotheses, the counterpart candidate (i.e. the good neighbour) is a match or it is found by chance.
