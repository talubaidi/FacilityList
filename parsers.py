from astropy.io import votable
from urllib2 import URLError, HTTPError
import json, os.path, urllib2

# directory containing raw input lists 
# is usually overwritten via setDataDir, but "data/" is default
datadir = "data/"

# add all values that occur in "MeasurementType" here that ought to be replaced by their corresponding UCD
MeasurementType2UCD = {
	"radiowave"			: "em.radio",
	"radio"				: "em.radio",
	"optical"			: "em.opt",
	"gamma-ray"			: "em.gamma",
	"microwaves"		: "em.mm.200-400GHz",
	"microwave"			: "em.mm.200-400GHz",
	"infrared"			: "em.IR",
	"submillimeter"		: "submillimeter", # UCD?
	"ultraviolet"		: "em.UV",
	"radiowaves"		: "em.radio",
	"x-ray"				: "em.X-ray",
	"particles"			: "particles", # UCD?
	"millimeter"		: "em.mm"
}

def setDataDir(dir):
	global datadir 
	datadir = dir

# eplace single measurementType value with respective UCD
def translateUCD(MeasurementType):
	if ( MeasurementType2UCD.has_key ( MeasurementType.lower() ) ):
		return MeasurementType2UCD[ MeasurementType.lower() ]
	else:
		return MeasurementType

# replace all measurementType values of a given object
def replaceUCDinJSON(input_obj):
	print "Replacing values in 'measurementType' with respective UCD..."
	for obj in input_obj:
		if "measurementType" in input_obj[obj]:
			for n,type in enumerate( input_obj[obj]["measurementType"] ):
				input_obj[obj]["measurementType"][n] = translateUCD(type)
	return input_obj
	
def load_existing_json(file):
	if ( file.startswith('http://') or file.startswith('https://') ):
		# URL (web service) has been provided
		try:
			print ( "Retrieving data from web service: " + file )
			response = urllib2.urlopen(urllib2.Request(file))
			return replaceUCDinJSON( json.load(response) )
		except ( URLError, HTTPError ) as e:
			print "ERROR reading data from web service:"
			print e.reason
			return {}			
	else:
		# filename has been provided
		if os.path.isfile(datadir + file):
			print ( "Loading existing JSON file: " + file )
			return replaceUCDinJSON( json.load(open(datadir + file) ) )
		else:
			print ("WARNING: JSON file '" + file + "' does not exist!")
			return {}
		
def load_aas_list():
	authority = 'aas'
	list_file = datadir + 'AAS.xml'
	input = votable.parse(list_file).get_first_table().to_table(use_names_over_ids=True)
	nlines = len(input['ID'])

	obsRangeTypes = ['Gamma-Ray','X-Ray','Ultraviolet','Optical','Infrared','Millimeter','Radio','Particles']
	data = {}
	for irec in range(nlines):
		data_tmp = {}
		data_tmp['alternateName'] = []
		altname_tmp = {}
		
		title = input['ID'][irec].strip()
		altname_tmp['name'] = input['Name'][irec].strip()
		altname_tmp['id'] = title
		altname_tmp['namingAuthority'] = authority
		data_tmp['alternateName'].append(altname_tmp)
		if input['Location'][irec] == 'Space':
			data_tmp['facilityType'] = 'spacecraft'
		else:
			data_tmp['facilityType'] = 'observatory'
			data_tmp['location'] = {}
			data_tmp['location']['continent'] = input['Location'][irec].strip()
		for otype in obsRangeTypes:
			if input[otype][irec].strip() != "\xc2\xa0":
				if data_tmp.has_key('measurementType'): 
					data_tmp['measurementType'].append(translateUCD(otype))
				else:
					data_tmp['measurementType'] = [translateUCD(otype)]
		if input['Solar'][irec].strip() != "\xc2\xa0":
			data_tmp['targetList'] = []
			data_tmp['targetList'].append('Sun')
		data[authority+":"+title] = data_tmp
	return data
			
