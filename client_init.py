import xmlrpclib, httplib, time

def create_proxy(ip, port):
	return xmlrpclib.ServerProxy('http://'+ip+':'+port, allow_none=True)

