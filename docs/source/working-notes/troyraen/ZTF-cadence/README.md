# docs/source/working-notes/troyraen/ZTF-cadence/README.md

## ZTF Cadence

Checking the time delta between ZTF observations of an object.

```python
# note for future:
# the first 'OVER' should probably be 'GROUP BY' instead
query = """
    SELECT
      AVG(deltajd) OVER (PARTITION BY objectId)
    FROM (
      SELECT
        objectId,
        jd-LAG(jd) OVER (PARTITION BY objectId ORDER BY jd) AS deltajd
      FROM
        `ardent-cycling-243415.ztf_alerts.DIASource`)
"""
```

```python
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import scipy.stats as st


downloaded_query_results = "/Users/troyraen/Documents/broker/Pitt-Google/troy/docs/source/working-notes/troyraen/ZTF-cadence/bquxjob_42c6be59_17e74ad8d7f.csv"
df = pd.read_csv(downloaded_query_results, header=0, names=['deltajd'])

# sigma clip
_, low, upp = st.sigmaclip(df['deltajd'])
dfclipped = df.loc[(df['deltajd'] > low) & (df['deltajd'] < upp)]

mn = dfclipped.deltajd.mean()
# = 8.921240050487983
mdn = dfclipped.deltajd.median()
# = 5.379834603232841

dfclipped.hist()
plt.title(f'ZTF avg delta jd per object. mean={np.round(mn,2)}, median={np.round(mdn,2)}')
plt.savefig('deltajd.png')
plt.show(block=False)

```
