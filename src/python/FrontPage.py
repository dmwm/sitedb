from RESTServer import RESTFrontPage
import os, re, cjson, SiteDB.Regexps

class FrontPage(RESTFrontPage):
  """SiteDB front page.

  SiteDB V2 provides only one web page, the front page. The page just
  loads the javascript user interface, complete with CSS and all JS
  code embedded into it. The only additional callouts needed are the
  image resources needed for YUI and other site graphics.

  The JavaScript code performs all the app functionality via the REST
  interface defined by the :class:`~.Data` class. Mostly it just does bulk
  load of the various details, and organises it into a nice user interface,
  and where necessary and appropriate, offers an interface to edit the
  information. Virtually all interactive functionality is done on the
  client side, including things like searching.

  User navigation state is stored in the fragment part of the URL, e.g.
  <https://cmsweb.cern.ch/sitedb/prod/sites/T1_CH_CERN>."""

  def __init__(self, app, config, mount):
    """
    :arg app: reference to the application object.
    :arg config: reference to the configuration.
    :arg str mount: URL mount point."""
    CONTENT = os.path.abspath(__file__).rsplit('/', 5)[0]
    X = (__file__.find("/xlib/") >= 0 and "x") or ""
    roots = \
    {
      "sitedb":
      {
        "root": "%s/%sdata/" % (CONTENT, X),
        "rx": re.compile(r"^[a-z]+/[-a-z0-9]+\.(?:css|js|png|gif|html)$")
      },

      "yui":
      {
        "root": "%s/build/" % os.environ["YUI3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9/_]+\.(?:css|js|png|gif)$")
      },

      "d3":
      {
        "root": "%s/data/" % os.environ["D3_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+/[-a-z0-9]+(?:\.min)?\.(?:css|js)$")
      },

      "xregexp":
      {
        "root": "%s/data/xregexp/" % os.environ["XREGEXP_ROOT"],
        "rx": re.compile(r"^[-a-z0-9]+(?:-min)?\.js$")
      }
    }

    frontpage = "sitedb/templates/sitedb.html"
    if os.path.exists("%s/templates/sitedb-min.html" % roots["sitedb"]["root"]):
      frontpage = "sitedb/templates/sitedb-min.html"

    regexps = dict((name[3:], getattr(SiteDB.Regexps, name).pattern)
                   for name in dir(SiteDB.Regexps)
                   if name.startswith("RX_") and name != "RX_PASSWD")

    RESTFrontPage.__init__(self, app, config, mount, frontpage, roots,
                           instances = lambda: app.views["data"]._db,
                           preamble = "var SITEDB_REGEXPS = %s;\n"
                                      % cjson.encode(regexps))