def load_ppi_list():
	authority = 'pds-ppi'
	list_file = datadir + 'pds-ppi-spacecraft.json'
	with open(list_file) as data_file:    
		input = json.load(data_file)

	data = {}
	for record in input['response']['docs']:
		current_sc = authority+":"+record['SPACECRAFT_NAME'][0]
		
		if current_sc not in data.keys():
			data[current_sc] = {}
			data[current_sc]['alternateName'] = []
			data[current_sc]['facilityGroup'] = []
			data[current_sc]['instrumentList'] = []
			data[current_sc]['targetList'] = []
			data[current_sc]['facilityType'] = 'spacecraft'
		
		if 'SPACECRAFT_NAME' in record.keys():
			for altname_item in record['SPACECRAFT_NAME']:
				altname_tmp_list = []
				for item in data[current_sc]['alternateName']:
					altname_tmp_list.append(item['name'])
				if altname_item not in altname_tmp_list:
					altname_tmp = {}
					altname_tmp['name'] = altname_item
					altname_tmp['namingAuthority'] = authority
					data[current_sc]['alternateName'].append(altname_tmp)
		
		if 'MISSION_NAME' in record.keys():
			if record['MISSION_NAME'] not in data[current_sc]['facilityGroup']:
				data[current_sc]['facilityGroup'].append(record['MISSION_NAME'])
		
		if 'INSTRUMENT_NAME' in record.keys():
			for instrum_item in record['INSTRUMENT_NAME']:
				instrum_tmp_list = []
				for item in data[current_sc]['instrumentList']:
					instrum_tmp_list.append(item['name'])
				if instrum_item not in instrum_tmp_list:
					ii = record['INSTRUMENT_NAME'].index(instrum_item)
					instrum_tmp = {}
					instrum_tmp['name'] = instrum_item				
					instrum_tmp['id'] = record['INSTRUMENT_ID'][ii]	
					data[current_sc]['instrumentList'].append(instrum_tmp)

		if 'TARGET_NAME' in record.keys():
			for target_item in record['TARGET_NAME']:
				target_item = target_item.strip()
				if target_item not in data[current_sc]['targetList']:
					data[current_sc]['targetList'].append(target_item)
	
	return data

def load_ads_list():
	authority = 'ads'
	list_file = datadir + 'ADS_facilities.txt'
	with open(list_file,'r') as data_file:    
		input = data_file.readlines()
	
	data = {}
	for record in input:
		data_tmp = {}			
		data_tmp['alternateName'] = []
		title = record[0:16].strip()
		altname_tmp = {}
		altname_tmp['namingAuthority'] = authority
		altname_tmp['id'] = title
		altname_tmp['name'] = record[16:].strip()
		data_tmp['alternateName'].append(altname_tmp)
		if '/' in record[16:]:
			data_tmp['facilityGroup'] = record[16:].split('/')[0]
		if title[0:3] == 'Sa.':
			data_tmp['facilityType'] = 'spacecraft'
		else:
			data_tmp['facilityType'] = 'observatory'
		data[authority+":"+title] = data_tmp
	return data

def load_nssdc_list():
	authority = 'nssdc'
	list_file = datadir + 'NSSDC.xml'
	input = votable.parse(list_file).get_first_table().to_table(use_names_over_ids=True)
	nlines = len(input['name'])
	
	data = {}
	for irec in range(nlines):
		data_tmp = {}
		data_tmp['alternateName'] = []
		altname_tmp = {}

		title = input['NSSDC id'][irec]
		altname_tmp['name'] = input['name'][irec]
		altname_tmp['id'] = title
		altname_tmp['namingAuthority'] = authority
		data_tmp['alternateName'].append(altname_tmp)
		
		data_tmp['referenceURL'] = []
		refurl_tmp = {}
		refurl_tmp['url'] = input['URL'][irec]
		refurl_tmp['title'] = 'NSSDC catalog entry'
		data_tmp['referenceURL'].append(refurl_tmp)
		data_tmp['facilityType'] = 'spacecraft'
		if input['Launch date'][irec] != "": data_tmp['launchDate'] = input['Launch date'][irec]
		
		data[authority+":"+title] = data_tmp
	
	return data
	
