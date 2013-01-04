#!/usr/bin/python
import sys, node

if sys.argv[1] == 'first':
	prev_dict = None
	this_dict = {'ip':sys.argv[2], 'port':sys.argv[3]}
	console = int(sys.argv[4])
else:
	prev_dict = {'ip':sys.argv[1], 'port':sys.argv[2]}
	this_dict = {'ip':sys.argv[3], 'port':sys.argv[4]}
	console = int(sys.argv[5])

node.Node(prev_dict, this_dict, console)
