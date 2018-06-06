from astropy.io import fits
import numpy as np
import os
from time import strftime, gmtime

## specify source files
path_to_cal = 'ArchCal/' # source directory
dates = [f for f in os.listdir(path_to_cal) if not f.startswith('.')] # index date folders in ArchCal
path_to_cal += max(dates)+'/' # specify path as most recent date
filenames = [f for f in os.listdir(path_to_cal) if not f.startswith('.')] # list of filenames to process

print('Searching %s for calibraton files...' % path_to_cal)

bias,dark,Red,Green,Blue,R,V,B,Halpha,Lum,filters = [],[],[],[],[],[],[],[],[],[],[] # initialize lists
# lists are used to store the data for each calibration file and then combine into a master

## sort the calibration images by type and store them in arrays
for filename in filenames:
    img = fits.open(path_to_cal+filename) # open each image
    data = img[0].data # split into data and header
    header = img[0].header
    if header['IMAGETYP']=='Bias Frame':
        bias_header = img[0].header # save header for each image type to attach to master version
        bias.append(data) # add data array to type list
    if header['IMAGETYP']=='Dark Frame':
        dark_header = img[0].header
        dark.append(data)
    if header['IMAGETYP']=='Flat Field':
        flat_header = img[0].header
        filters.append(header['FILTER']) # store the filters found in this directory in a list
        # so that we don't attempt to create new master flats with filters we did not have raw flats for
        code = header['FILTER']+'.append(data)' # string operations to add data to filter-specific list
        exec(code)
    del img
print('Indexed files:')
print('   Bias: %s' % len(bias))
print('   Dark: %s' % len(dark))
print('   Red Flat: %s' % len(Red))
print('   Green Flat: %s' % len(Green))
print('   Blue Flat: %s' % len(Blue))
print('   R Flat: %s' % len(R))
print('   V Flat: %s' % len(V))
print('   B Flat: %s' % len(B))
print('   Halpha Flat: %s' % len(Halpha))
print('   Lum Flat: %s' % len(Lum))

## make the masters
bias_master = np.median(np.array(bias),axis=0)
dark_master = np.median(np.array(dark)-bias_master,axis=0) # scalable dark with bias already removed
print('Constructed master bias')
print('Constructed master dark')
for i in np.unique(filters): # for each UNIQUE filter
    code = i+"_master = np.median("+i+",axis=0)/np.max(np.median("+i+",axis=0))"  # more string operations
    # normalize flat field
    exec(code)
    print('Constructed master %s flat' % i)


## write the masters to fits files

for j in ['bias','dark']: # for now: do not overwrite old bias / dark masters
    code = "fits.writeto('MasterCal/"+j+"_master.fit',"+j+"_master,header="+j+"_header,overwrite=False)"
    try:
        exec(code)
        print('Wrote master %s to file MasterCal/%s_master.fit' % (j,j))   
    except:
        print('Bias or dark master already exists, no new file written')
        pass 

for j in np.unique(filters): # only overwrite flats for the unique filters that we chose to update that night
    code = "fits.writeto('MasterCal/flat_master_"+j+".fit',"+j+"_master,header=flat_header,overwrite=True)"
    exec(code)   
    print('Wrote master %s flat to file MasterCal/flat_master_%s.fit' % (j,j))

