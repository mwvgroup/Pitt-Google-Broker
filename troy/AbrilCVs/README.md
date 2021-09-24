# CV Catalog from Abril 2020

- [Abril 2020](https://ui.adsabs.harvard.edu/abs/2020MNRAS.492L..40A/abstract)
- [CV catalog on CDS](https://cdsarc.cds.unistra.fr/viz-bin/cat?J/MNRAS/492/L40) (downloaded to this dir)

- Load to BQ
- cross match alerts (maybe best to package the catalog with the module rather than query BQ every time)
- BQ ML

- Michael:
    - number of dimensions to parameters. maybe dataset of only 2000 is ok. make the model smarter (vs data augmentation)

- Brett:
    - get ~2000 Gaia stars, combine with these CVs
    - mags, etc.
    - random forest

- Abril20
    - CMD
        - trends with subtypes and periods
        - population density distributions

- Questions:
    - Periods of hours. could you predict the magnitude based on different periods, and then check whether alert is consistent? or are the uncertainties too big? mags, period.
