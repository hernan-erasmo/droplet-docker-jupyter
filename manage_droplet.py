# -*- coding: iso-8859-1 -*-

import sys
import json
import random
import argparse
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests

log_file_name = 'log.log'

logger = logging.getLogger('logger_create')
logger.setLevel(logging.DEBUG)

# https://docs.python.org/3/library/logging.handlers.html
rfh = RotatingFileHandler(log_file_name, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False)
rfh.setLevel(logging.DEBUG)

# https://docs.python.org/3/library/logging.html#logrecord-attributes
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
rfh.setFormatter(formatter)

logger.addHandler(rfh)


bearer = ''

with open('DOTOKEN.json') as authfile:
	auth = json.load(authfile)
	bearer = 'Bearer ' + auth['bearer']

auth_headers = {
	"Content-Type":"application/json",
	"Authorization":bearer
}

# Thanks to https://stackoverflow.com/a/23816211/1603080
def pretty_print_request(req):
    logger.info('{}\n{}\n{}\n\n{}{}'.format(
        '\n - - - START - - -',
        req.method + ' ' + req.url,
        '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        'request body: ' + (str(req.body) if str(req.body) else ''),
        '\n- - - END - - -',
    ))


def terminate_script(error=False):
	logger.info('Terminating script\n\n\n\n')
	if error:
		sys.exit(1)
	else:
		sys.exit(0)


def get_droplet_ip(droplet_id):
	url_get_ip = 'https://api.digitalocean.com/v2/droplets/' + droplet_id
	req =  requests.Request('GET', url_get_ip, headers=auth_headers)
	prepared = req.prepare()

	logger.info('Getting droplet info... (We are sending this request)')
	pretty_print_request(prepared)
	s = requests.Session()
	resp = s.send(prepared)
	
	info = json.loads(resp.text)
	ips = ''

	try:
		for ip in info['droplet']['networks']['v4']:
			ips += ip['ip_address'] + ', '
	except KeyError as err:
		logger.error('There was an error while trying to get droplet info. DigitalOcean says: {0}'.format(resp.content))
		terminate_script(error=True)

	try:
		ips += '(IPv6 = '
		for ip in info['droplet']['networks']['v6']:
			ips += ip['ip_address'] + ', '

		ips += ')'
	except KeyError as err:
		logger.debug('This droplet doesn\'t seem to have IPv6')

	return ips


def load_cloud_config(cloud_config_path):
	try:
		with open(cloud_config_path, 'r') as cloud_config:
			return cloud_config.read()
	except Error as err:
			logger.error('There was an error while reading cloud-config: {0}'.format(str(err)))
			terminate_script(error=True)


def create_droplet(cloud_config_file=None):
	endpoint_create = 'https://api.digitalocean.com/v2/droplets'
	
	droplet_data = {
		'name':'disposabledroplet-' + datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'),
		'region':random.choice(['nyc1', 'nyc3', 'sfo2']),
		'size':'s-1vcpu-1gb',
		'image':'ubuntu-18-04-x64',
		'ssh_keys':None,
		'backups':'false',
		'ipv6':'true',
		'user_data':None,
		'private_networking':None,
		'volumes':None,
		'tags':['disposable-droplet']
	}

	if cloud_config_file:
		droplet_data['user_data'] = load_cloud_config(cloud_config_file)

	req = requests.Request('POST', endpoint_create, headers=auth_headers, json=droplet_data)
	prepared = req.prepare()
	
	logger.info('Sending create POST request to DigitalOcenan\'s API')
	pretty_print_request(prepared)
	s = requests.Session()
	
	return s.send(prepared)


def destroy_droplet(droplet_id):
	url_delete = 'https://api.digitalocean.com/v2/droplets/' + droplet_id
	req = requests.Request('DELETE', url_delete, headers=auth_headers)
	prepared = req.prepare()
	
	s = requests.Session()
	
	return s.send(prepared)


if __name__ == '__main__':
	logger.info('Starting up...')
	
	parser = argparse.ArgumentParser()
	parser.add_argument('-f', '--cloud-config', help='Path to cloud-config .yaml file', dest='cloud_config_file')
	parser.add_argument('-i', '--check-ip', help='Check if droplet with $id has an available IP address', dest='droplet_id_ip')
	parser.add_argument('-d', '--destroy-id', help='Destroy droplet with $id', dest='droplet_id_destroy')
	args = parser.parse_args()

	logger.debug('Script called with these parameters: {0}'.format(args))
	ccf = None

	if args.cloud_config_file:
		ccf = args.cloud_config_file

	if args.droplet_id_ip:
		print(get_droplet_ip(args.droplet_id_ip))
		terminate_script()

	if args.droplet_id_destroy:
		delete_req = destroy_droplet(args.droplet_id_destroy)

		try:
			if delete_req.status_code == 204:
				logger.info('Droplet with ID {0} has been sucessfully deleted.'.format(args.droplet_id_destroy))
				terminate_script()
			else:
				logger.error('There was an error while trying to delete droplet with ID {0}. DigitalOcean says: {1}'.format(args.droplet_id_destroy, delete_req.content))
				terminate_script(error=True)
		except KeyError as k:
			logger.error('Couldn\'t delete droplet. DigitalOcean says: {0}\n\n\n\n'.format(delete_req.content))
			terminate_script(error=True)

	req_create = create_droplet(cloud_config_file=ccf)

	try:
		if req_create.status_code == 202:
			droplet_data = json.loads(req_create.text)
			droplet_id = droplet_data['droplet']['id']
			logger.info('Droplet with ID {0} has been successfully created.'.format(droplet_id))
			print('droplet_id {0}'.format(droplet_id))
			logger.info('{0} requests available.'.format(req_create.headers['ratelimit-remaining']))
			terminate_script()
		else:
			logger.error('Couldn\'t create droplet. DigitalOcean says: {0}\n\n\n\n'.format(req_create.content))
			terminate_script(error=True)
	except KeyError as k:
		logger.error('Couldn\'t create droplet (KeyError). DigitalOcean says: {0}\n\n\n\n'.format(req_create.content))
		terminate_script(error=True)
