import http.server, socketserver, os
os.chdir(r"D:\dsh workspace\dsh test project")
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 8912), H) as httpd:
    print("serving on http://127.0.0.1:8912")
    httpd.serve_forever()
