from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import xmlrpclib, httplib, time
from threading import Thread

MAX_NODES = 4
MEMORY_SIZE = 6

def unique(array):
	tmp = {}
	for vector in array:
		for item in vector:
			tmp[item] = 0
	return list(tmp)

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)

class Node:
	def __del__(self):
		self.print_status()
		self.kill_server()
	def crash(self):
		self.kill_server()
		sys.exit(-1)
	def echo_about_read(self, offset, who):
		self.have_offset[offset][who] = 1
	def request(self, offset, who):
#		print self.id, ': Offset', offset, 'requested by ID', who, 'returning value', self.memory[offset]
		self.have_offset[offset][who] = 1
		#tell the other nodes about this new node having the value
		for i in xrange(MAX_NODES):
			proxy = self.proxies[i]
			if isinstance(proxy, xmlrpclib.ServerProxy) and i != who:
				proxy.echo_about_read(offset, who)
		return self.memory[offset]
	def invalidate(self, offset, inval_id):
		print self.id, ':Invalidate on offset', offset ,'received from', inval_id
		if self.memory[offset] == None:
#			print self.id, ':Info about offset', offset ,'received from', inval_id
			#just an info about invalidation, means that only inval_id now has a valid value
			self.have_offset[offset] = {}
			self.have_offset[offset][inval_id] = 1
		else :
#			print self.id, ':Invalidate on offset', offset ,'received.'
			self.have_offset[offset] = {}
			self.have_offset[offset][inval_id] = 1
			self.memory[offset] = None
	def send_invalidates(self, offset):
		#get ids of nodes that have this value
		print self.id, ':Sending invalidates for offset', offset
		print self.have_offset
		
		#for those, who did not need to be invalidated, we have to imform those, that this node now has this value
		for proxy in self.proxies:
			#invalidate all 
			if isinstance(proxy, xmlrpclib.ServerProxy):
#				print self.id, ':Invalidating offset', offset, 'on id', proxy
				try:
					proxy.invalidate(offset, self.id)
				except:
					print 'Sending invalidate failed'
					proxy = None		
	def read(self, offset, delay):
		time.sleep(delay)
#		print self.id, ':read request on offset', offset, "(", self.memory[offset], ")"
		if self.memory[offset] == None:
#			print 'I do not have a local copy, requesting'
			value = None
			for proxy_id in list(self.have_offset[offset]):
				proxy = self.proxies[proxy_id]
				if isinstance(proxy, xmlrpclib.ServerProxy):
#					print 'requesting from proxy', proxy
					if not value:
						try:
							value = proxy.request(offset, self.id)
							print 'got value', value
						except:
							print 'request to server failed, node probably disconnected'
							proxy = None
			if value != None:
				self.have_offset[offset][self.id] = 1
			self.memory[offset] = value
#		else:
#			print self.id, ":Reading local value"
		print self.id, ": READ offset=", offset, " ", self.memory[offset]
	def write(self, offset, value, delay):
		time.sleep(delay)
		print self.id, ":Write on offset", offset, "value", value	
		self.send_invalidates(offset)
		self.have_offset[offset] = {}
		self.have_offset[offset][self.id] = 1
		self.memory[offset] = value
	def echo_about_new_node(self, new_id):
		print 'incoming new node', new_id
		assert new_id != self.id
		self.proxies[new_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(new_id), allow_none=True)
	def register_new_node(self):
		print self.id, '"Incoming node registration'
		new_id = self.id + 1
		self.proxies[new_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(new_id), allow_none=True)
		proxy_ids = []
		for i in xrange(MAX_NODES):
			if (i == self.id) or (isinstance(self.proxies[i], xmlrpclib.ServerProxy) and i != new_id):
				proxy_ids.append(i)
				if i != self.id:
					self.proxies[i].echo_about_new_node(new_id)
		print 'returning proxy_ids', proxy_ids, new_id, self.have_offset
		#dictionaries have to be changed for serialization
		tmp_offsets = [dict() for x in xrange(MEMORY_SIZE)]
		for offset in xrange(MEMORY_SIZE):
			for key in self.have_offset[offset].iterkeys():
				tmp_offsets[offset][str(key)] = self.have_offset[offset][key]
		return new_id, tmp_offsets, proxy_ids
	def print_memory(self):
		print self.id, ':memory dump: ', 
		for i in xrange(MEMORY_SIZE):
			print self.memory[i],
		print
	def ping(self):
		return 'PONG'
	def kill_server(self):
		self.server.shutdown()
		self.server_thread.join()
	def disconnection_annoucement(self, disc_id):
		print self.id, ':Got disconnection annoucement from id', disc_id
		for offset_info in self.have_offset:
			if offset_info.has_key(disc_id):
				offset_info.pop(disc_id)

		self.proxies[disc_id] = None
	def print_status(self):
		print self.id, ':Status:'
#		print 'server: ', self.server
		print 'proxies: ', self.proxies
		print 'info about others', self.have_offset
		print 'memory: ', self.memory
	def disconnect(self):
		for proxy in self.proxies:
			if isinstance(proxy, xmlrpclib.ServerProxy):
				try:
					proxy.disconnection_annoucement(self.id)
				except:
					pass
		self.__del__()
	def server_start(self):
		# Create server
		self.server = SimpleXMLRPCServer(('localhost', 8000 + self.id), requestHandler=RequestHandler, allow_none=True)
		self.server.register_introspection_functions()
		#Register calls
		self.server.register_instance(self)
#		print 'server on port', 8000 + self.id, 'started'
		self.server.serve_forever()		
	def __init__(self, prev_id):
		self.id = 0
		self.memory = [None] * MEMORY_SIZE
		self.proxies = [None] * MAX_NODES
		self.have_offset = [dict() for x in xrange(MEMORY_SIZE)]
#		print 'starting node, previous:', prev_id
		if not prev_id == None:
			print 'not the first node, have to register with others'
			#Tell the previous node about this new node
			self.proxies[prev_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(prev_id), allow_none=True)
			self.id, tmp_offsets, proxy_ids = self.proxies[prev_id].register_new_node()
#			print 'new node got these offsets', tmp_offsets
#			print 'new node got these proxies', proxy_ids
			for proxy_id in proxy_ids:
				self.proxies[proxy_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(proxy_id), allow_none=True)
			for offset in xrange(MEMORY_SIZE):
				for key in tmp_offsets[offset].iterkeys():
					self.have_offset[offset][int(key)] = tmp_offsets[offset][key]
		#Start server
#		print 'starting rpc server, address: http://localhost:800'+str(self.id)
		self.server_thread = Thread(target = self.server_start)
		self.server_thread.start()
		print "Node with id =", self.id, "started"
#		print self.id, "offsets:", self.have_offset
#		print self.id, ':Proxies:', self.proxies
