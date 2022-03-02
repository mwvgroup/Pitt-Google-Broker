""" Runs unsupervised clustering on ASAS-SN data with features extracted
    using UPSILoN
"""

from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix
from sklearn.utils.multiclass import unique_labels

csv_colors = ["BP-RP", "J-K", "W1-W2", "W3-W4", "B-V"]

dfcsv_cols = [
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
]
csv_feats_dict = {
    "type": ["Type", "class_probability", "Classified"],
    "other": [
        "amplitude",
        "period",
        "Mean Vmag",
        "LKSL Statistic",
        "rfr_score",
        "Periodic",
    ],
    "mags": [
        "gmag",
        "bpmag",
        "rpmag",
        "jmag",
        "hmag",
        "kmag",
        "w1mag",
        "w2mag",
        "w3mag",
        "w4mag",
    ],
    "APASS_mags": [
        "APASS_Vmag",
        "APASS_Bmag",
        "APASS_gpmag",
        "APASS_rpmag",
        "APASS_ipmag",
    ],
    "colors": ["BP-RP", "J-K", "W1-W2", "W3-W4", "B-V"],
}


def load_features(
    f="upsilon_features.dat", fcsv="asassn-catalog.csv", cfeat=None, cprob=0.99
):

    # load features extracted from light curves using Upsilon
    df = pd.read_csv(f)
    df = df.set_index("id", drop=False)

    # add color info from csv file
    dfcsv = pd.read_csv(fcsv)
    dfcsv = dfcsv.astype({"id": "str"})
    dfcsv = dfcsv.set_index("id", drop=False)
    for c in csv_feats_dict["colors"]:
        df[c] = dfcsv.loc[dfcsv.id.isin(list(df.id)), :][c]

    if cfeat is not None:
        df = df.dropna(subset=[cfeat])

    # consolidate types ending with ":" and convert types to ints
    df = consol_types(df)

    ## get a df specifically for clustering
    dfhiprob = get_hiprob(df, cprob=cprob)
    # get types with low and hi number of members
    dfclust = get_hilow(dfhiprob, numHi=10000, numLow=50)

    # restrict to top features
    topfeats = ["period", "r21", "amplitude", "slope_per10", "quartile31", "skewness"]
    # allfeats = ['amplitude', 'cusum', 'eta', 'hl_amp_ratio', 'kurtosis',
    #        'period', 'period_uncertainty',
    #        'phase_cusum', 'phase_eta', 'phi21', 'phi31', 'quartile31', 'r21',
    #        'r31', 'shapiro_w', 'skewness', 'slope_per10', 'slope_per90',
    #        'stetson_k', 'weighted_mean', 'weighted_std']
    if cfeat is not None:
        topfeats = topfeats + [cfeat]
    dfclust_feats = dfclust.loc[:, topfeats]

    return df, dfcsv, dfclust, dfclust_feats


def consol_types(df):
    """Adds columns
    'newType': which merges Types ending in ":" with the base Type
    """
    d = df.copy()

    # consolidate types ending with ":"
    d["newType"] = d.Type.apply(lambda x: x if x[-1] != ":" else x[:-1])

    # recalculate numinType and reset intType
    d, _ = set_type_info(d)

    return d


def get_hiprob(df, cprob=0.99):

    d = df.loc[df.class_probability > cprob, :]

    # recalculate numinType and reset intType
    d, __ = set_type_info(d)

    return d


def get_hilow(df, numHi=10000, numLow=50):
    """Returns df of classes with large and small number of examples."""

    d = df.loc[((df.numinType > numHi) | (df.numinType < numLow))]

    return d


def set_type_info(df):
    """Adds or updates columns:
    'numinType', number of stars of this type
    'intType', converts the Type str to an integer for supervised classification
    """
    d = df.copy()
    sz = d.groupby("newType").size()
    type2int = dict(
        [(t, i) for i, t in enumerate(sz.sort_values(ascending=False).index)]
    )

    d["numinType"] = d.newType.map(dict(sz))
    d["intType"] = d.newType.map(type2int)

    return d, sz


def get_kclusts(df, dftest=None, nclusts=None, normfeats=True, color=None):
    """Runs Kmeans clustering using training set df.
    Returns various dataframes of predictions on df and dftest using both all features
      and a subset of the top features as indicated by feature importance from the
      random forest classification run by Upsilon
      (paper: https://www.aanda.org/articles/aa/pdf/2016/03/aa27188-15.pdf)
      CURRENTLY returns only kmeans on top features

    color should be None or one of the colors from csv_colors (as a string)
    """
    d = df.copy()
    if dftest is not None:
        dt = dftest.copy()
    if nclusts is None:
        nclusts = len(d.intType.unique())
    # kwargs = {'init':'random'}
    kwargs = {}

    if normfeats:
        d = norm_features(d)
        if dftest is not None:
            dt = norm_features(dt)

    # kmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(d.loc[:,feats])
    topkmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(d)

    # get predictions
    predics = topkmns.predict(d)
    if dftest is not None:
        predics_test = topkmns.predict(dt)

    # get distances from cluster means
    dists = topkmns.transform(d)
    if dftest is not None:
        dists_test = topkmns.transform(dt)

    if dftest is not None:
        return predics, predics_test, dists, dists_test
    else:
        return predics, dists


def do_isolationForest(df, kwargs=None):

    if kwargs is None:
        kwargs = {
            # 'n_estimators': 1000,
            "behaviour": "new",
            # 'max_samples': 1000,
            "random_state": 42,
            "contamination": "auto",
            "max_features": 3,
        }

    forest = IsolationForest(**kwargs).fit(df)

    predics = forest.predict(df)

    return forest, predics


def norm_features(df, algor="minmax"):
    if algor == "minmax":
        return (df - df.min()) / (df.max() - df.min())
    # elif algor == 'standardize':
    # need to finish this...


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