def load_xephem_list():
	authority = 'xephem'
	list_file = datadir + 'xephem_sites.txt'
	with open(list_file,'r') as data_file:    
		input = data_file.readlines()
	
	data = {}
	for record in input:
		if record[0] != '#':
			record = ' '.join(record.split())
			data_tmp = {}
			data_tmp['alternateName'] = []
	
			items = record.split(';')
			if ',' in items[0]:
				rec_tmp = items[0].split(',')
				rec_name = rec_tmp[0].strip()
				rec_location = ', '.join(rec_tmp[1:]).strip()
			else:
				rec_name = items[0]
				rec_location = ''
			
			rec_lat_txt = items[1].strip().split(' ')
			rec_lat = float(rec_lat_txt[0])+float(rec_lat_txt[1])/60.+float(rec_lat_txt[2])/3600.
			if rec_lat_txt[3] == 'S':
				rec_lat = - rec_lat
			rec_lon_txt = items[2].strip().split(' ')
			rec_lon = float(rec_lon_txt[0])+float(rec_lon_txt[1])/60.+float(rec_lon_txt[2])/3600.
			if rec_lon_txt[3] == 'E':
				rec_lon = - rec_lon
			rec_alt_txt = items[3].strip()
			rec_alt = float(rec_alt_txt)	
			
			title = rec_name.strip()
			altname_tmp = {}
			altname_tmp['name'] = title
			altname_tmp['namingAuthority'] = authority
			data_tmp['alternateName'].append(altname_tmp)
			data_tmp['facilityType'] = 'observatory'
			data_tmp['location'] = {}
			if rec_location != '':
				data_tmp['location']['country'] = rec_location
			data_tmp['location']['coordinates'] = {}
			data_tmp['location']['coordinates']['lat'] = rec_lat
			data_tmp['location']['coordinates']['lon'] = rec_lon
			if rec_alt != -1.:
				data_tmp['location']['coordinates']['alt'] = rec_alt
			
			data[authority+":"+title] = data_tmp

	return data
			
def load_naif_list():
	authority = 'naif'
	list_file = datadir + 'NAIF.xml'
	input = votable.parse(list_file).get_first_table().to_table(use_names_over_ids=True)
	nlines = len(input['NAIF ID'])
	
	data = {}
	for irec in range(nlines):
		
		data_tmp = {}
		data_tmp['alternateName'] = []
		altname_tmp = {}

		title = input['NAIF ID'][irec].strip()
		altname_tmp['name'] = input['NAIF name'][irec].strip()
		altname_tmp['id'] = title 
		altname_tmp['namingAuthority'] = authority
		
		if title in data.keys():
			data[authority+":"+title]['alternateName'].append(altname_tmp)
		else:
			data_tmp['alternateName'].append(altname_tmp)
			data[authority+":"+title] = data_tmp

	return data

def load_mpc_list(): 
	authority = 'iau-mpc'
	list_file = datadir + 'IAU-MPC.txt'
	with open(list_file,'r') as data_file:    
		input = data_file.readlines()
	
	data = {}
	for record in input[1:]:
		data_tmp = {}			
		data_tmp['alternateName'] = []
		
		title = record[0:3].strip()
		obs_lon_txt = record[4:13].strip()
		obs_cos_txt = record[13:21].strip()
		obs_sin_txt = record[21:30].strip()
		if (obs_lon_txt == ''):
			data_tmp['facilityType'] = 'spacecraft'
		else:
			data_tmp['facilityType'] = 'observatory'
			obs_lon = float(record[4:13].strip())
			obs_cos = float(record[13:21].strip())
			obs_sin = float(record[21:30].strip())
			data_tmp['location'] = {}
			data_tmp['location']['coordinates'] = {}
			data_tmp['location']['coordinates']['lon'] = obs_lon
			data_tmp['location']['coordinates']['cos'] = obs_cos
			data_tmp['location']['coordinates']['sin'] = obs_sin
		name = record[30:].strip()
		altname_tmp = {}
		altname_tmp['namingAuthority'] = authority
		altname_tmp['id'] = title
		altname_tmp['name'] = name
		data_tmp['alternateName'].append(altname_tmp)
		data[authority+":"+title] = data_tmp

	return data
		
