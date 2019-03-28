# Lasair Overview

## Primary Goals

1. Ingest the ZTF public alert stream into a relational database
2. Condense the alerts into possible objects
3. Produce lightcurves of these objects and reliable cross-matches to star and galaxy catalogs for possible follow-up

## Assorted Info

- Lasair = “flare” or “flash” in Scots and Irish gaelic
- The transient alerts broker for the LSST: UK collaboration
- Currently testing using the ZTF alert stream

- Databases saved on hardware in Edinburgh
- Can be viewed and queried through a web browser via a full SQL search engine
- Registration to their website is free, optional, and publically available

- Registered users can save useful SQL queries either privately or publically; public saves are called “streams”
  - Both the Lasair team and users can curate scientifically interesting substreams
  - Ex: nuclear transients and TDE candidates
  - Ex: SNe candidates—all objects NOT classified as a variable star, AGN, or CV and are not coincident with a Pan-STARRS stellar source

## Data Products

3 SQL tables as data products

1. **candidates**: photometric data from each ZTF alert
2.    **objects**: metadata for collected alerts:
  - Group of 3+ candidates with the same object ID number
    - ZTF assigns this same object ID number if the positions agree within 1.5” (check this number)
    - Requiring 3+ is done to remove moving objects and reduce bogus detections
  - Min, Max, and Average magnitudes
  - Earliest and latest dates of detection
  - Mean coordinates
  - All *objects* data is in the *candidates* table, but not all of the *candidates* table makes it into the *objects* table
3.    **sherlock_crossmatches**: value-added classification info created using Sherlock
  - Crossmatches nearby sources with various catalogs for their corresponding photometry and spec/photo z’s
  - Sherlock: uses star/galaxy separation methods, estimated distances, and galaxy offsets to classify the objects into a few possible categories:
    - Supernovae
    -  Nuclear transients
    -  Variable stars
    - AGN (Véron-Cetty and Véron 2010)
    - CV (Downes et al. 2001, Ritter and Kolb 2003)
    - Orphans: stationary, transient sources that aren’t associated with a cataloged star or galaxy
  - Maintains an up-to-date crossmatch with the IAU Transient Name Server to quickly identify known transients within the ZTF stream

## Searching Lasair

  - Can use SQL SELECT queries to search their provided tables
  - Few different types of search methods:
    - Single object, cone search using sky position or ZTF object ID
    -  Stored SQL queries, whether private saves or public “streams”
    - “Watchlists”: up to a few thousand sources saved in an input list that can be crossmatched at any future time; alerts will be sent to the watchlist owners when transient activity occurs (currently in development, estimated to be minutes between the time of observation and time to alert)
  - Results can be analyzed in Jupyter notebooks, with examples provided on their [website](https://lasair.roe.ac.uk/jupyter)
  - An example of the query results page of the *objects* table is shown in the only figure. Summary:
    - ZTF lightcurve and basic astro information: # of candidates, mean RA & Dec (degrees and hours/min/sec), galactic longitude (l) and latitude (b)
    - Classification and info from Sherlock, including links to cone searches
    - User comments (including Lasair bots)
    - Sherlock’s ranked table of the likely catalogued crossmatched sources
    - An interactive AladinLite display of the region of interest
    -  A table with each of the relevant candidates’ info (i.e., each lightcurve point), taken from the *candidates* table

## Sources

1. Smith, K. W., Williams, R. D., Young, R. D., et al. 2019, RNAAS 3:1
1. [https://github.com/thespacedoctor/sherlock](https://github.com/thespacedoctor/sherlock)