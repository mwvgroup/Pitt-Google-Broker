

from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import confusion_matrix
from sklearn.utils.multiclass import unique_labels

csv_colors = ['BP-RP','J-K','W1-W2','W3-W4','B-V']

def load_clust_plot(f='upsilon_features.dat', fcsv='asassn-catalog.csv', cfeat=None, normfeats=True):
    """ Loads a dataframe of features from file f.
        Makes various cuts and separations of the data.
        Runs Kmeans clustering.
        Plots the results.
    """

    # load the data
    df = load_features(f=f, fcsv=fcsv, cfeat=cfeat)

    # get various slices
    df, dfhi, db, dflow = get_dfs(df, cprob=0.98, ntype_hi=5000, ntype_low=100)

    # run Kmeans
    predics, predics_test, dists, dists_test = get_kclusts(db, dflow,
                                            normfeats=normfeats, color=cfeat)

    # make plots
    make_plots(db, dflow, predics, predics_test, cfeat=cfeat, distances=(dists, dists_test))

    return db, dflow, predics, predics_test


def load_features(f='upsilon_features.dat', fcsv='asassn-catalog.csv', cfeat=None):

    # load features extracted from light curves using Upsilon
    df = pd.read_csv(f)
    df = df.set_index('id', drop=False)

    # add color info from csv file
    dfcsv = pd.read_csv(fcsv)
    dfcsv = dfcsv.astype({'id':'str'})
    dfcsv = dfcsv.set_index('id', drop=False)
    dfcsv = dfcsv.loc[dfcsv.id.isin(list(df.id)),:]
    for c in csv_colors:
        df[c] = dfcsv[c]

    if cfeat is not None:
        df = df.dropna(subset=[cfeat])

    return df


def get_dfs(df, cprob=0.99, ntype_hi=1000, ntype_low=100):
    """
    Returns:
        original df with newType, intType, numinType columns added

        dfhi with rows of df satisfying
            class_probability > cprob,
            numinType > ntype_hi

        dfhi_blnc, same as dfhi but with balanced classes (the same number of stars in each class)

        dflow composed of classes numinType < ntype_low
    """

    # consolidate types ending with ":" and convert types to ints
    df['newType'] = df.Type.apply(lambda x: x if x[-1]!=":" else x[:-1])
    df, sz = set_type_info(df)

    dfhi = df.loc[df.class_probability > cprob, :]
    dfhi, sz = set_type_info(dfhi)
    dfhi = dfhi.loc[dfhi.numinType > ntype_hi, :]
    dfhi, sz = set_type_info(dfhi)

    # balance number of samples in each class
    typs = list(dfhi.newType.unique())
    l = sz.loc[sz.index.isin(typs)].sort_values(ascending=False).iloc[-1] # smallest number of samples
    lst = []
    for t in typs:
        lst.append(dfhi.loc[dfhi.newType==t,:].sample(l))
    dfhi_blnc = pd.concat(lst, axis=0)
    dfhi_blnc, __ = set_type_info(dfhi_blnc)

    #
    dflow = df.loc[df.numinType < ntype_low, :]
    dflow, sz = set_type_info(dflow)

    return df, dfhi, dfhi_blnc, dflow


def set_type_info(df):
    """ Adds columns
          'newType': which merges Types ending in ":" with the base Type
          'numinType', number of stars of this type
          'intType', converts the Type str to an integer for classification
    """
    d = df.copy()
    sz = d.groupby('newType').size()
    type2int = dict([(t,i) for i,t in enumerate(sz.sort_values(ascending=False).index)])

    d['numinType'] = d.newType.map(dict(sz))
    d['intType'] = d.newType.map(type2int)

    return d, sz

