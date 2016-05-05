# Leasing Scripts:


Dynamic Free Pool:

This script is used for reclaiming the non persistent nodes from projects in HaaS.

Limitations:

As of now, scripts location etc. are placed in my home folder. I want to change them to a service account(user which is not on my name). Also, this is more or less like a ticketing system which runs from a cron and executes the current script. So, there are chances of drifting if node gets just registered before  

Usage:

Update the leasing.cfg file with node_list and threshold value parameters:

node_list : List of non-persistent nodes which have to revoked seperated by ','.

url: The HaaS endpoint that we should be using.

threshold : No of hours we want the node to be part of project before being revoked.

username : The HaaS admin username

password : The HaaS admin password

status_file : The file to which script writes to and reads from. The general format of the file is.

<node_name> <project or free_pool> <duration_outside_free_pool>

With the above parameters configuration is complete.Now update the cron file with entry like:

#######################################################
@hourly /usr/bin/python /home/ravi/dynamic_free_pool.py
#######################################################

Again, this is on my name, which should be changed with service account.


