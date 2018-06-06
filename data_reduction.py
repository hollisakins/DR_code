from astropy.io import fits
import numpy as np
import os
from time import strftime, gmtime, strptime
import sys


def calibrate(obj,name):
    h = obj[0].header 
    if np.size(obj[0].data)==8487264:
        if h['XBINNING']==1 and h['YBINNING']==1:
            if h['CCD-TEMP']<=-4.0:
                if h.get('CALSTAT',default=0)==0:
                    return True
                if h.get('CALSTAT',default=0)=='BDF' or h.get('CALSTAT',default=0)=='DF':
                    return 'Redundant' 
                if h.get('CALSTAT',default=0)=='D':
                    return 'OnlyDark'
            else:
                return 'Temp'    
        else:
            return 'Binning'
    else: 
        return 'Size'

def write_to_header(head):
    if head.get('CALSTAT',default=0)==0: # if there is no calstat field in the header
        head.append(('CALSTAT','BDF','Status of Calibration')) # add one
    else:
        head['CALSTAT']='BDF' # otherwise set the value of calstat to BDF


def save_file(head,data,day):
    if not os.path.exists('Calibrated Images/'+day): 
        os.makedirs('Calibrated Images/'+day) 
    
    fits.writeto('Calibrated Images/'+day+'/'+filename.replace(".fit","_calibrated.fit"),data,head,overwrite=True)
    print('Wrote file to Calibrated Images/'+day)


## specify source files
path_to_files = 'ArchSky/'
path_to_cal = 'MasterCal/'
dates = [f for f in os.listdir(path_to_files) if not f.startswith('.')] # index date folders in ArchSky
path_to_files += max(dates)+'/' # specify path as most recent date
list_of_files = [f for f in os.listdir(path_to_files) if os.path.isfile(os.path.join(path_to_files,f)) and not f.startswith('.')]

print('Searching %s for sky images...' % path_to_files)
print('Searching %s for calibration files...' % path_to_cal)

try: 
    bias_fits = fits.open(path_to_cal+'bias_master.fit') 
    print('Successfully opened bias master %s' % path_to_cal+'bias_master.fit')
except: # if you encounter error
    print('Failed to open bias master %s' % path_to_cal+'bias_master.fit. Wrote to DR_errorlog.txt')
    with open('DR_errorlog.txt','a') as erlog: # open error log and write to it
        erlog.write('Missing bias master at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'. Auto DR halted.\n')
    sys.exit() # exit the program since you can't calibrate files without a bias frame

bias_h = bias_fits[0].header # split into header and data
bias = bias_fits[0].data


try:
    dark_fits = fits.open(path_to_cal+'dark_master.fit') 
    print('Successfully opened dark master %s' % path_to_cal+'dark_master.fit')
except:
    print('Failed to open dark master %s' % path_to_cal+'dark_master.fit. Wrote to DR_errorlog.txt')
    with open('DR_errorlog.txt','a') as erlog:
        erlog.write('Missing dark master at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'. Auto DR halted.\n')
    sys.exit()

dark_h = dark_fits[0].header
dark = dark_fits[0].data
dxptime = dark_h['EXPTIME'] # store the exposure time for the dark master for scaling purposes


print('-'*20)
print('Prepping calibration of %s files' % len(list_of_files))
print('-'*20)


for filename in list_of_files:
    light_fits = fits.open(path_to_files+filename) # open each image
    light_h = light_fits[0].header 
    light = light_fits[0].data
    exptime = light_h['EXPTIME'] # store light image exposure time

    print('Successfully opened '+light_h['FILTER']+' image '+path_to_files+filename)


    try: # open filter-specific flat
        flat_fits = fits.open(path_to_cal+'flat_master_'+light_h['FILTER']+'.fit') 
        print('Successfully opened '+light_h['FILTER']+' flat master '+path_to_cal+'flat_master_'+light_h['FILTER']+'.fit')
    except:
        print('Failed to open flat master %s' % path_to_cal+'flat_master_'+light_h['FILTER']+'.fit. Wrote to DR_errorlog.txt')
        with open('DR_errorlog.txt','a') as erlog:
            erlog.write('Missing '+light_h['FILTER']+'flat master at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'. Auto DR halted.\n')
        sys.exit()
    
    flat_h = flat_fits[0].header
    flat = flat_fits[0].data


    ## perform the actual data reduction
    if calibrate(light_fits,filename)==True:
        print('Calibrating image %s...' % filename)
        print(np.size(light))
        bias_corrected_image = light - bias # subtract the bias
        dark_corrected_image = bias_corrected_image - (exptime/dxptime)*dark # scale the dark linearly w/ exptime and subtract
        final_image = dark_corrected_image / flat # divide by the flat field (already normalized)
        
        write_to_header(light_h)
        save_file(light_h, final_image, max(dates))
        print('-'*20)


    elif calibrate(light_fits,filename)=='OnlyDark': # auto dark
        print('Calibrating image %s...' % filename)
        
        final_image = light / flat # divide by the flat field

        write_to_header(light_h)
        save_file(light_h, final_image, max(dates))
        print('-'*20)


    elif calibrate(light_fits,filename)=='Redundant':
        with open('DR_errorlog.txt','a') as erlog:
            erlog.write('Attempted redundant calibration on '+filename+' at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'\n')
        print('Image %s already calibrated' % filename)
        save_file(light_h, final_image, max(dates))
        print('-'*20)
        

    elif calibrate(light_fits,filename)=='Binning':
        with open('DR_errorlog.txt','a') as erlog:
            erlog.write('Image '+filename+' not 1x1 binning, rejected calibration at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'.')
        print('Image %s not 1x1 binning' % filename)
        print('-'*20)

    elif calibrate(light_fits,filename)=='Temp':
        with open('DR_errorlog.txt','a') as erlog:
            erlog.write('Image '+filename+' temp '+light_h['CCD-TEMP']+' degrees C, rejected calibration at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'.')
        print('Image %s taken at > -4 degrees C' % filename)
        print('-'*20)

    elif calibrate(light_fits,filename)=='Size':
        with open('DR_errorlog.txt','a') as erlog:
            erlog.write('Image '+filename+' not full size, rejected calibration at '+strftime("%Y%m%d %H:%M GMT", gmtime())+'.')
        print('Image %s taken at > -4 degrees C' % filename)
        print('-'*20)


    del light_fits,flat_fits # stop holding files in memory 
del bias_fits,dark_fits