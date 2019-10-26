from __future__ import division, print_function
import sys, os, time, gc, warnings
import numpy as np
from astropy.table import Table
import match_coord

from sklearn.ensemble import RandomForestRegressor
from sklearn.externals import joblib

nmad = lambda x: 1.48 * np.median(np.abs(x-np.median(x)))

def icomp(fracdev, fracexp, r_dev, r_exp, r):
    '''
    Surface brightness of a composite object. 
    '''
    idev = fracdev * np.exp(-7.669 * ((r/r_dev)**(1/4) - 1))
    iexp = fracexp * np.exp(-1.67835 * (r/r_exp - 1))
    return idev + iexp


def comp_radius(fracdev, fracexp, r_dev, r_exp, rmax=100, dr=0.01):
    '''
    Calculate the half-light radius of composite objects. 
    Factor of 2*Pi and normalization are ignored. 
    '''
    # total flux
    ftot = fracdev * r_dev**2 * 3.60732 + fracexp * r_exp**2 * 1.90166
    f = 0
    # dr = 0.01 # integration spacing
    r = -dr/2
    while (f<(ftot/2)) and (r<rmax):
        r += dr
        f += r * icomp(fracdev, fracexp, r_dev, r_exp, r) * dr
    return r


def unpack(cat):

    warnings.simplefilter("ignore")
    gmag = 22.5-2.5*np.log10(cat['FLUX_G'])
    rmag = 22.5-2.5*np.log10(cat['FLUX_R'])
    zmag = 22.5-2.5*np.log10(cat['FLUX_Z'])
    w1mag = 22.5-2.5*np.log10(cat['FLUX_W1'])
    w2mag = 22.5-2.5*np.log10(cat['FLUX_W2'])
    
    return gmag, rmag, zmag, w1mag, w2mag


def get_radius(cat):

    radii = np.ones(len(cat))*(-99.)
    # Watch out for the space!
    mask = (cat['TYPE']=='DEV') | (cat['TYPE']=='DEV ')
    radii[mask] = cat['SHAPEDEV_R'][mask]
    # REX type added in DR5
    mask = (cat['TYPE']=='EXP') | (cat['TYPE']=='SIMP') | (cat['TYPE']=='PSF') | (cat['TYPE']=='REX')
    mask |= (cat['TYPE']=='EXP ') | (cat['TYPE']=='PSF ') | (cat['TYPE']=='REX ')
    radii[mask] = cat['SHAPEEXP_R'][mask]

    print('Computing radius for COMP objects')
    comp_idx = np.where(cat['TYPE']=='COMP')[0]
    comp_count = len(comp_idx)
    rcomp = np.zeros(comp_count)
    print(comp_count)
    for obj_index in range(comp_count):
        # # These two lines throw errors
        # if (obj_index+1)%(comp_count//10)==0:
        #     print('{:.2f}%'.format(obj_index/(comp_count)*100))
        rcomp[obj_index] = comp_radius(cat['FRACDEV'][comp_idx[obj_index]], (1-cat['FRACDEV'][comp_idx[obj_index]]), 
                                   cat['SHAPEDEV_R'][comp_idx[obj_index]], cat['SHAPEEXP_R'][comp_idx[obj_index]],
                                   rmax=30, dr=0.01)
    radii[comp_idx] = rcomp

    mask = rcomp>=30
    print(np.sum(mask), 'objects with no solution in r < 30 arcsec')

    return radii


