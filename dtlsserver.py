import socket
import select

from pgdtls.ffi import lib, ffi
from pgdtls import PSKServerCredentials, Priority
from pgdtls.dtls import DTLSSocket
from pgdtls.reactor import Reactor
from pgdtls.util import log
from pgdtls.sockutil import MMsgHdr

class Callback(object):
	def handshake(self, conn):
		log("handshake: %r" % (conn,))

	def connected(self, conn):
		log("connected: %r" % (conn,))

	def recvfrom(self, data, data_len, seq, conn):
		#log("recvfrom: %r %r %r %r" % (data, seq, sock, peer))
		conn.sock.sendto(data, data_len, conn.name)

	def gone(self, conn):
		log("gone: %r" % (conn,))

s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
s.bind(("::", 11111))

def credFunc(session, userName, datum):
	userName = ffi.string(userName)
	datum.data = lib.gnutls_malloc(8)
	ffi.buffer(datum.data, 8)[0:8] = b"password"
	datum.size = 8
	return 0

reactor = Reactor()

credentials = PSKServerCredentials()
credentials.setFunction(credFunc)

priority = Priority(b"SECURE192:+PSK")

def sendmsg(msg, fd=s.fileno()):
	res = lib.sendmsg(fd, msg, 0)
	#print("SENDMSG(%d, %r, 0) = %d" % (fd, msg, res))
	return res

def recvmmsg(events, s, dsock, fd=s.fileno(), mmsg=MMsgHdr()):
	n = mmsg.recv(fd)
	if n > 0:
		for i in range(n):
			dsock.recvmsg(mmsg.iov[i].iov_base, mmsg.msgvec[i].msg_len, mmsg.name + i, mmsg.msgvec[i].msg_hdr.msg_namelen)
		mmsg.reinit(n)
	elif n < 0:
		log("RECVMMSG(%d, %r, 0) = %d" % (fd, n))
	else:
		raise ValueError("EOF")

dsock = DTLSSocket(Callback(), sendmsg, reactor, priority, None, credentials)

reactor.register(s.fileno(), select.EPOLLIN, recvmmsg, s, dsock)
reactor.run()
