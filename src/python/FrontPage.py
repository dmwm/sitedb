from cherrypy import expose, HTTPError
from cherrypy.lib.static import serve_file
import os, re, jsmin

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
    DIR = os.path.abspath(__file__).rsplit('/', 5)[0]
    PVS = os.environ["PROTOVIS_ROOT"]
    YUI = os.environ["YUI_ROOT"] + "/build"
    X = self._x = (__file__.find("/xlib/") >= 0 and "x") or ""

    def _load(dir, filename):
      return file("%s/%s" % (dir, filename)).read()

    def _css(dir, filename, rewrite):
      text = _load(dir, filename)
      if rewrite == "YUI":
        path = filename.rsplit('/', 1)[0]
        text = re.sub(r"url\((\.\./)+([-a-z._/]+)\)", r"url(yui/\2)", text)
        text = re.sub(r"url\(([-a-z._]+)\)", r"url(yui/%s/\1)" % path, text)

      text = re.sub(r'/\*(?:.|[\r\n])*?\*/', '', text)
      text = re.sub(r'[ \t]+', ' ', text)
      text = re.sub(re.compile(r'^[ \t]+', re.M), ' ', text)
      text = re.sub(re.compile(r'\s+$', re.M), '', text)
      text = re.sub(r'\n+', '\n', text)
      return "\n" + text + "\n"

    def _js(dir, filename, minimise):
      text = _load(dir, filename)
      if minimise:
        text = jsmin.jsmin(text)
      return "\n" + text + "\n"

    CSS = [_css(dir, filename, rewrite)
           for dir, filename, rewrite in
           ((DIR, X + "data/css/sitedb.css", None),
            (YUI, "container/assets/skins/sam/container.css", "YUI"),
            (YUI, "resize/assets/skins/sam/resize.css", "YUI"))]

    JS = [_js(dir, filename, min)
          for dir, filename, min in
          ((YUI, "yahoo/yahoo.js", True),
           (YUI, "dom/dom.js", True),
           (YUI, "event/event.js", True),
           (YUI, "connection/connection.js", True),
           (YUI, "utilities/utilities.js", False),
           (YUI, "container/container-min.js", False),
           (YUI, "resize/resize-min.js", False),
           (PVS, "protovis-r3.2.js", False),
           (DIR, X + "data/javascript/sprintf.js", True),
           (DIR, X + "data/javascript/utils.js", True),
           (DIR, X + "data/javascript/sitedb-addrs.js", True),
           (DIR, X + "data/javascript/sitedb-core.js", True),
           (DIR, X + "data/javascript/sitedb-admin.js", True),
           (DIR, X + "data/javascript/sitedb-sites.js", True),
           (DIR, X + "data/javascript/sitedb-people.js", True),
           (DIR, X + "data/javascript/sitedb-pledges.js", True))]

    self._app = app
    self._content = DIR
    self._page = _load(DIR, X + "data/templates/sitedb.html") \
                 .replace("@JS@", "".join(JS)) \
                 .replace("@CSS@", "".join(CSS))

  @expose
  def yui(self, *args, **kwargs):
    """Serve YUI static assets needed by JavaScript."""
    path = "/".join(args)
    if re.match(r"^[-a-z_/]+\.(png|gif)$", path):
      return serve_file(self._yui + '/' + path)
    raise HTTPError(404, "No such file")

  @expose
  def static(self, *args, **kwargs):
    """Serve our own static assets."""
    if len(args) == 1 and re.match(r"^[-a-z]+\.(png|gif)$", args[0]):
      return serve_file(self._content + '/' + self._x + 'data/images/' + args[0])
    raise HTTPError(404, "No such file")

  @expose
  def index(self):
    """Generate the SiteDB front page."""
    return self._page