def compute_photoz(cat, dr, n_perturb=20, n_estimators=50):

    if dr=='6' or dr==6:
        specz_train_path = '/global/cscratch1/sd/rongpu/dr6_lrg_photoz/individual_trees/20181008/truth_combined_ds_dr6.0_20181008_train.fits'
        specz_full_path = '/global/cscratch1/sd/rongpu/dr6_lrg_photoz/truth/truth_combined_dr6.0_20181008.fits'
        forest_path = '/global/cscratch1/sd/rongpu/dr6_lrg_photoz/individual_trees/20181008/regrf_20181008_'
    elif dr=='7' or dr==7:
        specz_train_path = '/global/cscratch1/sd/rongpu/dr7_lrg_photoz/individual_trees/20180823/truth_combined_ds_20180823_train.fits'
        specz_full_path = '/global/cscratch1/sd/rongpu/dr7_lrg_photoz/truth/truth_combined_20180823.fits'
        forest_path = '/global/cscratch1/sd/rongpu/dr7_lrg_photoz/individual_trees/20180823/regrf_20180823_'
    else:
        raise ValueError('Invalid DR value!')

    cat_pz = Table()

    gmag, rmag, zmag, w1mag, w2mag = unpack(cat)

    gmag[~np.isfinite(gmag)] = 99.
    rmag[~np.isfinite(rmag)] = 99.
    zmag[~np.isfinite(zmag)] = 99.
    w1mag[~np.isfinite(w1mag)] = 99.
    w2mag[~np.isfinite(w2mag)] = 99.

    # # objects with zero color(s):
    # mask_bad = (gmag-rmag==0) | (rmag-zmag==0) | (zmag-w1mag==0) | (w1mag-w2mag==0)
    # print(np.sum(mask_bad), 'objects without photo-z due to zero color')
    # # almost all of these "bad" objects are due to w1-w1==0 and 
    # # are eventually removed by the non-stellar cut

    # axis ratio
    ##################################################################################
    # The code is correct, but for robustness, next time I should include 'EXP ' etc.
    ##################################################################################
    e = np.zeros(len(cat)) # ellipticity is zero for PSF and SIMP objects
    mask = cat['TYPE']=='EXP'
    e[mask] = (np.sqrt(cat['SHAPEEXP_E1']**2+cat['SHAPEEXP_E2']**2))[mask]
    mask = cat['TYPE']=='DEV'
    e[mask] = (np.sqrt(cat['SHAPEDEV_E1']**2+cat['SHAPEDEV_E2']**2))[mask]
    mask = cat['TYPE']=='COMP'
    e[mask] = ((1-cat['FRACDEV']) * np.sqrt(cat['SHAPEEXP_E1']**2+cat['SHAPEEXP_E2']**2) \
              + cat['FRACDEV'] * np.sqrt(cat['SHAPEDEV_E1']**2+cat['SHAPEDEV_E2']**2))[mask]
    q = (1+e)/(1-e)

    # shape probability (definition of shape probability in Soo et al. 2017)
    p = np.ones(len(cat))*0.5
    # mask_chisq = (cat['dchisq_dev']>0) & (cat['dchisq_exp']>0)
    # p[mask_chisq] = cat['dchisq_dev'][mask_chisq]/(cat['dchisq_dev']+cat['dchisq_exp'])[mask_chisq]
    mask_chisq = (cat['DCHISQ'][:, 3]>0) & (cat['DCHISQ'][:, 2]>0)
    p[mask_chisq] = cat['DCHISQ'][:, 3][mask_chisq]/(cat['DCHISQ'][:, 3]+cat['DCHISQ'][:, 2])[mask_chisq]

    radius = cat['radius']

    ##################### Photo-z point estimates and errors #########################

    print('Computing photo-z\'s and errors with perturbed photometry')

    col_list = ['FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2']
    mag_max = 30
    mag_fill = 100

    # n_estimators = 50 # Number of trees in a forest
    # n_perturb = 20 # Number of perturbed sample
    z_phot_array = np.zeros((len(cat), n_perturb*n_estimators), dtype='float32')
    np.random.seed(1456)
        
    for tree_index in range(n_estimators):

        print(tree_index*n_perturb,'/', n_estimators*n_perturb)

        # Load single pre-trained tree
        regrf = joblib.load(forest_path+'{:d}.pkl'.format(tree_index))

        # Predict!
        cat1 = Table()
        for perturb_index in range(n_perturb):

            # print(perturb_index+tree_index*n_perturb,'/', n_estimators*n_perturb)

            cat1['FLUX_G'] = np.array(cat['FLUX_G']+np.random.randn(len(cat))*(1/np.sqrt(cat['FLUX_IVAR_G'])), dtype='float32')
            cat1['FLUX_R'] = np.array(cat['FLUX_R']+np.random.randn(len(cat))*(1/np.sqrt(cat['FLUX_IVAR_R'])), dtype='float32')
            cat1['FLUX_Z'] = np.array(cat['FLUX_Z']+np.random.randn(len(cat))*(1/np.sqrt(cat['FLUX_IVAR_Z'])), dtype='float32')
            cat1['FLUX_W1'] = np.array(cat['FLUX_W1']+np.random.randn(len(cat))*(1/np.sqrt(cat['FLUX_IVAR_W1'])), dtype='float32')
            cat1['FLUX_W2'] = np.array(cat['FLUX_W2']+np.random.randn(len(cat))*(1/np.sqrt(cat['FLUX_IVAR_W2'])), dtype='float32')

            # Fill in negative fluxes
            for index in range(len(col_list)):
                mask = ((cat1[col_list[index]]<10**(0.4*(22.5-mag_max))) | (cat1[col_list[index]]==np.inf))
                cat1[col_list[index]][mask] = 10**(0.4*(22.5-mag_fill))

            gmag1, rmag1, zmag1, w1mag1, w2mag1 = unpack(cat1)
            data1 = np.column_stack((gmag1-rmag1, rmag1-zmag1, zmag1-w1mag1, w1mag1-w2mag1, rmag1, radius, q, p))

            z_phot_array[:, tree_index*n_perturb+perturb_index] = regrf.predict(data1)

        # clear cache
        gc.collect()

    z_phot = np.mean(z_phot_array, axis=1)
    z_phot_err = np.std(z_phot_array, axis=1)
    # z_phot[mask_bad] = -99
    cat_pz['z_phot'] = z_phot
    cat_pz['z_phot_err'] = z_phot_err
    cat_pz['z_phot_all'] = z_phot_array

    # ######################## Match to truth table #############################

    print('Matching to truth table')

    # Catalog used for training:
    cat_train = Table.read(specz_train_path)
    # Full truth catalog (not all objects were used for training):
    cat_full = Table.read(specz_full_path)

    cat_pz['z_spec'] = np.ones(len(cat), dtype='float32')*(-99.)
    cat_pz['survey'] = '       '
    cat_pz['training'] = False

    ra1 = np.array(cat_full['RA'])
    dec1 = np.array(cat_full['DEC'])
    ra2 = np.array(cat['RA'])
    dec2 = np.array(cat['DEC'])
    idx1, idx2, _, _, _, = match_coord.match_coord(ra1, dec1, ra2, dec2, search_radius=0.1, plot_q=False)
    cat_pz['z_spec'][idx2] = cat_full['redshift'][idx1]
    cat_pz['survey'][idx2] = cat_full['survey'][idx1]

    ra1 = np.array(cat_train['RA'])
    dec1 = np.array(cat_train['DEC'])
    ra2 = np.array(cat['RA'])
    dec2 = np.array(cat['DEC'])
    idx1, idx2, _, _, _, = match_coord.match_coord(ra1, dec1, ra2, dec2, search_radius=0.1, plot_q=False)
    cat_pz['training'][idx2] = True

    ##########################################################################################

    return cat_pz