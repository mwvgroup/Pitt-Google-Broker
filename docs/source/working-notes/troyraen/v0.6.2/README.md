# v0.6.2: Issue #68

[#68](https://github.com/mwvgroup/Pitt-Google-Broker/issues/68)

Solution summary:

- require astropy==3.2.1
  - fix utils module to accomodate this astropy version

Note the specific error from issue 68
`OSError: No SIMPLE card found, this file does not appear to be a valid FITS file` can
be avoided by added the kwarg `ignore_missing_simple=True` to the function
`astropy.io.fits.open()`. However, then we run into the ValueError documented in
`pgb_utils.figures.plot_stamp()`, and fixing this requires astropy 3.2.1.

Work details:

pgb-utils v0.2.5 throws an error when trying to plot cutouts.

Try with colab version of pgb-utils to make sure it still works with a new alert:

```bash
conda create -n pgbutils1 python=3.7
conda activate pgbutils1
pip install pgb-utils==0.1.4

cd /Users/troyraen/Documents/broker/repo2/version_tracking/v0.6.0
python
```

```python
import fastavro
from matplotlib import pyplot as plt
import pgb_utils as pgb

fname = "ZTF18acegotq.1680242110915010008.ztf_20210808_programid1.avro"
with open(fname, "rb") as fin:
    alert_list = [r for r in fastavro.reader(fin)]
pgb.figures.plot_lightcurve_cutouts(alert_list[0])
plt.show(block=False)
# this works
```

Find which dependencies make that version work:

```bash
conda create --name issue68 python=3.7
conda activate issue68

pip install ipython
pip install fastavro==1.4.4
pip install matplotlib==3.4.2
# pip install beautifulsoup4==4.8

# pip uninstall astropy
pip install astropy==3.2.1  # this is the one that fixes it
pip install APLpy

cd ~/Documents/broker/repo2/pgb_utils/pgb_utils
```

```python
import fastavro
from matplotlib import pyplot as plt

# import pgb_utils.figures
import figures as pfig

dname = "/Users/troyraen/Documents/broker/repo2/version_tracking/v0.6.0/"
fname = "ZTF18acegotq.1680242110915010008.ztf_20210808_programid1.avro"

with open(f"{dname}{fname}", "rb") as fin:
    alert_list = [r for r in fastavro.reader(fin)]
alert_dict = alert_list[0]

pfig.plot_cutouts(alert_dict)
plt.show(block=False)
```

Now Issue 68 is fixed, but this breaks utils.alert_dict_to_table() because dicts do not
necessarily have the same keys(). Fix it:

```python
import utils as put

table = put.alert_dict_to_table(alert_dict)
```

Now everything should work. Test it:

```bash
conda remove -n issue68 --all
conda create -n issue68 python=3.7
conda activate issue68

cd /Users/troyraen/Documents/broker/repo3/pgb_utils
python -m pip install -e .

ipython
```

```python
import fastavro
from matplotlib import pyplot as plt
import pgb_utils.figures as pfig
import pgb_utils.utils as put

# open the alert
dname = "/Users/troyraen/Documents/broker/repo2/version_tracking/v0.6.0/"
fname = "ZTF18acegotq.1680242110915010008.ztf_20210808_programid1.avro"

with open(f"{dname}{fname}", "rb") as fin:
    alert_list = [r for r in fastavro.reader(fin)]
alert_dict = alert_list[0]

# test the cutout
pfig.plot_cutouts(alert_dict)
plt.show(block=False)
# this works

# test the dict to table
table = put.alert_dict_to_table(alert_dict)
# this works
```

Test the conda env from yaml method after publishing to PyPI:

```bash
conda env create --file pgb_env.yaml
conda activate PGByaml
# now run the previous python block, and both functions work, yay
```
