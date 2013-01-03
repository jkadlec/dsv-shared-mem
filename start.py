import node as n, sys, time

node_count = int(sys.argv[1])
nodes = [None] * node_count
nodes[0] = n.Node(None)
time.sleep(1)
nodes[1] = n.Node(0)
#print 'started first node'
#for i in xrange(1, int(sys.argv[1])):
#	time.sleep(1)
#	nodes[i] = n.Node(i - 1)
#	print 'started node nr.:', i

print 'nodes started'

nodes[0].read(0)
nodes[1].read(0)
nodes[1].write(5, 1234)

raw_input()

nodes[0].kill_server()
nodes[1].kill_server()

print 'simulation finished'
