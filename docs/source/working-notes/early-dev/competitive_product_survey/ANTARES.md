# ANTARES

###### The Arizona-NOAO Temporal Analysis and Response to Events System



## Overview

*"The primary goal of the ANTARES prototype is to recognize ‘interesting’ alerts that are uncharacteristic of known kinds of transients and variables so that follow-up observations for further elucidation (which are likely to be time-critical) can be done as soon as permissible."*



- Only forwards alerts that pass image-quality tests.  
  - Real bogus score `ztf_rb` < 0.55 are ignored

  - Alerts with bad pixels (`ztf_nbad` > 0) or a large difference in aperture vs PSF magnitudes (`ztf_magdiff` outside of the range -0.1 to 0.1) are ignored. 
  - Alerts with poor seeing (`ztf_fwhm` > 5.0 arcsec) or elongated sources (`ztf_elong` > 1.2) are ignored 
- All alerts, regardless of the above cuts, are stored in case they are needed for future processing.
- Waits for two detections to run science since alerts with only one detection are likely to be unknown Solar System objects
- Associates each alert with the nearest point of known past measurements in a 1" radius. (The `Locus`)



## Services

- A search engine for the alerts database 
- Slack notifications of new alerts in your stream/watchlist of interest (Done)
- Object watchlists ([Done](http://antares.noao.edu/watchlist))
- Ability to add custom Python filters directly through their website ([Done](http://antares.noao.edu/filters))
- A DevKit to develop custom filters ([Done](https://github.com/noaodatalab/notebooks-latest/blob/master/05_Contrib/TimeDomain/AntaresDevKit/AntaresFilterDevKit.ipynb))
- Filters and analysis on the alerts DB can be run in NOAO DataLab's Jupyter environment
  - Expressed as Python functions
  - Filters are submitted to ANTARES and revied. Every filter has a unique name and creates a new Kafka topic with that name.



## Architecture

- Alerts are ingested and then cross-matched and associated with previously discovered objects. Any alerts associated with more than one object can be replicated to consider each association
  - Object association with the AstroObject Database is performed by calculating each object’s 20-digit index on a hierarchical triangular mesh (HTM, Kunszt et al., 2001) used to cover the sphere (Szalay et al., 2007). The quad-tree search of the HTM is implemented in SciSQL. Association radii are different for the various astronomical catalogs, as the resolution of surveys in different regions of the electromagnetic spectrum can vary by orders of magnitude.
- To determine if an object is interesting, it is compared against the *Touchstone* (defined below) using a variation of the nearest-neighbor search. 
- As part of ranking alerts, objects fall into four categories: known-knowns, known-unknowns, unknown-knowns, and unknown-unknowns.
  - known-knowns: We have seen before and understand.
  - Known-unknowns: Predicted to exist that have not yet been observed. 
  - Unknown-knowns: Objects observed, but not yet understood. 
  - Unknown-unknowns: Newly discovered, unpredicted objects.
- Alerts are then passed through filters and sent out to the alert streams.
- Each alert is treated independently. Spatially correlated alerts (such as multiply lensed systems or extended objects like light echoes) will have to be evaluated in a different system. Moving objects are also not considered.
- The majority of alerts will come from repeat variables within the Galaxy. These are diverted from the main stream.
- Databases include:
  1. **Aggregated AstroObject Catalog**: Represents current astronomical knowledge. This information is used to annotate the incoming alerts with relevant data if the alert can be associated with a known object
  2. **Locus-Aggregated Annotated Alerts**: All alerts processed by ANTARES with annotations, including AstroObject association, feature derivation, and filtering results.
  3. **Touchstone**: A database of properties and features for known or predicted kinds of variable astronomical sources based on the Kepler survey and eventually Gaia.
  4. **Annotated Coalesced Alerts**: Database of all alerts processed by ANTARES with annotations and ranking 
  5. A few others that are not relevant here.



## Example Use Cases

1. **Counterparts to Gravitational Wave Sources**: There is extensive literature predicting the optical characteristics of a GW source. For an aLIGO alert, the expectation is that there will not be a previously detected source, but that there will be a host galaxy. There may not be enough information from early, limited observations, so a list of likely alerts may be produced, rather than a single, sure thing. 50% of aLIGO events will have localizations ≤ 20 square degrees. LSST has a 10 square degree field-of-view. 

2. **Tidal Disruption Events (TDEs)**: If a star moves too close to a massive black hole, the tidal forces can essentially rip it apart. These TDEs will also appear as alerts in the LSST data stream with characteristics quite similar to AGN.

3. **Supernovae on Demand**: Submit an ANTARES filter that will yield only SN, potentially in a specific region of the sky.



## Value-added Products

Primarily forwarding value the raw ZTF alerts with the addition of some internal bookkeeping data and crossmatching. Work is underway to add real-time classifications of transient sources. For more information see [The ZTF Science Data System (ZSDS) Explanatory Supplement](http://web.ipac.caltech.edu/staff/fmasci/ztf/ztf_pipelines_deliverables.pdf) (page 60).



## Links

#### Websites

1. [ANTARES Webpage](https://antares.noao.edu)
2. [Python Alerts Developer Kit](https://github.com/noaodatalab/notebooks-latest/blob/master/05_Contrib/TimeDomain/AntaresDevKit/AntaresFilterDevKit.ipynb)

#### Project Documents

1. [Project Overview](https://www.noao.edu/noao/staff/matheson/ANTARES-Introduction.pdf)
2. [Architecture Outline](https://www.noao.edu/noao/staff/matheson/ANTARES-Architecture.pdf)
3. [Example Use Cases](https://www.noao.edu/noao/staff/matheson/ANTARES-Usecases.pdf)
4. [Development Plans](https://www.noao.edu/noao/staff/matheson/ANTARES-Development.pdf)

#### Publications

1. [ANTARES: A Prototype Transient Broker System (Saha et al. 2014)](https://arxiv.org/abs/1409.0056)

2. [ANTARES: Progress towards building a ‘Broker’ of
   time-domain alerts (Saha et al. 2016)](https://arxiv.org/abs/1611.05914)

3. [Machine Learning-based Brokers for Real-time Classification of the LSST Alert Stream (Narayan et al. 2018)](https://arxiv.org/abs/1801.07323)

   
