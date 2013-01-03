from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import xmlrpclib, httplib
from threading import Thread

MAX_NODES = 4
MEMORY_SIZE = 8

RPC_EOK = 0

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)

class Node:

	def request(self, offset):
		return self.memory[offset]
	def invalidate(self, offset):
		print self.id, ':Invalidate on offset', offset ,'received.'
		self.memory[offset] = None
		return RPC_EOK
	def send_invalidate(self, offset):
		for proxy in self.proxies:
			if isinstance(proxy, xmlrpclib.ServerProxy):
				proxy.invalidate(offset)
	def read(self, offset):
		print self.id, ':read request on offset', offset, "(", self.memory[offset], ")"
		self.print_memory()
		if self.memory[offset] == None:
			print 'I do not have a local copy, requesting'
			value = None
			for proxy in self.proxies:
				if isinstance(proxy, xmlrpclib.ServerProxy):
					print 'requesting from proxy', proxy
					if not value:
						try:
							value = proxy.request(offset)
							print 'got value', value
						except:
							print 'request to server failed, node probably disconnected'
							proxy = None
			assert not value == None
			self.memory[offset] = value
		else:
			print self.id, ":Reading local value"
		print self.id, ": Read value on offset=", offset, " ", self.memory[offset]
		self.print_memory()
	def write(self, offset, value):
		print self.id, ":Write on offset", offset, "value", value
		self.send_invalidate(offset)
		self.memory[offset] = value
	def register_new_node(self):
		print 'incoming node registration'
		new_id = self.id + 1
		self.proxies[new_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(new_id), allow_none=True)
		return new_id
	def print_memory(self):
		print self.id, ':memory dump: ', 
		for i in xrange(MEMORY_SIZE):
			print self.memory[i],
		print
	def kill_server(self):
		self.server.shutdown()
		self.print_memory()
	def server_start(self):
		# Create server
		self.server = SimpleXMLRPCServer(('localhost', 8000 + self.id), requestHandler=RequestHandler)
		self.server.register_introspection_functions()
		#Register calls
		self.server.register_instance(self)
		print 'server on port', 8000 + self.id, 'started'
		self.server.serve_forever()		
	def __init__(self, prev_id):
		self.id = 0
		self.memory = [None] * MEMORY_SIZE
		self.proxies = [None] * MAX_NODES
		self.server = None
		print 'starting node, previous:', prev_id
		if not prev_id == None:
			print 'not the first node, have to register with others'
			#Tell the previous node about this new node
			self.proxies[prev_id] = xmlrpclib.ServerProxy('http://localhost:800'+str(prev_id), allow_none=True)
			self.id = self.proxies[prev_id].register_new_node()
		else:
			#first node, init memory with something
			print 'First node, initializing memory'
			for i in xrange(MEMORY_SIZE):
				self.memory[i] = i
		#Start server
		print 'starting rpc server, address: http://localhost:800'+str(self.id)
		server_thread = Thread(target = self.server_start)
		server_thread.start()
		print "Node with id =", self.id, "started"
