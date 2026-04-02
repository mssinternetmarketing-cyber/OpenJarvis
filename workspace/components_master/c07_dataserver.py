# ═══ c07_dataserver — HTTP Data Server + QCBridge ═══
# WHAT: HTTP server on port 9999 receives quantum ring snapshots
#       QCBridge manages bidirectional Q↔C communication
# WHY:  Slack bridge reads live data via POST to localhost:9999
#       QCBridge feeds classical gradients back into quantum params
#       Cell Block 4 source

class DataHandler(BaseHTTPRequestHandler):
    # WHAT: Receives quantum snapshot from qcai_3d.py, stores for bridge
    # WHY:  Bridge polls this to get live cv/negfrac/pcms/node_outputs
    quantum_data = {}

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            DataHandler.quantum_data = json.loads(body)
        except Exception:
            pass
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        data = json.dumps(DataHandler.quantum_data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass   # suppress HTTP logs


def start_data_server(port=DATA_PORT):
    # WHAT: Start HTTP server in daemon thread
    # WHY:  Non-blocking — viz continues while server handles bridge requests
    try:
        server = HTTPServer(("127.0.0.1", port), DataHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    except OSError:
        return None   # port already in use — bridge may already be running


def post_data_periodically(system, port=DATA_PORT, interval=2.0):
    # WHAT: Send quantum snapshot to bridge every interval seconds
    # WHY:  Keeps Slack bridge's live data current without blocking animation
    import urllib.request

    def _loop():
        while True:
            try:
                snapshot = system.get_snapshot()
                data     = json.dumps(snapshot).encode()
                req      = urllib.request.Request(
                    f"http://127.0.0.1:{port}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req, timeout=1)
            except Exception:
                pass
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
