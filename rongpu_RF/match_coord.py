from __future__ import print_function, division
import numpy as np
from astropy import units as u
from astropy.table import Table
from astropy.coordinates import SkyCoord
from matplotlib.ticker import NullFormatter


def match_coord(ra1, dec1, ra2, dec2, search_radius=1., nthneighbor=1, plot_q=True, verbose=True,
    keep_all_pairs=False):
    '''
    Match objects in (ra2, dec2) to (ra1, dec1). 

    Inputs: 
        RA and Dec of two catalogs;
        search_radius: in arcsec;
        (Optional) keep_all_pairs: if true, then all matched pairs are kept; otherwise, if more than
        one object in t2 is match to the same object in t1 (i.e. double match), only the closest pair
        is kept.

    Outputs: 
        idx1, idx2: indices of matched objects in the two catalogs;
        d2d: distances (in arcsec);
        d_ra, d_dec: the differences (in arcsec) in RA and Dec; note that d_ra is the actual angular 
        separation;
    '''
    
    t1 = Table()
    t2 = Table()
    
    # protect the global variables from being changed by np.sort
    ra1, dec1, ra2, dec2 = map(np.copy, [ra1, dec1, ra2, dec2])

    t1['ra'] = ra1
    t2['ra'] = ra2
    t1['dec'] = dec1
    t2['dec'] = dec2
    
    t1['id'] = np.arange(len(t1))
    t2['id'] = np.arange(len(t2))
    
    # Matching catalogs
    sky1 = SkyCoord(ra1*u.degree,dec1*u.degree, frame='icrs')
    sky2 = SkyCoord(ra2*u.degree,dec2*u.degree, frame='icrs')
    idx, d2d, d3d = sky2.match_to_catalog_sky(sky1, nthneighbor=nthneighbor)
    # This finds a match for each object in t2. Not all objects in t1 catalog are included in the result. 
    
    # convert distances to numpy array in arcsec
    d2d = np.array(d2d.to(u.arcsec))

    matchlist = d2d<search_radius
    
    if np.sum(matchlist)==0:
        if verbose:
            print('0 matches')
        return np.array([], dtype=int), np.array([], dtype=int), np.array([]), np.array([]), np.array([])

    t2['idx'] = idx
    t2['d2d'] = d2d
    t2 = t2[matchlist]
    
    init_count = np.sum(matchlist)

    #--------------------------------removing doubly matched objects--------------------------------
    # if more than one object in t2 is matched to the same object in t1, keep only the closest match
    if not keep_all_pairs:
    
        t2.sort('idx')
        i = 0
        while i<=len(t2)-2:
            if t2['idx'][i]>=0 and t2['idx'][i]==t2['idx'][i+1]:
                end = i+1
                while end+1<=len(t2)-1 and t2['idx'][i]==t2['idx'][end+1]:
                    end = end+1
                findmin = np.argmin(t2['d2d'][i:end+1])
                for j in range(i,end+1):
                    if j!=i+findmin:
                        t2['idx'][j]=-99
                i = end+1
            else:
                i = i+1

        mask_match = t2['idx']>=0
        t2 = t2[mask_match]

        t2.sort('id')

        if verbose:
            print('Doubly matched objects = %d'%(init_count-len(t2)))
    
    # -----------------------------------------------------------------------------------------
    if verbose:
        print('Final matched objects = %d'%len(t2))

    # This rearranges t1 to match t2 by index.
    t1 = t1[t2['idx']]

    d_ra = (t2['ra']-t1['ra']) * 3600.    # in arcsec
    d_dec = (t2['dec']-t1['dec']) * 3600. # in arcsec
    ##### Convert d_ra to actual arcsecs #####
    mask = d_ra > 180*3600
    d_ra[mask] = d_ra[mask] - 360.*3600
    mask = d_ra < -180*3600
    d_ra[mask] = d_ra[mask] + 360.*3600
    d_ra = d_ra * np.cos(t1['dec']/180*np.pi)
    ##########################################

    if plot_q:
        markersize = np.max([0.01, np.min([10, 0.3*100000/len(d_ra)])])    
        axis = [-search_radius*1.05, search_radius*1.05, -search_radius*1.05, search_radius*1.05]
        scatter_plot(d_ra, d_dec, markersize=markersize, alpha=0.5, axis=axis)

    return np.array(t1['id']), np.array(t2['id']), np.array(t2['d2d']), np.array(d_ra), np.array(d_dec)


def find_neighbor(ra1, dec1, search_radius=1., nthneighbor=1):
    '''
    Find the n-th nearest neighbor. 
    nthneighbor: the n-th neighbor; the nthneighbor=1 is the first neighbor other than itself. 
    '''
    
    t1 = Table()
    t1['ra'] = ra1
    t1['dec'] = dec1
    t1['id'] = np.arange(len(t1))

    # Matching catalogs
    sky1 = SkyCoord(ra1*u.degree,dec1*u.degree, frame='icrs')
    idx, d2d, d3d = sky1.match_to_catalog_sky(sky1, nthneighbor=(nthneighbor+1))
    # This find a match for each object in t2. Not all objects in t1 catalog is included in the result. 
    
    # convert distances to numpy array in arcsec
    d2d = np.array(d2d.to(u.arcsec))

    matchlist = d2d<search_radius    
    t1['idx'] = idx
    t1['d2d'] = d2d
    t1 = t1[matchlist]
    
    return np.array(t1['id']), np.array(t1['idx']), np.array(t1['d2d'])



