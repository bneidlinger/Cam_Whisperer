"""
Simple ONVIF Mock Server for Testing

This creates a basic HTTP server that responds to ONVIF queries
for testing the CamOpt AI ONVIF integration without real hardware.

Usage:
    python onvif_mock_server.py

Then test with:
    - Discovery: Won't work (needs WS-Discovery broadcast)
    - Direct connection: http://localhost:8080
    - Username: admin
    - Password: admin
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime


class ONVIFMockHandler(BaseHTTPRequestHandler):
    """Mock ONVIF camera HTTP handler"""

    def log_message(self, format, *args):
        """Override to add timestamps to logs"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {format % args}")

    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "status": "online",
            "message": "ONVIF Mock Camera",
            "manufacturer": "CamOpt AI",
            "model": "Mock-Camera-1080p",
            "firmware": "1.0.0",
            "endpoints": {
                "device_service": "/onvif/device_service",
                "media_service": "/onvif/media_service",
                "imaging_service": "/onvif/imaging_service"
            }
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        """Handle POST requests (ONVIF SOAP)"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        # Log SOAP request
        print(f"\nReceived SOAP request:\n{body[:200]}...")

        # Send mock SOAP response
        self.send_response(200)
        self.send_header('Content-type', 'application/soap+xml')
        self.end_headers()

        # Generic SOAP response
        soap_response = '''<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope">
    <SOAP-ENV:Body>
        <tds:GetDeviceInformationResponse>
            <tds:Manufacturer>CamOpt AI</tds:Manufacturer>
            <tds:Model>Mock-Camera-1080p</tds:Model>
            <tds:FirmwareVersion>1.0.0</tds:FirmwareVersion>
            <tds:SerialNumber>MOCK-12345</tds:SerialNumber>
            <tds:HardwareId>MOCK-HW-001</tds:HardwareId>
        </tds:GetDeviceInformationResponse>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''

        self.wfile.write(soap_response.encode())


def run_server(port=8080):
    """Start the mock ONVIF server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ONVIFMockHandler)

    print("=" * 60)
    print("ONVIF MOCK SERVER")
    print("=" * 60)
    print(f"\nServer running on: http://localhost:{port}")
    print("\nCamera Details:")
    print(f"  IP:       localhost (127.0.0.1)")
    print(f"  Port:     {port}")
    print(f"  Username: admin")
    print(f"  Password: admin")
    print("\nManufacturer: CamOpt AI")
    print("Model:        Mock-Camera-1080p")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down mock server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
