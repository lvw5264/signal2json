
import sys, BaseHTTPServer, SimpleHTTPServer

class ExtHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """content-type extension for tunnelx configuration files"""
    def guess_type(self, path):
        mimetype = SimpleHTTPServer.SimpleHTTPRequestHandler.guess_type(self, path)
        if mimetype == 'application/octet-stream':
            if path.endswith('tunnelx'):
                mimetype = 'web+tunnelx/conf'

        return mimetype

HandlerClass = ExtHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 8000

server_address = ('127.0.0.1', port)

HandlerClass.protocol_version = Protocol
httpd = ServerClass(server_address, HandlerClass)

socketname = httpd.socket.getsockname()

print "Serving HTTP on", socketname[0], "port", socketname[1], "..."

httpd.serve_forever()