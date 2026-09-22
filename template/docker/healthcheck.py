"""Docker HEALTHCHECK: /healthz 200 dönüyor mu?

ALLOWED_HOSTS'taki ilk alan adıyla istek atılır (aksi halde Django DisallowedHost ile 400 döner).
"""

import os
import sys
import urllib.request

host = (os.environ.get("ALLOWED_HOSTS", "localhost").split(",")[0].strip() or "localhost").lstrip(".")
request = urllib.request.Request(
    "http://127.0.0.1:8000/healthz", headers={"Host": host, "X-Forwarded-Proto": "https"}
)
try:
    with urllib.request.urlopen(request, timeout=4) as response:  # noqa: S310 (sabit yerel adres)
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
