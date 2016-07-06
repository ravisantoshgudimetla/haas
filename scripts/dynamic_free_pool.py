#! /bin/python
import urlparse
import requests
from sets import Set
import json
import time
import sys
from requests.auth import HTTPBasicAuth
import ConfigParser, os

				
def release_nodes(haas_url, haas_username, haas_password, statusfile, non_persistent_list,threshold_time):  
	"""Release nodes : Takes node list as arguments and puts them back to free pool 	        after given time
	"""
	free_node_list = get_free_node_list(haas_url, haas_username, haas_password)
	#Only these nodes should be updated in the file(either for project or for time)
	nodes_to_update_infile = list(Set(non_persistent_list)-Set(free_node_list))
	for node in nodes_to_update_infile:
		#get the information from status file for node.
		node_info_from_file = get_project_and_time_for_node(statusfile, node)
		project_in_file = node_info_from_file[0]
		old_time = node_info_from_file[1]
		#get the information from HaaS for node
		node_current_info =  get_node_current_info(haas_url, haas_username, haas_password, node)
		project_in_haas = node_current_info[0]
		networks = node_current_info[1]
		nic = node_current_info[2]
		#Increase the time by one unit
		new_time = int(node_info_from_file[1])+1
		#See if the node is in the same project and if it is outside 
		#free pool for time less than threshold value then update only 
		#time in status file
	        if compare_projects(project_in_file, project_in_haas) \
					and can_live(new_time, threshold_time):
			update_time_for_node(statusfile, node, old_time, new_time)
		#See if the node is in the same project and if it is outside
		#free pool for time greater than threshold value then release
		#the node back to free pool
		elif  compare_projects(project_in_file, project_in_haas)\
					and not can_live(new_time, threshold_time):
		  	#Detaching nodes from networks
			if networks!=[]:
				detach_networks_from_node(haas_url, haas_username, haas_password, node,\
								networks, nic)		
			#Releasing node from project.
			release_from_project(haas_url, haas_username, haas_password, statusfile,\
						node, project_in_haas) 
		#See if the node is not in free pool and check if the projects
		#are not matching then we need to update project in status file
		elif not compare_projects(project_in_file, project_in_haas) \
			and project_in_haas != None:
			update_project_in_status_file(statusfile, node, project_in_haas,\
							project_in_file)
				
		#else:
			#Need to write a function which actually brings down 
			#the nodes if they are in free pool.
			#Power save mode on :)	

def compare_projects(project_in_file,project_in_haas):
	"""Boolean Function to check if the projects are same.""" 
	if project_in_file == project_in_haas:
		return True
	else:
		return False		  

def can_live(time, threshold_time):
	"""Boolean Function to check if node can live in the same project."""
	if time < threshold_time:
		return True
	else:
		return False

def get_project_and_time_for_node(statusfile, node):
	"""Reads current information from file for every node."""
	with open(statusfile,'r') as status_file:
		for line in status_file:
			if node in line:
				node_status = line.split()
				node_project = node_status[1]
				node_duration = node_status[2]
	return (node_project, node_duration)	

def update_time_for_node(statusfile, node, old_time, new_time):
	"""Updates the time for a node in file."""
	lines = []
	with open(statusfile,'r') as status_file:
                for line in status_file:
                        if node in line:
				#line = line.replace(old_time,str(new_time))
				words = line.split()
				words[2] = str(new_time)
				line = ' '.join(words)+"\n"
			lines.append(line)	
	with open(statusfile,'w') as status_file:		
		for line in lines:
			status_file.write(line)


def update_project_in_status_file(statusfile, node, new_project, old_project):
	"""Project will be changed in file to match the project in HaaS."""
	lines = []
        with open(statusfile,'r') as status_file:
                for line in status_file:
                        if node in line:
                                #line = line.replace(old_project, new_project)
				words = line.split()
				words[1] = new_project
				line = ' '.join(words) + "\n"
                        lines.append(line)
        with open(statusfile,'w') as status_file:
                for line in lines:
                        status_file.write(line)

def get_node_current_info(haas_url, haas_username, haas_password, node):
	"""
	Checks the current information for the node and returns a tuple consisting of (<project_name>,List of <{"network": network-name}>, NIC name)
	"""
	url = haas_url + "node/" + node
	resp = requests.get(url, auth = (haas_username,haas_password))
	node_info = resp.json()
	node_project = node_info['project']
	data = node_info['nics'][0]['networks']
	node_nic = node_info['nics'][0]['label']
	networks = [{"network":v} for k,v in data.items() if k.startswith('vlan')]
	return (node_project, networks, node_nic)	

def detach_networks_from_node(haas_url, haas_username, haas_password, node, networks, node_nic):
	"""
	Takes a node ,list of {network, "network-name"}- networks attached to it, nic on which network is attached and detaches all the networks
	"""
	url = haas_url + "node/" + node + "/nic/" + node_nic + "/detach_network"
	for network in networks:
		res = requests.post(url, json.dumps(network), auth = (haas_username,haas_password))
		time.sleep(5)
	return res	


def release_from_project(haas_url, haas_username, haas_password, statusfile, node, project):	
        """
	Updates the file with project name as free and 
	releases it back to free pool
	"""
	lines = []
        with open(statusfile,'r') as status_file:
                for line in status_file:
                        if node in line:
                                line = node +" "+ "free_pool "+str(0) +"\n"
                        lines.append(line)
	with open(statusfile,'w') as status_file:
                for line in lines:
                        status_file.write(line)
	time.sleep(5)
	response = release_node_from_project(haas_url, haas_username, haas_password,\
						node, project)
	return response	
		
def release_node_from_project(haas_url, haas_username, haas_password, node, project):
	"""Release a node from a project."""
	haas_url = haas_url + 'project/' + project + '/detach_node'
	body = {
		"node" : node
	       }
	r = requests.post(haas_url, data = json.dumps(body), auth = (haas_username, haas_password))
	return r
	
def get_free_node_list(haas_url, haas_user_name, haas_password):
	"""Checks for free pool in the list and returns the list."""
	free_node_list =  urlparse.urljoin(haas_url,'free_nodes')
	free_node_list = requests.get(free_node_list, auth = (haas_user_name, haas_password))
	return free_node_list


if __name__ == "__main__":
	"""Main function for calling rest of functions"""
	try:
		config = ConfigParser.SafeConfigParser()
		#Leaving it for as of now and has to be replaced by another 
		#location which HIL has access to.
		config.read("/home/ravi/leasing.cfg")
		node_list = [x.strip() for x in config.get('haas','node_list').split(',')]
		threshold = int(config.get('haas','threshold'))
		haas_url = config.get('haas', 'url')
		haas_username = config.get('haas', 'user_name')
		haas_password = config.get('haas', 'password')
		statusfile = config.get('haas', 'status_file')
		release_nodes(haas_url, haas_username, haas_password, statusfile, node_list, threshold)
	except ConfigParser.NoOptionError, err:
		print err