def match_self(ra, dec, search_radius=1., return_indices=False, plot_q=False):
    '''
    Find objects that has a neighbor within search_radius arcsec. 

    Return: 
    Number of suspected duplicates. 
    (Optional) idx1, idx2: arrays of indices of suspected duplicates. 
        (Both arrays are returned so one can recreate the scatter plot)
    '''

    ra = np.array(ra)
    dec = np.array(dec)
    skycat = SkyCoord(ra*u.degree,dec*u.degree, frame='icrs')
    idx, d2d, _ = skycat.match_to_catalog_sky(skycat, nthneighbor=2)

    # convert distances to numpy array in arcsec
    d2d = np.array(d2d.to(u.arcsec))

    mask = d2d<search_radius
    print(np.sum(mask), "objects with a nearby neighbor")
    n_duplicates = np.sum(mask)
    idx1 = np.arange(len(ra))[mask]
    idx2 = idx[mask]

    if plot_q and (n_duplicates!=0):
        d_ra = (ra[idx1] - ra[idx2]) * 3600. # arcsec
        d_dec = (dec[idx1] - dec[idx2]) * 3600. # arcsec
        ##### Convert d_ra to actual arcsecs #####
        mask = d_ra > 180*3600
        d_ra[mask] = d_ra[mask] - 360.*3600
        mask = d_ra < -180*3600
        d_ra[mask] = d_ra[mask] + 360.*3600
        d_ra = d_ra * np.cos(dec[idx1]/180*np.pi)
        ##########################################
        scatter_plot(d_ra, d_dec)

    if return_indices:
        return n_duplicates, idx1, idx2
    else:
        return n_duplicates



def search_around(ra1, dec1, ra2, dec2, search_radius=1., verbose=True):
    '''
    Using the astropy.coordinates.search_around_sky module to find all pairs within
    some search radius.

    Inputs: 
    RA and Dec of two catalogs;
    search_radius (arcsec);


    Outputs: 
        idx1, idx2: indices of matched objects in the two catalogs;
        d2d: angular distances (arcsec);
        d_ra, d_dec: the differences in RA and Dec (arcsec); 
    '''
    
    # protect the global variables from being changed by np.sort
    ra1, dec1, ra2, dec2 = map(np.copy, [ra1, dec1, ra2, dec2])
    
    # Matching catalogs
    sky1 = SkyCoord(ra1*u.degree,dec1*u.degree, frame='icrs')
    sky2 = SkyCoord(ra2*u.degree,dec2*u.degree, frame='icrs')
    idx1, idx2, d2d, d3d = sky2.search_around_sky(sky1, seplimit=search_radius*u.arcsec)
    if verbose:
        print('%d nearby objects'%len(idx1))
    
    # convert distances to numpy array in arcsec
    d2d = np.array(d2d.to(u.arcsec))


    d_ra = (ra2[idx2]-ra1[idx1])*3600.    # in arcsec
    d_dec = (dec2[idx2]-dec1[idx1])*3600. # in arcsec
    ##### Convert d_ra to actual arcsecs #####
    mask = d_ra > 180*3600
    d_ra[mask] = d_ra[mask] - 360.*3600
    mask = d_ra < -180*3600
    d_ra[mask] = d_ra[mask] + 360.*3600
    d_ra = d_ra * np.cos(dec1[idx1]/180*np.pi)
    ##########################################

    return idx1, idx2, d2d, d_ra, d_dec



def scatter_plot(d_ra, d_dec, markersize=1, alpha=1, figsize=8, axis=None, title='', show=True,
    xlabel='RA2 - RA1 (arcsec)', ylabel=('DEC2 - DEC1 (arcsec)')):
    '''
    INPUTS:

     d_ra, d_dec (arcsec): array of RA and Dec difference in arcsec
     (optional): dec (degrees): if specificied, d_ra's are plotted in actual angles
    
    OUTPUTS:

     axScatter: scatter-histogram plot
    '''

    import matplotlib.pyplot as plt

    nullfmt = NullFormatter()         # no labels

    # definitions for the axes
    left, width = 0.1, 0.85
    bottom, height = 0.1, 0.85

    rect_scatter = [left, bottom, width, height]
    rect_histx = [left, bottom, width, 0.3]
    rect_histy = [left, bottom, 0.3, height]

    # start with a rectangular Figure
    plt.figure(figsize=(figsize, figsize))

    axScatter = plt.axes(rect_scatter)
    axScatter.set_title(title)
    axHistx = plt.axes(rect_histx)
    axHisty = plt.axes(rect_histy)

    axScatter.plot(d_ra, d_dec, 'k.', markersize=markersize, alpha=alpha)

    axHistx.hist(d_ra, bins=100, histtype='step', color='r', linewidth=2)
    axHisty.hist(d_dec, bins=100, histtype='step', color='r', linewidth=2, orientation='horizontal')

    if axis is None:
        axHistx.set_xlim(axScatter.get_xlim())
        axHisty.set_ylim(axScatter.get_ylim())
    else:
        axHistx.set_xlim(axis[:2])
        axHisty.set_ylim(axis[2:])
        axScatter.set_xlim(axis[:2])
        axScatter.set_ylim(axis[2:])

    axHistx.axis('off')
    axHisty.axis('off')

    axScatter.axhline(0, color='r', linestyle='--', linewidth=1.2)
    axScatter.axvline(0, color='r', linestyle='--', linewidth=1.2)
    axScatter.set_xlabel(xlabel)
    axScatter.set_ylabel(ylabel)
            
    if show==True:
        plt.show()
    else:
        return axScatter