def load_iraf_list(): 
	authority = 'iraf'
	list_file = datadir + 'IRAF.txt'
	with open(list_file,'r') as data_file:    
		input = data_file.readlines()
	
	nlines = len(input)
	data = {}

	for irec in range(nlines):
		record = input[irec]
		if record[0:3] == 'obs':
			data_tmp = {}			
			data_tmp['alternateName'] = []		
			title = record.split(' = ')[1].strip().strip('"')
			obs_name = ''
			obs_lon = '0'
			obs_lat = '0'
			obs_alt = '0'
			obs_tz = '0'			
		
			for i in range(5):
				iirec = irec+i+1
				if input[iirec][1:4] == 'nam':
					obs_name = input[iirec].split(' = ')[1].strip().strip('"')
				if input[iirec][1:4] == 'lon':
					obs_lon = input[iirec].split(' = ')[1].strip()
				if input[iirec][1:4] == 'lat':
					obs_lat = input[iirec].split(' = ')[1].strip()
				if input[iirec][1:4] == 'alt':
					obs_alt = float(input[iirec].split(' = ')[1].strip())
				if input[iirec][1:4] == 'tim':
					obs_tz = float(input[iirec].split(' = ')[1].strip())
						
			altname_tmp = {}
			altname_tmp['namingAuthority'] = authority
			altname_tmp['id'] = title
			altname_tmp['name'] = obs_name
			data_tmp['alternateName'].append(altname_tmp)
			
			if ':' in obs_lon:
				obs_lon_tmp = obs_lon.split(':')
				obs_lon = float(obs_lon_tmp[0])+float(obs_lon_tmp[1])/60.
				if len(obs_lon_tmp) == 3:
					obs_lon = obs_lon + float(obs_lon_tmp[2])/3600.
			else:
				obs_lon = float(obs_lon)

			if ':' in obs_lat:
				obs_lat_tmp = obs_lat.split(':')
				obs_lat = float(obs_lat_tmp[0])+float(obs_lat_tmp[1])/60.
				if len(obs_lat_tmp) == 3:
					obs_lat = obs_lat + float(obs_lat_tmp[2])/3600.
			else:
				obs_lat = float(obs_lat)
			
			data_tmp['location'] = {}
			data_tmp['location']['coordinates'] = {}
			data_tmp['location']['coordinates']['lon'] = obs_lon
			data_tmp['location']['coordinates']['lat'] = obs_lat
			data_tmp['location']['coordinates']['alt'] = obs_alt
			data_tmp['location']['coordinates']['tz']  = obs_tz

			data_tmp['facilityType'] = 'observatory'
			
			data[authority+":"+title] = data_tmp
	
	return data
	
def load_dsn_list():
	authority = 'dsn'
	list_file = datadir + 'DSN.txt'
	with open(list_file,'r') as data_file:    
		input = data_file.readlines()
	
	data = {}
	for record in input:
		data_tmp = {}			
		data_tmp['alternateName'] = []
		rec_items = record.strip().split()
		id = rec_items[0]
		name = ' '.join(rec_items[1:]).strip("'")
		
		title = id
		altname_tmp = {}
		altname_tmp['namingAuthority'] = authority
		altname_tmp['id'] = title
		altname_tmp['name'] = name
		data_tmp['alternateName'].append(altname_tmp)

		data[authority+":"+title] = data_tmp
	
	return data