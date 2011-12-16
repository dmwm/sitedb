from cherrypy import expose, HTTPError, request, response, tools
from cherrypy.lib import cptools, http
import os, re, jsmin, hashlib, cjson

class FrontPage:
  """SiteDB front page.

  SiteDB V2 provides only one web page, the front page. The page just
  loads the javascript user interface, complete with CSS and all JS
  code embedded into it. The only additional callouts needed are the
  image resources needed for YUI and other site graphics.

  The javascript code performs all the app functionality via the REST
  interface defined by `Data` class. Mostly it just does bulk load of
  the various details, and organises it into a nice user interface,
  and where necessary and appropriate, offers an interface to edit the
  information. Virtually all interactive functionality is done on the
  client side, including things like searching.

  User navigation state is stored in the fragment part of the URL, e.g.
  <https://cmsweb.cern.ch/sitedb#v,s,CERN> to view site 'CERN'."""

  def __init__(self, app, config, mount):
    """Initialise the main server."""
    CONTENT = os.path.abspath(__file__).rsplit('/', 5)[0]
    X = (__file__.find("/xlib/") >= 0 and "x") or ""
    self._mount = mount
    self._app = app
    self._static = \
    {
      "sitedb":
      {
        "root": "%s/%sdata/" % (CONTENT, X),
        "rx": re.compile(r"^[a-z]+/[-a-z0-9]+\.(?:css|js|png|gif|html)$")
      },

      "yui":
      {
        "root": "%s/build/" % os.environ["YUI3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9/]+\.(?:css|js|png|gif)$")
      },

      "d3":
      {
        "root": "%s/data/" % os.environ["D3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9]+(?:\.min)?\.(?:css|js)$")
      }
    }

  def _serve(self, items):
    """Serve static assets."""
    mtime = 0
    result = ""
    ctype = ""

    if not items:
      raise HTTPError(404, "No such file")

    for item in items:
      origin, path = item.split("/", 1)
      if origin not in self._static:
        raise HTTPError(404, "No such file")
      desc = self._static[origin]
      fpath = desc["root"] + path
      suffix = path.rsplit(".", 1)[-1]
      if not desc["rx"].match(path) or not os.access(fpath, os.R_OK):
        raise HTTPError(404, "No such file")

      mtime = max(mtime, os.stat(fpath).st_mtime)
      data = file(fpath).read()

      if suffix == "js":
        if not ctype:
          ctype = "text/javascript"
        elif ctype != "text/javascript":
          ctype = "text/plain"

        if origin == "sitedb":
          jsmin.jsmin(data)

        if result == "":
          instances = [dict(id=k, title=v[".title"], order=v[".order"])
		       for k, v in self._app.views["data"]._db.iteritems()]
          instances.sort(lambda a, b: a["order"] - b["order"])
          result = ("var REST_SERVER_ROOT = '%s';\n"
                    "var REST_INSTANCES = %s;\n"
                    % (self._mount, cjson.encode(instances)))

        result += "\n" + data + "\n"

      elif suffix == "css":
        if not ctype:
          ctype = "text/css"
        elif ctype != "text/css":
          ctype = "text/plain"

        data = re.sub(r'/\*(?:.|[\r\n])*?\*/', '', data)
        data = re.sub(r'[ \t]+', ' ', data)
        data = re.sub(re.compile(r'^[ \t]+', re.M), ' ', data)
        data = re.sub(re.compile(r'\s+$', re.M), '', data)
        data = re.sub(r'\n+', '\n', data)
        result += "\n" + data + "\n"

      elif origin == "sitedb" and suffix == "html":
        if not ctype:
          ctype = "text/html"
        elif ctype != "text/html":
          ctype = "text/plain"

        data = data.replace("@MOUNT@", self._mount)
        result += data

      elif suffix == "gif":
        ctype = "image/gif"
        result = data
      elif suffix == "png":
        ctype = "image/png"
        result = data
      else:
        raise HTTPError(404, "Unexpected file type")

    response.headers['Content-Type'] = ctype
    response.headers['Last-Modified'] = http.HTTPDate(mtime)
    response.headers['Cache-Control'] = "public, max-age=%d" % 86400
    response.headers['ETag'] = '"%s"' % hashlib.sha1(result).hexdigest()
    cptools.validate_since()
    cptools.validate_etags()
    return result

  @expose
  @tools.gzip()
  def static(self, *args, **kwargs):
    """Serve static assets."""
    if len(args) > 1 or (args and args[0] != "yui"):
      raise HTTPError(404, "No such file")
    paths = request.query_string.split("&")
    if not paths:
      raise HTTPError(404, "No such file")
    if args:
      paths = [args[0] + "/" + p for p in paths]
    return self._serve(paths)

  @expose
  def feedback(self, **kwargs):
    """Receive browser problem feedback."""
    return ""

  @expose
  @tools.gzip()
  def default(self, *args, **kwargs):
    """Generate the SiteDB front page."""
    return self._serve(["sitedb/templates/sitedb.html"])
