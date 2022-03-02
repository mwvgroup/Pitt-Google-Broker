# TOM proposal clustering

<!-- fs TOM proposal clustering -->

```bash
conda create -n pgb python=3.7
conda activate pgb
pip install ipython
pip install scikit-learn

```

```python
import kmeans1 as km1
import pandas as pd
from matplotlib import pyplot as plt

f = "f4.dat"
cfeat = "B-V"
normfeats = True
# for cfeat in km1.csv_colors:
# for cfeat in ['BP-RP','W3-W4','B-V']:
cfeat = "W3-W4"
db, dflow, predics, predics_test = km1.load_clust_plot(
    f=f, cfeat=cfeat, normfeats=normfeats
)
db["clust"] = pred
# plot color v amplitude colored by classification
featx, featy = cfeat, "amplitude"
plt.figure()
plt.scatter(db[featx], db[featy], c=db["clust"], alpha=0.5)
plt.xlabel(featx)
plt.ylabel(featy)
plt.show(block=False)


# df = pd.read_csv(f)
# df, dfhi, db, dflow = km1.get_dfs(df, cprob=0.98, ntype_hi=5000, ntype_low=100)
# dfcsv = pd.read_csv('asassn-catalog.csv')
# dfcsv = dfcsv.astype({'id':'str'})
#
# kmns, topkmns, dis, distest, nclusts, pred, ptest = km1.get_kclusts(db, dflow, normfeats=True)
# db['clust'] = pred
#
# # plot color v amplitude colored by classification
# db = db.set_index('id', drop=False)
# dfcsv = dfcsv.set_index('id', drop=False)
#
# ids = list(db.id)
# dbcsv = dfcsv.loc[dfcsv.id.isin(ids),:]
# l = len(dbcsv)
# for c in ['BP-RP','J-K','W1-W2','W3-W4','B-V']:
#     # numin = l - dbcsv[c].isnull().sum()
#     # print(f'{c}: num not null = {numin}')
#     d = db.loc[:,['newType','intType','amplitude','clust']]
#     d[c] = dbcsv[c]
#     d = d.dropna()
#
#     featx, featy = c, 'amplitude'
#     plt.figure()
#     plt.scatter(d[featx], d[featy], c=d['clust'], alpha=0.5)
#     plt.xlabel(featx)
#     plt.ylabel(featy)
#     plt.show(block=False)


import pandas as pd
from sklearn.cluster import KMeans
from matplotlib import pyplot as plt

# df = pd.read_csv('Korriban/PGB/asassn-catalog.csv')
df = pd.read_csv("asassn-catalog.csv")
cols = df.columns
Index(
    [
        "asassn_name",
        "Other Names",
        "id",
        "raj2000",
        "dej2000",
        "l",
        "b",
        "Mean Vmag",
        "amplitude",
        "period",
        "Type",
        "class_probability",
        "LKSL Statistic",
        "rfr_score",
        "epochhjd",
        "gdr2_id",
        "gmag",
        "e_gmag",
        "bpmag",
        "e_bpmag",
        "rpmag",
        "e_rpmag",
        "BP-RP",
        "parallax",
        "parallax_error",
        "parallax_over_error",
        "pmra",
        "e_pmra",
        "pmdec",
        "e_pmdec",
        "v_t",
        "dist",
        "allwise_id",
        "jmag",
        "e_jmag",
        "hmag",
        "e_hmag",
        "kmag",
        "e_kmag",
        "w1mag",
        "e_w1mag",
        "w2mag",
        "e_w2mag",
        "w3mag",
        "e_w3mag",
        "w4mag",
        "e_w4mag",
        "J-K",
        "W1-W2",
        "W3-W4",
        "APASS_DR9ID",
        "APASS_Vmag",
        "e_APASS_Vmag",
        "APASS_Bmag",
        "e_APASS_Bmag",
        "APASS_gpmag",
        "e_APASS_gpmag",
        "APASS_rpmag",
        "e_APASS_rpmag",
        "APASS_ipmag",
        "e_APASS_ipmag",
        "B-V",
        "E(B-V)",
        "Reference",
        "Periodic",
        "Classified",
        "ASASSN_Discovery",
    ],
    dtype="object",
)
df.Type.hist()
plt.figure()
df.period.hist()
plt.show(block=False)


dff = df.loc[:, ["Mean Vmag", "amplitude", "period", "J-K", "W1-W2", "W3-W4", "B-V"]]
dff.period.fillna(-1, inplace=True)


x = dff[["Mean Vmag", "amplitude"]].sample(100000)
kmeans = KMeans(n_clusters=15, random_state=0).fit(x)
# kmeans = KMeans(n_clusters=8, init=’k-means++’, n_init=10, max_iter=300, tol=0.0001, precompute_distances=’auto’, verbose=0, random_state=None, copy_x=True, n_jobs=None, algorithm=’auto’)

plt.figure()
plt.scatter(x.amplitude, x["Mean Vmag"], c=kmeans.labels_)
plt.xlabel("amplitude")
plt.ylabel("Mean Vmag")
plt.show(block=False)


### Match lc.dat file to catalog id
import os

lcids = [f.split(".")[0][2:] for f in os.listdir("./lc")]  # len(lcids) = 543227
csvids = list(dfcsv.id)  # len(csvids) = 626281
intsec = list(set(lcids).intersection(set(csvids)))  # len(intsec) = 134009
# most matches start with 'AP', but some are strictly integers
# all are one or the other: len(ap)+len(n)-len(intsec) = 0
ap = [i for i in intsec if i[:2] == "AP"]  # len(ap) = 103318
n = [i for i in intsec if i[0] != "A"]  # len(n) = 30691

# first attempt (worked)
catids = ["13148638", "53339396", "368878", "427135"]  # sample of catalog id's
for i, f in enumerate(os.listdir("./lc")):
    # if f.split('.')[-1] == 'tgz': continue
    #
    fsplt = f.split(".")
    # print(f, fsplt[0][2:])
    # if i>5: break
    fnum = fsplt[0][2:]
    if fnum in catids:
        print(f"{f}")

    try:
        int(fnum)
    except:
        print(f)
###

#############
### Feature extract using Upsilon
import pandas as pd
import os
import upsilon

dfcsv = pd.read_csv("asassn-catalog.csv")
dfcsv = dfcsv.astype({"id": "str"})

# get id's with both an lc#.dat file and a match in dfcsv.id
lcids = [f.split(".")[0][2:] for f in os.listdir("./lc")]  # len(lcids) = 543227
csvids = list(dfcsv.id)  # len(csvids) = 626281
ids = list(set(lcids).intersection(set(csvids)))  # len(ids) = 134009

# do feature extraction on ids
fname = "features.dat"
dflst = []
colnames = [
    "HJD",
    "Cam",
    "mag",
    "mag_err",
    "flux",
    "flux_err",
]  # flux and flux_err in mJy
for i, id in enumerate(ids):
    f = "lc/lc" + id + ".dat"
    try:
        df = pd.read_csv(f, comment="#", names=colnames, sep="\t")
    except:
        print(f"can't load file num: {i}, name: file {f}")
        continue

    # extract features
    try:
        e_features = upsilon.ExtractFeatures(df.HJD, df.mag, df.mag_err)
        e_features.run()
        features = e_features.get_features()
    except:
        print(f"can't extract features from file num: {i}, name: file {f}")
        continue

    # create DF of joint data and write to file
    lc0df = pd.DataFrame(features, index=dfcsv.loc[dfcsv.id == id, "Type"].index)
    lc0df["id"] = id
    lc0df["Type"] = dfcsv.loc[dfcsv.id == id, "Type"]
    lc0df["class_probability"] = dfcsv.loc[dfcsv.id == id, "class_probability"]
    dflst.append(lc0df)

    lcdf = pd.concat(dflst, ignore_index=True)
    dflst = [lcdf]

    lcdf.to_csv(fname, index=False)

#############

#############
### Kmeans on csv file
from sklearn.cluster import KMeans
from matplotlib import pyplot as plt
import pandas as pd

dfcsv = pd.read_csv("asassn-catalog.csv")
dfcsv.period.fillna(-1000, inplace=True)
df, dfhi, db, dflow = km.get_dfs(dfcsv, cprob=0.98, ntype_hi=5000, ntype_low=100)
kmns, topkmns, dis, distest, nclusts, pred, ptest = km.get_kclusts(
    db, dflow, which="csv"
)

for d, p, lbl in zip([db, dflow], [pred, ptest], ["pred", "ptest"]):
    clss = d.groupby("newType").mean().intType.astype("int").sort_values().index
    km.plot_confusion_matrix(d.intType, p, clss, normalize=True, title=lbl)
    plt.show(block=False)


cols = dfcsv.columns
Index(
    [
        "asassn_name",
        "Other Names",
        "id",
        "raj2000",
        "dej2000",
        "l",
        "b",
        "Mean Vmag",
        "amplitude",
        "period",
        "Type",
        "class_probability",
        "LKSL Statistic",
        "rfr_score",
        "epochhjd",
        "gdr2_id",
        "gmag",
        "e_gmag",
        "bpmag",
        "e_bpmag",
        "rpmag",
        "e_rpmag",
        "BP-RP",
        "parallax",
        "parallax_error",
        "parallax_over_error",
        "pmra",
        "e_pmra",
        "pmdec",
        "e_pmdec",
        "v_t",
        "dist",
        "allwise_id",
        "jmag",
        "e_jmag",
        "hmag",
        "e_hmag",
        "kmag",
        "e_kmag",
        "w1mag",
        "e_w1mag",
        "w2mag",
        "e_w2mag",
        "w3mag",
        "e_w3mag",
        "w4mag",
        "e_w4mag",
        "J-K",
        "W1-W2",
        "W3-W4",
        "APASS_DR9ID",
        "APASS_Vmag",
        "e_APASS_Vmag",
        "APASS_Bmag",
        "e_APASS_Bmag",
        "APASS_gpmag",
        "e_APASS_gpmag",
        "APASS_rpmag",
        "e_APASS_rpmag",
        "APASS_ipmag",
        "e_APASS_ipmag",
        "B-V",
        "E(B-V)",
        "Reference",
        "Periodic",
        "Classified",
        "ASASSN_Discovery",
    ],
    dtype="object",
)

type2int = dict([(t, i) for i, t in enumerate(dfcsv.Type.unique())])
dfcsv["intType"] = dfcsv.Type.map(type2int)
feats = ["Mean Vmag", "amplitude", "LKSL Statistic", "rfr_score"]
# feats = ['intType','period']
kmns = KMeans(n_clusters=15, random_state=0).fit(dfcsv.loc[:, feats])

# class vs cluster plot
plt.figure()
plt.scatter(dfcsv.intType, kmns.labels_)
plt.xlabel("True Type")
plt.ylabel("Cluster")
plt.show(block=False)

# features plot
featx, featy = "period", "intType"
plt.figure()
plt.scatter(dfcsv[featx], dfcsv[featy], c=kmns.labels_)
plt.xlabel(featx)
plt.ylabel(featy)
plt.show(block=False)

#############

from sklearn.cluster import DBSCAN

clustering = DBSCAN().fit(db.loc[:, topfeats])

#############
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import confusion_matrix
from sklearn.utils.multiclass import unique_labels


def plot_confusion_matrix(
    y_true, y_pred, classes, normalize=False, title=None, cmap=plt.cm.Blues
):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if not title:
        if normalize:
            title = "Normalized confusion matrix"
        else:
            title = "Confusion matrix, without normalization"

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
    classes = classes[unique_labels(y_true, y_pred)]
    if normalize:
        cm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print("Confusion matrix, without normalization")

    print(cm)

    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation="nearest", cmap=cmap)
    ax.figure.colorbar(im, ax=ax)
    # We want to show all ticks...
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        # ... and label them with the respective list entries
        yticklabels=classes,
        title=title,
        ylabel="True label",
        xlabel="Predicted label",
        ylim=(-0.5, len(classes) - 0.5),
    )

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = ".2f" if normalize else "d"
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                format(cm[i, j], fmt),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
            )
    fig.tight_layout()
    return ax


def set_type_info(df):
    d = df.copy()
    sz = d.groupby("newType").size()
    type2int = dict(
        [(t, i) for i, t in enumerate(sz.sort_values(ascending=False).index)]
    )

    d["numinType"] = d.newType.map(dict(sz))
    d["intType"] = d.newType.map(type2int)

    return d, sz


def get_dfs(df, cprob=0.99, ntype_hi=1000, ntype_low=100):
    """
    Returns:
        original df with newType, intType, numinType columns added

        dfhi with rows of df satisfying
            class_probability > cprob,
            numinType > ntype_hi
    """

    # consolidate types ending with ":" and convert types to ints
    df["newType"] = df.Type.apply(lambda x: x if x[-1] != ":" else x[:-1])
    df, sz = set_type_info(df)

    dfhi = df.loc[df.class_probability > cprob, :]
    dfhi, sz = set_type_info(dfhi)
    dfhi = dfhi.loc[dfhi.numinType > ntype_hi, :]
    dfhi, sz = set_type_info(dfhi)

    # balance number of samples in each class
    typs = list(dfhi.newType.unique())
    l = (
        sz.loc[sz.index.isin(typs)].sort_values(ascending=False).iloc[-1]
    )  # smallest number of samples
    lst = []
    for t in typs:
        lst.append(dfhi.loc[dfhi.newType == t, :].sample(l))
    dfhi_blnc = pd.concat(lst, axis=0)
    dfhi_blnc, __ = set_type_info(dfhi_blnc)

    #
    dflow = df.loc[df.numinType < ntype_low, :]
    dflow, sz = set_type_info(dflow)

    return df, dfhi, dfhi_blnc, dflow


def get_kclusts(df, dftest, which="ups"):
    """ """
    nclusts = len(df.intType.unique())
    kwargs = {"init": "random"}

    if which == "ups":
        feats = [
            "amplitude",
            "cusum",
            "eta",
            "hl_amp_ratio",
            "kurtosis",
            "period",
            "period_uncertainty",
            "phase_cusum",
            "phase_eta",
            "phi21",
            "phi31",
            "quartile31",
            "r21",
            "r31",
            "shapiro_w",
            "skewness",
            "slope_per10",
            "slope_per90",
            "stetson_k",
            "weighted_mean",
            "weighted_std",
        ]
        topfeats = [
            "period",
            "r21",
            "amplitude",
            "slope_per10",
        ]  # , 'quartile31', 'skewness']
    elif which == "csv":
        feats = ["Mean Vmag", "amplitude", "period", "LKSL Statistic", "rfr_score"]
        topfeats = feats

    kmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(df.loc[:, feats])

    topkmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(
        df.loc[:, topfeats]
    )
    pred = topkmns.predict(df.loc[:, topfeats])
    ptest = topkmns.predict(dftest.loc[:, topfeats])

    dis = topkmns.transform(df.loc[:, topfeats])
    distest = topkmns.transform(dftest.loc[:, topfeats])

    return kmns, topkmns, dis, distest, nclusts, pred, ptest


### Kmeans on extracted features
import pandas as pd
from matplotlib import pyplot as plt
import kmeans as km

df = pd.read_csv("f2.dat")
cols = df.columns
Index(
    [
        "amplitude",
        "cusum",
        "eta",
        "hl_amp_ratio",
        "kurtosis",
        "n_points",
        "period",
        "period_SNR",
        "period_log10FAP",
        "period_uncertainty",
        "phase_cusum",
        "phase_eta",
        "phi21",
        "phi31",
        "quartile31",
        "r21",
        "r31",
        "shapiro_w",
        "skewness",
        "slope_per10",
        "slope_per90",
        "stetson_k",
        "weighted_mean",
        "weighted_std",
        "id",
        "Type",
        "class_probability",
    ],
    dtype="object",
)

# Clean
# df = df.drop(['period_SNR','period_log10FAP'], axis=1) # most are NaNs
# df = df.dropna()
# df = df.loc[~df.Type.isin(['L','L:','SR']),:]
# lowlst = ['AM+E', 'CV+E', 'V838MON', 'UGWZ', 'ZZB', 'UGZ', 'V1093HER', 'DYPer',
#        'PVTELI', 'HMXB', 'ZZ', 'SXARI', 'PPN', 'SDOR', 'ZZLep', 'UGSU', 'ZZA',
#        'ELL', 'DQ', 'V361HYA', 'WR', 'R', 'SXPHE', 'UGSS', 'CV', 'ZAND', 'RCB',
#        'HB', 'RVA', 'LSP', 'SRD', 'RRD', 'CWB', 'DCEPS', 'UG', 'UV', 'CWA']
# df = df.loc[~df.Type.isin(lowlst),:]
df = pd.read_csv("f4.dat")
# df = df.loc[~df.Type.isin(['L','L:','SR','SRS']),:]
df, dfhi, db, dflow = km.get_dfs(df, cprob=0.98, ntype_hi=5000, ntype_low=100)
kmns, topkmns, dis, distest, nclusts, pred, ptest = km.get_kclusts(db, dflow)

for d, p, lbl in zip([db, dflow], [pred, ptest], ["pred", "ptest"]):
    clss = d.groupby("Type").mean().intType.astype("int").sort_values().index
    km.plot_confusion_matrix(d.intType, p, clss, normalize=True, title=lbl)
    plt.show(block=False)


for k, lbl in zip([kmns, topkmns], ["kmns", "topkmns"]):
    km.plot_confusion_matrix(
        db.intType, k.labels_, db.intType.unique(), normalize=True, title=lbl
    )
    plt.show(block=False)

    plt.figure()
    # plt.scatter(df.intType, kmns.labels_, alpha=0.1)
    plt.hist2d(
        db.intType,
        k.labels_,
        bins=[len(db.intType.unique()), nclusts],
        weights=1 / db.numinType,
    )
    plt.xlabel("True Type")
    plt.ylabel("Cluster")
    plt.show(block=False)

plt.figure()
ax = plt.gca()
for d, lbl in zip([dis, distest], ["training set distance", "test set distance"]):
    dfdis = pd.DataFrame(d)
    mindist = dfdis.min(axis=1)
    mindist.hist(bins=30, ax=ax, label=lbl, alpha=0.5, density=True)
plt.legend()
plt.show(block=False)


# features plot
featx = "period"
feats = [
    "amplitude",
    "cusum",
    "eta",
    "hl_amp_ratio",
    "kurtosis",
    "period",
    "period_uncertainty",
    "phase_cusum",
    "phase_eta",
    "phi21",
    "phi31",
    "quartile31",
    "r21",
    "r31",
    "shapiro_w",
    "skewness",
    "slope_per10",
    "slope_per90",
    "stetson_k",
    "weighted_mean",
    "weighted_std",
]
for featy in feats:
    plt.figure()
    plt.scatter(db[featx], db[featy], c=topkmns.labels_)
    plt.xlabel(featx)
    plt.ylabel(featy)
    plt.show(block=False)

#############


### look at a file that Upsilon couldn't process
# problem is: some magnitudes are an upper limit.
# e.g. of problem entry:
#                HJD Cam      mag  mag_err   flux  flux_err
#   2.457799e+06  bf  >15.680    99.99  1.518     0.410
import pandas as pd
import upsilon

fprob = "lc/lc320080.dat"  # 'lc/lc297988.dat'
colnames = ["HJD", "Cam", "mag", "mag_err", "flux", "flux_err"]
df = pd.read_csv(fprob, comment="#", names=colnames, sep="\t")
e_features = upsilon.ExtractFeatures(df.HJD, df.mag, df.mag_err)
e_features.run()
features = e_features.get_features()
###
```