def get_kclusts(df, dftest, which='ups', normfeats=True, color=None):
    """ Runs Kmeans clustering using training set df.
        Returns various dataframes of predictions on df and dftest using both all features
          and a subset of the top features as indicated by feature importance from the
          random forest classification run by Upsilon
          (paper: https://www.aanda.org/articles/aa/pdf/2016/03/aa27188-15.pdf)

        color should be None or one of the colors from csv_colors (as a string)
    """
    d = df.copy()
    dt = dftest.copy()
    nclusts = len(d.intType.unique())
    # kwargs = {'init':'random'}
    kwargs = {}

    if which == 'ups':
        feats = ['amplitude', 'cusum', 'eta', 'hl_amp_ratio', 'kurtosis',
               'period', 'period_uncertainty',
               'phase_cusum', 'phase_eta', 'phi21', 'phi31', 'quartile31', 'r21',
               'r31', 'shapiro_w', 'skewness', 'slope_per10', 'slope_per90',
               'stetson_k', 'weighted_mean', 'weighted_std']
        topfeats = ['period', 'r21', 'amplitude', 'slope_per10']#, 'quartile31', 'skewness']
    elif which == 'csv':
        feats = ['Mean Vmag', 'amplitude', 'period', 'LKSL Statistic', 'rfr_score']
        topfeats = feats

    if color is not None:
        feats = feats + [color]
        topfeats = topfeats + [color]

    if normfeats:
        d = norm_features(d.loc[:,feats])
        dt = norm_features(dt.loc[:,feats])

    # kmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(d.loc[:,feats])
    topkmns = KMeans(n_clusters=nclusts, random_state=0, **kwargs).fit(d.loc[:,topfeats])

    # get predictions
    predics = topkmns.predict(d.loc[:,topfeats])
    predics_test = topkmns.predict(dt.loc[:,topfeats])

    # get distances from cluster means
    dists = topkmns.transform(d.loc[:,topfeats])
    dists_test = topkmns.transform(dt.loc[:,topfeats])

    return predics, predics_test, dists, dists_test

def norm_features(df):
    return (df-df.min())/(df.max()-df.min())

def make_plots(db, dflow, predics, predics_test, cfeat=None, distances=None):
    """
    Args:
        db: dataframe used to do kmeans training
        dflow: dataframe of testing data
        predics: kmeans predictions on db
        predics_test: kmeans predictions on dflow
        cfeat: string, color used as feature (should be one of csv_colors)
        distances: tuple of (dists, dists_test), distances from cluster means
    """

    # confusion matrix
    for d,p,lbl in zip([db,dflow],[predics, predics_test],['predics', 'predics_test']):
        clss = d.groupby('Type').mean().intType.astype('int').sort_values().index
        plot_confusion_matrix(d.intType, p, clss,
                                  normalize=True, title='Confusion Matrix')
        plt.show(block=False)

    # plot color v amplitude colored by classification
    if cfeat is not None:
        featx, featy = cfeat, 'amplitude'
        plt.figure()
        plt.scatter(db[featx], db[featy], c=predics, alpha=0.5)
        plt.xlabel(featx)
        plt.ylabel(featy)
        plt.show(block=False)


    # distance from cluster centers
    if distances is not None:
        plt.figure()
        ax = plt.gca()
        for d,lbl in zip([distances[0], distances[1]],['training set distance', 'test set distance']):
            dfdis = pd.DataFrame(d)
            mindist = dfdis.min(axis=1)
            mindist.hist(bins=30, ax=ax, label=lbl, alpha=0.5,density=True)
        plt.legend()
        plt.show(block=False)

    return None


def plot_confusion_matrix(y_true, y_pred, classes,normalize=False,title=None,cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if not title:
        if normalize:
            title = 'Normalized confusion matrix'
        else:
            title = 'Confusion matrix, without normalization'

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
    classes = classes[unique_labels(y_true, y_pred)]
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
    ax.figure.colorbar(im, ax=ax)
    # We want to show all ticks...
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           # ... and label them with the respective list entries
           yticklabels=classes,
           title=title,
           ylabel='True label',
           xlabel='Predicted label',
           ylim=(-0.5,len(classes)-0.5))

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    return ax
