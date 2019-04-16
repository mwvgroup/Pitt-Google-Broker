import pandas as pd
from astropy import units as u
from astroquery import xmatch

##
# Example Usage:
#
# from mock_stream import xmatch as xm
#
# # Write a CSV file with RA, DEC:
# fradec = 'mock_stream/data/alerts_radec.csv'
# xm.get_alerts_RA_DEC(fout=fradec)
#
# Query VizieR for cross matches:
table = xm.get_xmatches(fcat1=fradec, cat2='vizier:II/246/out')
#
##
# Helpful links:
# https://astroquery.readthedocs.io/en/latest/#using-astroquery
# https://astroquery.readthedocs.io/en/latest/xmatch/xmatch.html#module-astroquery.xmatch


def get_xmatches(fcat1=fradec, cat2='vizier:II/246/out'):
    """ fcat1 = string. Path to csv file, as written by get_alerts_RA_DEC().

        cat2 = string. Passed through to XMatch.query().

        Returns astropy table. Columns (e.g.):
                ['angDist','alert_id','ra','dec','2MASS','RAJ2000','DEJ2000',
                'errHalfMaj','errHalfMin','errPosAng','Jmag','Hmag','Kmag',
                'e_Jmag','e_Hmag','e_Kmag','Qfl','Rfl','X','MeasureJD']
    """
    table = XMatch.query(cat1=open(fcat1), cat2=cat2, \
                    max_distance=5 * u.arcsec, colRA1='ra', colDec1='dec')

    return table




def get_alerts_RA_DEC(fout=None, max_alerts=1000):
    """ Iterate through alerts and grab RA, DEC.
        Write data to file with format compatible with astroquery.xmatch.query().

        fout =  string, path to save file.
                None, returns the alert data as a Pandas DataFrame.

        max_alerts  = max number of alerts to grab data from.
                    <= 0 will return all available.
    """

    # Grab RA, DEC from each alert
    data_list = []
    for a, alert in enumerate(iter_alerts()):
        alert_id = alert['candid']
        alert_data = get_alert_data(alert_id)

        dat = {}
        dat['alert_id'] = alert_id
        dat['ra'] = alert_data['candidate']['ra']
        dat['dec'] = alert_data['candidate']['dec']
        data_list.append(dat)

        if (a>max_alerts) & (a>0): break

    # Write to file or return as a DataFrame
    df = pd.DataFrame(data_list)
    if fout is not None:
        df.to_csv(fout, sep=',', columns=['alert_id','ra','dec'], header=True, index=False)
    else:
        return df

    return None
