import os
import re

# Missing credentials must stop the listener rather than turn an empty header into authorization.
if not re.fullmatch(r"[0-9a-f]{64}", os.environ.get("LAWCAST_API_SERVICE_TOKEN", "")):
    raise SystemExit("LAWCAST_API_SERVICE_TOKEN must contain 32 random bytes as hexadecimal")
