import node as n, sys, time

node_count = int(sys.argv[1])
nodes = [None] * node_count
nodes[0] = n.Node(None, {'ip':'127.0.0.1', 'port':'8000'})
time.sleep(1)
nodes[1] = n.Node({'ip':'127.0.0.1', 'port':'8000'}, {'ip':'127.0.0.1', 'port':'8001'})
nodes[2] = n.Node({'ip':'127.0.0.1', 'port':'8000'}, {'ip':'127.0.0.1', 'port':'8002'})
time.sleep(1)
#print 'started first node'
#for i in xrange(1, int(sys.argv[1])):
#	time.sleep(1)
#	nodes[i] = n.Node(i - 1)
#	print 'started node nr.:', i

#print 'nodes started'

nodes[2].write(0, 5, 0)
nodes[1].read(0, 0)
nodes[0].write(0, 1, 0)
nodes[0].write(4, 4, 0)
nodes[1].write(3, 2, 0)
nodes[0].read(3, 0)
nodes[2].write(4, 111, 0)
nodes[2].write(3, 112, 0)
nodes[2].read(0, 0)


nodes[3] = n.Node({'ip':'127.0.0.1', 'port':'8000'}, {'ip':'127.0.0.1', 'port':'8003'})

nodes[2].disconnect()

time.sleep(1)

nodes[0].print_status()
nodes[1].print_status()
nodes[3].print_status()

raw_input()

nodes[0].disconnect()
nodes[1].disconnect()
nodes[3].disconnect()


print 'simulation finished'