<!-- fe TOM proposal clustering -->

# Use cases

<!-- fs use cases -->

look in to [astrorapid](https://pypi.org/project/astrorapid/) for classification

## SN

<!-- fs SN -->

What user wants: * Prob(SN type...) - selection function - host galaxy - mass - SFR How
to classify: - astrorapid Primary catalogs to match on: - SDSS, maybe BOSS (northern
sky) - DES (southern) - ZTF XM features: * RA, DEC - classification - errors (more
specifically... ?) - external survey depth - redshift

<!-- fe SN -->

## CV (white dwarf with non-degen companion)

<!-- fs CV -->

[Prospects for detection of detached double white dwarf binaries with Gaia, LSST and LISA](arxiv:1703.02555)
expect periodicity? can we do better than Lomb-Scargle? What user wants: * Prob(CV) -
period - companion information - followup when go Nova How to classify: - more light in
xray than visible, but we probably won't have this info - check for existing ML or other
algorithms Primary catalogs to match on: - GAIA (more likely to contain companion than
WD, WD completeness only to hundreds of pc. Gaia DR2 does not contain many binaries,
they are mostly thrown out b/c it makes for noisy paralax measurements. DR3 will try to
do better here.) - APOGEE (more likely to contain companion than WD) - Ritter & Kolb
2003 (CV catalog) XM features: * RA, DEC - classification - errors (more specifically...
?)

```
population: selection function what we saw what we didn't see
most novae are gamma ray emitters. observing, focusing gamma rays is hard

papers:
brad schaefer compendium of all good observations of classical novae
recurance novae repeats in ~human lifetime. classical noave longer time scales. all novae reoccur
brightest things in M31 that vary are usually novae and cephids. range in novae brightness is much larger than in cephieds
some (1?) novae in M31 has period of 1 yr
novae are degen white dwarfs
# open question: does accretion add to white dwarf mass or erode it?. nova explosion signature shows carbon, oxegyn. so can you get SN1a from this?
monica sorieson. get well sampled light curves for novae and use those as templates. (or google it)
strop and schaefer 2010 paper
oxygen neon WD cannot explode as SN. get much more energy from burning carbon. binding energy larger than energy you get from burning neon. carbon oxygen WD is the most massive object that can completely blow itself up.
nova is thermonuclear runaway on the surface of the WD
CV can have changes in brignetness due to flares
ASASSIN survey may be useful to us. finds CV and novae and alert on things.
Kochanek & Stanek OSU people and CVs
faint novae are probably very faint... can see all SN because lower limit is above telescope mag limit, not the case with novae
look at surveys in the local group.
Laura Chomiuk (Summit's current boss) studies novae
Atlas (has panstars filter system) must have seen novae
Novae lightcurves are much more diverse than SN ones
retrain SuperNNova for novae
```

_Talk to Carlos:_ CV's: What if anything are the alerts going to be useful for? - If so,
What do you want to know about the object? If not, change use case? - Track CV's -
follow up when -> Nova - Are any SN progenitors? Novae. - Short rise times few days. -
Decline time and shape => mass distance and composition info. - Need follow-up => alert.
Mv= -6 to -9. - MW rate 35+-10 per year, scales with galaxy mass. Other questions: -
What other objects are easily confused with CVs and need to be ruled out? How? Physical
mechanisms. What to look for.

_Brett thoughts_ on classifying CVs and looking for training datasets: - Folded light
curve may be useful (cephied). - AGN with changing broad lines, changing look quasars
Jessie Runnoe. - M dwarf flares. _Datasets._ - Ogle micro lensing two stars source and
lens, Found ~10^6 variable stars. -
[Atlas of Variable Star Light Curves](http://ogle.astrouw.edu.pl/atlas/). "The OGLE
Catalog of Variable Stars consists of over 400,000 objects and is now the largest set of
variable stars in the world." Light curves (I band) "usually consist of several hundred
to several thousand observing points obtained between 1997 and 2012" -
[search "Recent Scientific Results" section for 'nova'; "Main OGLE Results:"->"Variable Stars"](http://ogle.astrouw.edu.pl/)
\- [data](http://www.astrouw.edu.pl/ogle/ogle4/OCVS/CV/) -
[CVOM: OGLE-IV REAL TIME MONITORING OF CATACLYSMIC VARIABLES](http://ogle.astrouw.edu.pl/ogle4/cvom/cvom.html)
\- [Classical novae in OGLE data](https://pos.sissa.it/255/054/pdf) -
[TNS Novae:](https://wis-tns.weizmann.ac.il/search?&discovered_period_value=&discovered_period_units=months&unclassified_at=0&classified_sne=0&name=&name_like=0&isTNS_AT=all&public=all&ra=&decl=&radius=&coords_unit=arcsec&groupid%5B%5D=null&classifier_groupid%5B%5D=null&objtype%5B%5D=26&at_type%5B%5D=null&date_start%5Bdate%5D=&date_end%5Bdate%5D=&discovery_mag_min=&discovery_mag_max=&internal_name=&discoverer=&classifier=&spectra_count=&redshift_min=&redshift_max=&hostname=&ext_catid=&ra_range_min=&ra_range_max=&decl_range_min=&decl_range_max=&discovery_instrument%5B%5D=null&classification_instrument%5B%5D=null&associated_groups%5B%5D=null&at_rep_remarks=&class_rep_remarks=&num_page=50)
\-
[One Thousand New Dwarf Novae from the OGLE Survey](https://ui.adsabs.harvard.edu/abs/2015AcA....65..313M/abstract)
\-
[OGLE ATLAS OF CLASSICAL NOVAE II. MAGELLANIC CLOUDS](https://arxiv.org/pdf/1511.06355.pdf)
\-
[OGLE ATLAS OF CLASSICAL NOVAE I. GALACTIC BULGE OBJECTS](https://arxiv.org/pdf/1504.08224.pdf)
\- "Nova remnants can also become Type Ia supernovae (SNe Ia). The contribution of novae
to these phenomena depends on nova rates, which are not well established for the Galaxy"
\- more notes highlighted in the paper stored in Mendeley. -
[Dwarf Novae in the OGLE Data. II. Forty New Dwarf Novae in the OGLE-III Galactic Disk Fields](https://ui.adsabs.harvard.edu/abs/2013AcA....63..135M/abstract)
\- Gaia, 5x10^5 variables - Kepler. - Galaxy zoo may have a dataset. - Sloan data, Stripe
82 time sampling is good on an equatorial stripe. -
[The January 2016 eruption of recurrent nova LMC 1968](https://arxiv.org/pdf/1909.03281.pdf)
\- [TT Arietis: 40 years of photometry](https://arxiv.org/pdf/1909.05696.pdf)

<!-- fe CV -->

<!-- fe use cases -->

# Notes and To Do

<!-- fs -->

[Google fellowship](https://ai.google/research/outreach/phd-fellowship/)

- ? need "Research/dissertation proposal (recommended length 4-5 pages, no longer than
  8)"

incorporate Rongpu's DECaLS catalog by end of August

## Chicago talk

```python
import numpy as np
from matplotlib import pyplot as plt
from broker.ztf_archive import iter_alerts

num_alerts = 4732
alert_list = next(iter_alerts(num_alerts=num_alerts))

sn = []
for alert in alert_list:
    epochs = alert["prv_candidates"] + [alert["candidate"]]
    for epoch in enumerate(epochs):
        sn.append(epoch["scorr"])

plt.hist(np.array(sn))
```

## Create value_added module

<!-- fs value added -->

*Korriban environment not working... delete all PB environments and start from scratch*

```bash
# update astrorapid
pip install astrorapid --upgrade
```

```python
# filter warnings
import warnings

warnings.filterwarnings("ignore")
# warnings.simplefilter('once', UserWarning) # doesn't work

# get alerts
from broker.ztf_archive import iter_alerts

num_alerts = 4732
alert_list = next(iter_alerts(num_alerts=num_alerts))

# get value added products
from broker.value_added import value_added as va

kwargs = {"survey": "ZTF", "rapid_plotdir": "./broker/value_added/plots"}
# kwargs = { 'survey': 'ZTF', 'rapid_plotdir': None }
xmatch_dicts_list, class_dicts_list = va.get_value_added(alert_list, **kwargs)
xmatch_dicts_list
class_dicts_list

# find a good classification for Columbus talk plot
# rmax,rmax2,idx,idx2=(0,0,0,0)
# for j,d in enumerate(class_dicts_list):
#     m = 0
#     for i in range(12):
#         m = max(d['prob_class'+str(i)],m)
#     # m = d['prob_class1']
#     if m > rmax:
#         idx3 = idx2
#         rmax3 = rmax2
#         idx2 = idx
#         rmax2 = rmax
#         idx = j
#         rmax = m

## Tests:
### checking epoch zeropoint key error
### early schemas did not contain this key
### all downloaded schema 3.3 epochs did contain it.
from broker.ztf_archive import _parse_data as psd

num_alerts = 4739
alert_list = next(psd.iter_alerts(num_alerts=num_alerts))
N_alerts, N_epochs, alerts_wo_zp, epochs_wo_zp = (0 for i in range(4))
for a in alert_list:
    N_alerts = N_alerts + 1
    a_has_all_zp = True
    for n, epoch in enumerate(a["prv_candidates"] + [a["candidate"]]):
        N_epochs = N_epochs + 1
        if "magzpsci" not in epoch.keys():
            epochs_wo_zp = epochs_wo_zp + 1
            a_has_all_zp = False
    if a_has_all_zp == False:
        alerts_wo_zp = alerts_wo_zp + 1


### test rapid results packaging for BQ
from broker.value_added import classify as classify
from broker.value_added import xmatch as xm
from broker.value_added import value_added as va
from broker.value_added.value_added import alert_xobj_id
from broker.ztf_archive import _parse_data as psd

num_alerts = 15
alert_list = next(psd.iter_alerts(num_alerts=num_alerts))

survey = "ZTF"
xmatch_list = xm.get_xmatches(alert_list, survey=survey)
light_curves = va.format_for_rapid(alert_list, xmatch_list, survey=survey)
predictions = classify.rapid(light_curves, plot=False, use_redshift=True)
```

<!-- fe value added -->

## Create RAPID module

<!-- fs -->

```python
# had to manually update the following:
# pip install wrapt --upgrade --ignore-installed
# pip install setuptools --upgrade
# pip install protobuf --upgrade
# then the following succeeded:
# pip install astrorapid

# do the classification (pre value_added.py):
from broker.classify import rapid as pbr

lst = pbr.collect_ZTF_alerts(max_alerts=1)
res = pbr.classify(lst, plot=True, use_redshift=True)


# lst contains alerts with hostgal info and at least 2 observations
from matplotlib import pyplot as plt

# plot redshifts
z = [l[-2] for l in lst]
plt.figure()
plt.hist(z)
plt.savefig("./tests/rapid/photoz_dist.png")
plt.show(block=False)

# number of hostgals
```

<img src="./tests/rapid/photoz_dist.png" alt="photoz_dist" width="400"/>

Need to:

- fix redshift (need closest decals object or a different training set)
- check magnitude and error conversions
- fix "fix this" and "check this" items

<!-- fe ## Create RAPID module -->

## July 9

<!-- fs -->

1. Have RAPID classifying SN with host galaxy info by July 23rd.
   - write it to accept dictionary as input (AVRO files are priority, but should be able
     to accept BigQuery input with some wrapper function.)
   * mwebv: milky way excess b-v color (dust extinction)
   * mjd: modified julian date
   * flux and error: convert PSF mags
   * zeropoint: magzpsci. ask Daniel
   * photflag: ask Daniel
1. Test pub/sub. Try to write automated tests.. input, calling fncs or code trying to
   test, and expected output.

<!-- fe ## July 9 -->

## Classifications meeting prep (RAPID and SuperNNova)

<!-- fs -->

[RAPID](https://astrorapid.readthedocs.io)
[ZTF Avro Schemas](https://zwickytransientfacility.github.io/ztf-avro-alert/schema.html)
Meeting prep:

- RAPID and SuperNNova
- RAPID more straightforward so setting that up.
  - but requires redshift info... standard process seems to be to use host gal redshift.
  - not sure what they do when there's no identified host.
- Need training dataset. Have galaxy set from Graham and SN, etc. set from PLAsTICC.
  - not sure if I'm allowed to use either for this purpose.

<!-- fe ## Classifications meeting prep (RAPID and SuperNNova) -->

## Testing pub_sub branch. PASSED.

<!-- fs -->

GCP topic: troy_test_topic GCP subscription: troy_test_subscript

```python
# General setup
# from broker import ztf_archive as ztfa
# ztfa.download_recent_data(max_downloads=1)
project_id = "ardent-cycling-243415"
topic_name = "troy_test_topic"
subscription_name = "troy_test_subscript"

# Check pub/sub of general data. PASSED.
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)
for n in range(4):
    data = "Message number {}".format(n + 100)
    # Data must be a bytestring
    data = data.encode("utf-8")
    # When you publish a message, the client returns a future.
    future = publisher.publish(topic_path, data=data)
    print("Published {} of message ID {}.".format(data, future.result()))
print("Published messages.")
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_name)
max_messages = 10
response = subscriber.pull(subscription_path, max_messages=max_messages)
ack_ids = []
for received_message in response.received_messages:
    print("Received: {}".format(received_message.message.data))
    ack_ids.append(received_message.ack_id)
subscriber.acknowledge(subscription_path, ack_ids)
print("Received and acknowledged {} messages. Done.".format(len(ack_ids)))


# Check pub/sub of alert data. PASSED.
# get alert identifiers
from broker.ztf_archive import _parse_data as psd

ids = []
for a, alert in enumerate(psd.iter_alerts()):
    print(alert["candid"])
    ids.append(alert["candid"])
    if a > 3:
        break
# publish
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)
for a, id in enumerate(ids):
    future = publisher.publish(topic_path, data=psd.get_alert_data(id, raw=True))
    print("Published message number {} with ID {}.".format(a, future.result()))
    if a > 0:
        break
print("Published messages.")
# get the alerts back
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_name)
max_messages = 10
response = subscriber.pull(subscription_path, max_messages=max_messages)
ack_ids = []
for received_message in response.received_messages:
    print("Received: {}".format(received_message.message.data))
    ack_ids.append(received_message.ack_id)
subscriber.acknowledge(subscription_path, ack_ids)
print("Received and acknowledged {} messages. Done.".format(len(ack_ids)))
```

<!-- fe ## Testing pub_sub branch -->

<!-- fe # Notes and To Do -->

# Info

<!-- fs INFO -->

# GIT Info

[repo](https://github.com/mwvgroup/Pitt-Google-Broker)
git@github.com:mwvgroup/Pitt-Google-Broker.git
[read the docs](https://pitt-broker.readthedocs.io/en/latest/index.html)

# DATA Info

To use data stored on Korriban: in broker/ztf_archive/\_download_data.py, set the
variable: ZTF_DATA_DIR =
Path('/Users/troyraen/Korriban/Documents/Pitt-Broker/broker/ztf_archive/data')

# ZTF Info

[alert schema](https://zwickytransientfacility.github.io/ztf-avro-alert/schema.html)

# GCP Account Info

Project name: pitt-google-broker-prototype Project ID: ardent-cycling-243415 Project
number: 591409139500

Service Account: tjraen-owner@ardent-cycling-243415.iam.gserviceaccount.com project_id =
'ardent-cycling-243415' topic_name = 'troy_test_topic' subscription_name =
'troy_test_subscript'

<!-- fe INFO -->

# Code

<!-- fs -->

## Download ZTF Data

<!-- fs -->

```python
from broker import ztf_archive as ztfa
from broker.ztf_archive import iter_alerts

ztfa.download_recent_data(max_downloads=1)
# Iterate through local alert data
for alert in iter_alerts():
    alert_id = alert["candid"]
    print(alert_id)
    break
```

<!-- fe ## Download ZTF Data -->

## Astroquery

<!-- fs -->

```python

# Get RA and DEC from alerts and write to file:
import pandas as pd
def get_alerts_RA_DEC(fout=None):
    """ Iterate through alerts and grab RA, DEC.
        Write data to file with format compatible with astroquery.xmatch.query().

        fout = string, path to save file.

        Returns the alert data as a Pandas DataFrame.
    """

    data_list = []
    for a, alert in enumerate(iter_alerts()):
        alert_id = alert['candid']
        alert_data = get_alert_data(alert_id)

        dat = {}
        dat['alert_id'] = alert_id
        dat['ra'] = alert_data['candidate']['ra']
        dat['dec'] = alert_data['candidate']['dec']
        data_list.append(dat)

        if a>1000: break

    print('creating df')
    df = pd.DataFrame(data_list)

    if fout is not None:
        print('writing df')
        df.to_csv(fout, sep=',', columns=['alert_id','ra','dec'], header=True, index=False)
    else:
        return df

    return None

fradec = 'mock_stream/data/alerts_radec.csv'
get_alerts_RA_DEC(fout=fradec)

# Use Astroquery to query CDS xMatch service
from astropy import units as u
from astroquery.xmatch import
table = XMatch.query(cat1=open(fradec), cat2='vizier:II/246/out', \
                    max_distance=5 * u.arcsec, colRA1='ra', colDec1='dec')
# with the current data, this matches 818 out of 1002 in fradec
# table.columns gives ['angDist','alert_id','ra','dec','2MASS','RAJ2000','DEJ2000','errHalfMaj','errHalfMin','errPosAng','Jmag','Hmag','Kmag','e_Jmag','e_Hmag','e_Kmag','Qfl','Rfl','X','MeasureJD']

```

<!-- fe Astroquery -->

## Download and look at alerts

<!-- fs -->

```python
from matplotlib import pyplot as plt
from mock_stream import download_data
from mock_stream import get_alert_data
from mock_stream import get_number_local_alerts
from mock_stream import iter_alerts
from mock_stream import number_local_releases
from mock_stream import plot_stamps

# Download data from ZTF. By default only download 1 day
# Note: Daily releases can be as large as several G
download_data(max_downloads=1)

# Retrieve the number of daily releases that have been downloaded
print(number_local_releases())

# Retrieve the number of alerts that have been downloaded
# from all combined daily releases.
print(get_number_local_alerts())

# Iterate through local alert data
for alert in iter_alerts():
    alert_id = alert["candid"]
    print(alert_id)
    break

# Get alert data for a specific id
alert_id = 833156294815015029
alert_data = get_alert_data(alert_id)
RA, DEC = alert_data["candidate"]["ra"], alert_data["candidate"]["dec"]
# print(alert_data)


# Plot stamp images for alert data
fig = plot_stamps(alert_data)
plt.show()
```

<!-- fe download and look at alerts -->

## Remove and reinstall Conda environment

<!-- fs -->

```bash
conda remove --name pitt_broker --all
conda create -n pitt_broker python=3.7
conda activate pitt_broker  # Activate the new environment
pip install -r requirements.txt
python setup.py install --user  # Install the package
OGdir=$(pwd)
# Create files to run on startup and exit
cd $CONDA_PREFIX
mkdir -p ./etc/conda/activate.d
mkdir -p ./etc/conda/deactivate.d
touch ./etc/conda/activate.d/env_vars.sh
touch ./etc/conda/deactivate.d/env_vars.sh
# Add environmental variables
echo 'export BROKER_PROJ_ID="ardent-cycling-243415"' >> ./etc/conda/activate.d/env_vars.sh
# echo 'export GOOGLE_APPLICATION_CREDENTIALS="/Users/troyraen/Documents/Pitt-Broker/GCPauth_pitt-google-broker-prototype-0679b75dded0.json"' >> ./etc/conda/activate.d/env_vars.sh
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/home/tjr63/Documents/Pitt-Broker/GCPauth_pitt-google-broker-prototype-0679b75dded0.json"' >> ./etc/conda/activate.d/env_vars.sh
# echo 'export PGB_DATA_DIR="~/some/directory/name/"' >> ./etc/conda/activate.d/env_vars.sh
echo 'unset BROKER_PROJ_ID' >> ./etc/conda/deactivate.d/env_vars.sh
echo 'unset GOOGLE_APPLICATION_CREDENTIALS' >> ./etc/conda/deactivate.d/env_vars.sh
# echo 'unset PGB_DATA_DIR' >> ./etc/conda/deactivate.d/env_vars.sh
cd $OGdir
```

<!-- fe ## Remove and reinstall Conda environment -->

Beetled59Expounded84crucially18dilemma's55protesting

<!-- fe # Code -->

# Supernovae Handbook

## Ch 12 Observational and Physical Classification of Supernovae (9/13/19)

Classifications based on spectroscopy at peak brightness. 1st cut: is there hydrogen?
yes = Type II, no = Type I Type I cut: SiII = Ia, none = 1b (has He) or 1c (no He) (mag
~-19) Type Ia = carbon oxygen WD with companion. WD accretes and explodes. only Ia's are
standardizable enough to use for cosmology (All others are core collapse) 1991T: super
luminous, hotter and brighter by ~0.5 mag (~20%) 1991bg: cooler and dimmer by ~1 mag
(~15%) Iax: even dimmer than 91bg's 1b: have normal and double peak. double peak: 1st
peak looks like 1b, 2nd looks like 1c Type II: easy to identify early on b/c have strong
H lines IIb: have He contribution.. look similar to Ib's (could just be Ib's inside
circumstellar material) IIn: "normal", narrow and strong H at peak Note: 7000-10000
Angstroms, water vapor absorption gets strong

<!-- fs ARCHIVE -->

## 6/11/19

<!-- fs -->

travel funding use cases data studio

<!-- fe ## 6/4/19 -->

## 6/4/19

<!-- fs -->

travel funding use cases data studio

<!-- fe ## 6/4/19 -->

## 5/28/19

<!-- fs -->

questions to answer: planning to fail with Messier objects (15 arcmin) what are our use
cases minimum viable product/protype user watch list - (galactic variable stars,
identified strong lensing systems, ) - could define own matching radius. Notify user of
alert match and upcoming expected observations. *want to set up user web interface* -
list of alerts + value added - upcoming pointing regions - DIA object page - all related
alerts - postage stamps - light curve: interactive, connect plot points to data tables -
cross matches - whether spectra exist - classification confidence as a function of time
\- Ia, Ic, variable, AGN, galaxy

<!-- fe ## 5/28/19 -->

## 5/21/19

<!-- fs -->

1. choose a small handful of catalogs to focus on
   - SDSS (photometery and spectroscopy)
     - SEGUE (MW stars)
     - Sloan Supernova Survey (1a)
     - APOGEE (IR spec of MW stars)
     - BOSS and eBOSS (LRGs)
     - MaNGA (nearby galaxy spectroscopy)
   - WISE (IR all sky survey, near earth objects, star clusters) - ask Ross
   - GAIA (MW stars)
   - 2MASS (galaxies, star clusters, stars, galaxies behind MW, low mass stars)
   - Chandra Source Catalog (X-ray sources, AGN, SNe remnants, X-ray binaries)
1. evaluate store catalogs in Big Query
1. think about what we want to use in the xmatch
   - RA/DEC
   - redshift
   - object type/classification
   - photometery/colors
   - period

<!-- fe ## 5/21/19 -->

## April-ish 19

<!-- fs -->

\[SDSS catalog\](bruno/users/cnm37/Skyserver_3e5_stars_mags.csv,
~/Korriban/Documents/Pitt-Broker/mock_stream/data/Skyserver_3e5_stars_mags.csv)

- [x] rsync -avzn -e ssh
  tjr63@bruno.phyast.pitt.edu:pitt-broker/Skyserver_3e5_stars_mags.csv
  ~/Korriban/Documents/Pitt-Broker/mock_stream/data/.

moving data dir to Korriban:

- [x] rsync -avz /Users/troyraen/Documents/Pitt-Broker/mock_stream/data
  ~/Korriban/Documents/Pitt-Broker/mock_stream/

<!-- fe ## April-ish 19 -->

# DESC call re: LSST call for brokers (4/10/19)

<!-- fs -->

[Official Notes](https://docs.google.com/document/d/1hsQd4JDPgscUkGEw6m8qL_Fxy8JyRvMSBYHzDePXlMc/edit)

No DESC working groups have expressed need for alerts on timescales \< 24 hours => no
driver for DESC to develop a broker One thing DESC needs that is not part of 60sec alert
stream is..?

Value added products DESC needs: - classify events scientifically - triggering followup

LSST considering offering alert stream in cloud.

DESC will focus on 24hr and yearly data releases.

__Useful quality of Broker: _light_ filtering of alerts__

<!-- fe DESC call re: LSST call for brokers -->

<!-- fe ARCHIVE -->
