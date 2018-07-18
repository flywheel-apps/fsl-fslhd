#!/usr/bin/env python

import os
import re
import csv
import json
import string
import logging
import datetime
from pprint import pprint

logging.basicConfig()
log = logging.getLogger('fslhd')

def assign_type(s):
    """
    Sets the type of a given input.
    """
    if type(s) == list:
        try:
            return [ int(x) for x in s ]
        except ValueError:
            try:
                return [ float(x) for x in s ]
            except ValueError:
                return [ format_string(x) for x in s if len(x) > 0 ]
    else:
        s = str(s)
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return format_string(s)


def format_string(in_string):
    """
    Remove non-ascii characters.
    """
    formatted = re.sub(r'[^\x00-\x7f]',r'', str(in_string)) #
    formatted = filter(lambda x: x in string.printable, formatted)
    if len(formatted) == 1 and formatted == '?':
        formatted = None
    return formatted#.strip()



def _extract_nifti_header(fslhd_xml):
    """
    Extract nifti header from xml
    """
    import csv

    with open(fslhd_xml, 'r') as f:
        lines = f.readlines()

    nifti_header = {}
    for l in lines[1:-2]:
        string = l.replace('\n', '')
        k,v = string.split(' = ')
        key = k.strip()
        value = v.replace('\'','').strip()
        nifti_header[key] = assign_type(value)

    return nifti_header


def _write_metadata(nifti_file_name, fslhd_xml, output_json, outbase='/flywheel/v0/output'):
    """
    Extracts metadata from nifti file header and writes to .metadata.json.
    """
    import json

    # Grab the nifti_header from the xml
    nifti_header = _extract_nifti_header(fslhd_xml)

    # Build metadata
    metadata = {}

    # File metadata
    nifti_file = {}
    nifti_file['name'] = os.path.basename(nifti_file_name)
    nifti_file['info'] = {}
    nifti_file['info']['fslhd'] = _extract_nifti_header(fslhd_xml)

    # Append the nifti_file to the files array
    metadata['acquisition'] = {}
    metadata['acquisition']['files'] = [nifti_file]

    # Write out the metadata to file (.metadata.json)
    metafile_outname = os.path.join(outbase,'.metadata.json')
    with open(metafile_outname, 'w') as metafile:
        json.dump(metadata, metafile)

    # Write out the fslhd data as a jsonfile
    if output_json:
        outname = os.path.join(outbase, os.path.basename(nifti_file_name).split('.nii')[0]) + '.json'
        with open(outname, 'w') as f:
            json.dump(nifti_file['info']['fslhd'], f)

    # Show the metadata
    pprint(metadata)

    return metafile_outname


if __name__ == '__main__':
    """
    Extracts metadata from nifti file header and writes to .metadata.json.
    """
    import json
    import shlex
    import subprocess

    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('fslhd').setLevel(logging.INFO)
    log.info('  start: %s' % datetime.datetime.utcnow())

    # Grab Config
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    pprint(config)
    nifti_file_path = config['inputs']['nifti']['location']['path']
    nifti_file_name = config['inputs']['nifti']['location']['name']
    output_json = config['config']['output_json']

    # Generate xml
    fslhd_xml = '/tmp/fslhd_xml.xml'
    # cmd = shlex.split("fsl5.0-fslhd -x " + " %s  >  %s" % (nifti_file_path, fslhd_xml))
    cmd = "fsl5.0-fslhd -x " + "\"%s\"  >  %s" % (nifti_file_path, fslhd_xml)
    print(cmd)
    status = os.system(cmd)

    if status:
        log.info('Could not extract nifti file header! Exiting')
        os.sys.exit(1)

    metadatafile = _write_metadata(nifti_file_path, fslhd_xml, output_json)

    if os.path.exists(metadatafile):
        log.info('  generated %s' % metadatafile)
    else:
        log.info('  failure! %s was not generated!' % metadatafile)

    log.info('  stop: %s' % datetime.datetime.utcnow())
