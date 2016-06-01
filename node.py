import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import xmlrpclib, httplib, time, sys
from threading import Thread
from select import select


_MEMORY_SIZE = 6


#from http://stackoverflow.com/questions/268629/how-to-stop-basehttpserver-serve-forever-in-a-basehttprequesthandler-subclass
class StoppableRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):

    stopped = False
    allow_reuse_address = True


    def __init__(self, *args, **kw):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, *args, **kw)
        self.register_function(lambda: 'PONG', 'ping')


    def serve_forever(self):
        while not self.stopped:
            self.handle_request()


    def force_stop(self):
        self.stopped = True
        self.create_dummy_request()
        self.server_close()


    def create_dummy_request(self):
        server = xmlrpclib.Server('http://%s:%s' % self.server_address)
        server.ping()


def unique(array):
	tmp = {}
	for vector in array:
		for item in vector:
			tmp[item] = 0
	return list(tmp)


def ret_tuple(my_id):
	return (my_id['ip'], my_id['port'])


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)


class Node:


	def __del__(self):
		self.server.force_stop()
		sys.exit(0)


	def crash(self):
		self.server.force_stop()
		sys.exit(-1)


	def echo_about_read(self, offset, who):
		self.have_offset[offset][ret_tuple(who)] = 1


	def request(self, offset, who):
		print self.id, ': Offset', offset, 'requested by ID', who, 'returning value', self.memory[offset]
		self.have_offset[offset][ret_tuple(who)] = 1
		#tell the other nodes about this new node having the value
		for proxy_key in self.proxies:
			proxy = self.proxies[proxy_key]
			if proxy_key != ret_tuple(who):
				proxy.echo_about_read(offset, who)
		return self.memory[offset]


	def invalidate(self, offset, inval_id):
		print self.id, ':Invalidate on offset', offset ,'received from', inval_id
		if self.memory[offset] == None:
			print self.id, ':Info about offset', offset ,'received from', inval_id
			#just an info about invalidation, means that only inval_id now has a valid value
			self.have_offset[offset] = {}
			self.have_offset[offset][ret_tuple(inval_id)] = 1
			assert self.memory[offset] == None
		else :
			print self.id, ':Invalidate on offset', offset ,'received.'
			self.have_offset[offset] = {}
			self.have_offset[offset][ret_tuple(inval_id)] = 1
			self.memory[offset] = None


	def send_invalidates(self, offset):
		#get ids of nodes that have this value
		print self.id, ':Sending invalidates for offset', offset
		print self.have_offset
		
		#for those, who did not need to be invalidated, we have to imform those, that this node now has this value
		for proxy in self.proxies:
			#invalidate all 
				print self.id, ':Invalidating offset', offset, 'on id', proxy
				try:
					self.proxies[proxy].invalidate(offset, self.id)
				except:
					print 'Sending invalidate failed'
					proxy = None


	def read(self, offset, delay):
		time.sleep(delay)
		print self.id, ':read request on offset', offset, "(", self.memory[offset], ")"
		if self.memory[offset] == None:
			print 'I do not have a local copy, requesting'
			value = None
			for proxy_id in list(self.have_offset[offset]):
				proxy = self.proxies[proxy_id]
				assert isinstance(proxy, xmlrpclib.ServerProxy)
				print 'requesting from proxy', proxy
				if not value:
					try:
						value = proxy.request(offset, self.id)
						print 'got value', value
					except:
						print 'request to server failed, node probably disconnected'
						proxy = None
			if value != None:
				self.have_offset[offset][ret_tuple(self.id)] = 1
			self.memory[offset] = value
		return "READ offset="+str(offset)+", value="+str(self.memory[offset])


	def write(self, offset, value, delay):
		time.sleep(delay)
		print self.id, ":Write on offset", offset, "value", value
		self.send_invalidates(offset)
		self.have_offset[offset] = {}
		self.have_offset[offset][ret_tuple(self.id)] = 1
		self.memory[offset] = value
		return 'WRITE offset='+str(offset)+' value='+str(value)+' written successfuly.'


	def echo_about_new_node(self, new_id):
		print 'incoming new node', new_id
		assert new_id != self.id
		self.proxies[ret_tuple(new_id)] = xmlrpclib.ServerProxy('http://'+new_id['ip']+':'+new_id['port'], allow_none=True)


	def register_new_node(self, new_id):
		print self.id, 'Incoming node registration:', new_id
		proxy_ids = []
		for key in self.proxies.iterkeys():
				proxy_ids.append(key)
				if key != ret_tuple(self.id):
					try:
						print 'sending echo about node', new_id, 'to proxy', key, self.proxies[key]
						self.proxies[key].echo_about_new_node(new_id)
					except:
						print 'Sending new node echo failed on', self.proxies[key], key
						self.proxies[key] = None
		
		self.proxies[(new_id['ip'], new_id['port'])] = xmlrpclib.ServerProxy('http://'+new_id['ip']+':'+new_id['port'], allow_none=True)
		print 'returning proxy_ids', proxy_ids, self.have_offset
		return_offsets = []
		for item in self.have_offset:
			return_offsets.append(list(item))
		return return_offsets, proxy_ids


	def print_memory(self):
		print self.id, ':memory dump: ', 
		for i in xrange(_MEMORY_SIZE):
			print self.memory[i],
		print


	def disconnection_annoucement(self, disc_id):
		print self.id, ':Got disconnection annoucement from id', disc_id
		for offset_info in self.have_offset:
			if offset_info.has_key(ret_tuple(disc_id)):
				offset_info.pop(ret_tuple(disc_id))

		self.proxies[ret_tuple(disc_id)] = None


	def print_status(self):
		print self.id, ':Status:'
		print 'server: ', self.server
		print 'proxies: ', self.proxies
		print 'info about others', self.have_offset
		print 'memory: ', self.memory


	def disconnect(self):
		print 'sending goodbyes'
		for proxy in self.proxies:
			try:
				self.proxies[proxy].disconnection_annoucement(self.id)
			except:
				pass
		self.__del__()


	def server_start(self):
		# Create server
		self.server = StoppableRPCServer((self.id['ip'], int(self.id['port'])), requestHandler=RequestHandler, allow_none=True)
		self.server.register_introspection_functions()
		#Register calls
		self.server.register_instance(self)
		self.server.serve_forever()


	def console_start(self):
		self.console_running = True
		run = True
		while run:
			user_input = raw_input("promt:")
			split = user_input.split()
			if split == []:
				continue
			if user_input == 'quit':
				run = False
				self.disconnect()
			elif split[0] == 'w':
				print self.write(int(split[1]), int(split[2]), 0)
			elif split[0] == 'r':
				print self.read(int(split[1]), 0)
			elif user_input == 'm':
				print self.memory
		self.console_thread.join()


	def dump_mem(self):
		return 'MEMORY: '+str(self.memory)


	def dump_status(self):
		return 'STATUS: PROXIES:'+str(self.proxies)+' INFO:'+str(self.have_offset)


	def r(self, offset):
		return self.read(offset, 0)


	def w(self, offset, value):
		return self.write(offset, value, 0)


	def __init__(self, prev_id, my_id, console):
		self.id = my_id
		self.memory = [None] * _MEMORY_SIZE
		self.proxies = {}
		self.have_offset = [dict() for x in xrange(_MEMORY_SIZE)]
		print 'starting node, previous:', prev_id
		if not prev_id == None:
			print 'not the first node, have to register with others, previous:', prev_id
			#Tell the previous node about this new node
			initiator_proxy = xmlrpclib.ServerProxy('http://'+prev_id['ip']+':'+prev_id['port'], allow_none=True)
			self.proxies[(prev_id['ip'], prev_id['port'])] = initiator_proxy
			offset_ids, proxy_ids = initiator_proxy.register_new_node(self.id)
			print 'new node got these offsets', offset_ids
			print 'new node got these proxies', proxy_ids
			for i in xrange(_MEMORY_SIZE):
				if offset_ids[i] != []:
					for dict_ids in offset_ids[i]:
						self.have_offset[i][(dict_ids[0], dict_ids[1])] = 1
			for proxy_id in proxy_ids:
				self.proxies[tuple(proxy_id)] = xmlrpclib.ServerProxy('http://'+proxy_id[0]+':'+proxy_id[1], allow_none=True)
		#Start server
		print 'starting rpc server, address:', self.id
		self.server_thread = Thread(target = self.server_start)
		self.server_thread.start()
		if console:
			self.console_thread = self.server_thread = Thread(target = self.console_start)
			self.console_thread.start()
		print "Node with id =", self.id, "started"
		print self.id, "offsets:", self.have_offset
		print self.id, ':Proxies:', self.proxies
