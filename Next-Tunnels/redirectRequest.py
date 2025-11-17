# forward_by_host_port.py
from mitmproxy import http, ctx
import re
from urllib.parse import urlparse, urlunparse

def request(flow: http.HTTPFlow) -> None:
  host_header = flow.request.headers.get("host") or flow.request.headers.get(":authority") or ""
  ctx.log.info(f"[REQ] Url:[{flow.request.pretty_url}] | Host header: {host_header} Incoming scheme: {flow.request.scheme} | {flow.request.http_version}")

  flow.request.host = "host.docker.internal"
  flow.request.headers["host"] = "localhost" if host_header.startswith("localhost:") else host_header
  # Log headers
  # ctx.log.info("[REQUEST HEADERS]")
  # for name in flow.request.headers.keys():
  #   for value in flow.request.headers.get_all(name):
  #     ctx.log.info(f" {name}: {value}")

def response(flow: http.HTTPFlow) -> None:
  originalHost = flow.request.headers.get("X-Forwarded-Host")
  originalDomain = get_base_domain(originalHost)
  location = flow.response.headers.get("Location", "")
  ctx.log.info(f"[RES] response: {flow.response} Location:{location} {flow.response.http_version}")
  #Log headers
  # ctx.log.info("[RESPONSE HEADERS]")
  # for name in flow.request.headers.keys():
  #   for value in flow.request.headers.get_all(name):
  #     ctx.log.info(f" {name}: {value}")

  if "set-cookie" in flow.response.headers:
    original_cookies = flow.response.headers.get_all("set-cookie")
    updated_cookies = []
    for cookie in original_cookies:
        # Remove any existing domain=... attribute
        cookie = re.sub(r';\s*domain=[^;]+', '', cookie, flags=re.IGNORECASE)
        # Append the correct domain
        cookie += f"; domain={originalDomain}"
        updated_cookies.append(cookie)
    # Overwrite all Set-Cookie headers with the updated ones
    flow.response.headers.set_all("set-cookie", updated_cookies)
    ctx.log.info("Update set-cookie!")

  # Override redirect Location header if it points to original domain
  if 300 <= flow.response.status_code < 400:
    ctx.log.info(f"Location: {location} AND originalHost:{originalHost}")
    parsed = urlparse(location)
    # Rebuild URL with updated host
    new_location = urlunparse(parsed._replace(netloc=originalHost))
    flow.response.headers["Location"] = new_location
    ctx.log.info(f"✅ Overridden Location header: {new_location}")

def get_base_domain(hostname):
  parts = hostname.strip().split('.')
  if len(parts) >= 2:
      return '.'.join(parts[-2:])  # Get last two segments
  return hostname  # Not enough parts to extract
