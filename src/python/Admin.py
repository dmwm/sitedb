import os, cherrypy, cjson, socket, cx_Oracle
from cherrypy.test import test, webtest, helper
from WMCore.REST.Test import fake_authz_headers, fake_authz_key_file
from WMCore.REST.Main import RESTMain
from WMCore.REST.Tools import tools
from SiteDB.Config import Config
from SiteDB.Data import Data
from SiteDB.DataAccounts import *
from SiteDB.DataSchema import *
from SiteDB.DataTiers import *
from cherrypy import expose
from getpass import getpass

server = None
authz_key = None
AUTH = { 'admin': { '*': { 'type': cx_Oracle,
                           'trace': True,
                           'schema': "",
                           'clientid': "sitedb-admin@%s" % socket.getfqdn().lower(),
                           'liveness': "select sysdate from dual",
                           'user': "",
	                   'password': "",
	                   'dsn': "",
	                   'timeout': 300 },
                  }
       }

class AdminServer(Data):
  """Server object for REST data access API bootstrap operations."""
  def __init__(self, app, config, mount):
    """
    :arg app: reference to application object; passed to all entities.
    :arg config: reference to configuration; passed to all entities.
    :arg str mount: API URL mount point; passed to all entities."""
    Data.__init__(self, app, config, mount)
    self._add({ "tiers":                  Tiers(app, self, config, mount),
                "accounts":               Accounts(app, self, config, mount),
                "schema":                 Schema(app, self, config, mount) })

class AdminClient(helper.CPWebCase):
  """Client command operations."""

  #: Headers to be used for all request, mainly internal authorisation ones.
  _authz_headers = None

  def __init__(self, *args, **kwargs):
    helper.CPWebCase.__init__(self, *args, **kwargs)

  def runTest(self):
    """This isn't a test suite, we just run as one to get an internal server."""
    pass

  def _marshall(self, args):
    """Build a MIME multi-part form body from arguments.

    :arg list args: sequence of key-value dictionaries for the form data.
    :returns: A tuple (headers, body), where headers is a list of tuples
             and body a string.
    """
    boundary = 'BOUNDARY'
    body, crlf = '', '\r\n'
    for kv in args:
      for key, value in kv.iteritems():
        body += '--' + boundary + crlf
        body += ('Content-Disposition: form-data; name="%s"' % key) + crlf
        body += crlf + str(value) + crlf
    body += '--' + boundary + '--' + crlf + crlf
    return ([('Content-Type', 'multipart/form-data; boundary=' + boundary),
	     ('Content-Length', len(body))],
	    body)

  def _authenticate(self):
    """Return headers to authentication ourselves as a global admin, plus
    an 'Accept' header for JSON content type.

    :returns: a sequence of (header, value) tuples."""
    if not self._authz_headers:
      self._authz_headers = fake_authz_headers\
        (authz_key.data, roles = {"Global Admin": {'group': ['global']}})
      self._authz_headers.append(("Accept", "application/json"))
    return self._authz_headers

  def get_schema(self):
    """Print out the current schema.

    :returns: Nothing."""
    authz = self._authenticate()
    self.getPage("/sitedb/admin/schema", headers=authz)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")
    for row in cjson.decode(self.body)['result']:
      print row

  def modify_schema(self, action):
    """Archive current schema, or move archive back to current.

    :arg str action: ``archive`` or ``restore``.
    :returns: Nothing."""
    assert action in ('archive', 'restore')
    authz = self._authenticate()
    h, b = self._marshall([{"action": action}])
    self.getPage("/sitedb/admin/schema", method="POST", body=b, headers=h+authz)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")

  def remove_schema(self, action):
    """Remove current or archived schema, or both.

    :arg str action: ``all``, ``current`` or ``archive``.
    :returns: Nothing."""
    assert action in ('all', 'current', 'archive')
    authz = self._authenticate()
    h, b = self._marshall([{"action": action}])
    self.getPage("/sitedb/admin/schema", method="DELETE", body=b, headers=h+authz)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")

  def _put(self, to, *args):
    """Perform one PUT operation to server, marshalling arguments.

    :arg str to: entity name.
    :arg list args: sequence of dictionaries for objects to insert.
    :returns: Nothing."""
    authz = self._authenticate()
    h, b = self._marshall(args)
    self.getPage("/sitedb/admin/%s" % to, method="PUT", body=b, headers=h+authz)
    self.assertStatus("200 OK")
    self.assertHeader("X-REST-Status", "100")
    self.assertMatchesBody(r"""\{ "modified": %d \}""" % len(args))

  def load_schema(self):
    """Insert schema plus essential seed data.

    :returns: Nothing."""
    self._put("schema")
    self._put("tiers",
	      {"position": 0, "name": "Tier 0"},
	      {"position": 1, "name": "Tier 1"},
	      {"position": 2, "name": "Tier 2"},
	      {"position": 3, "name": "Tier 3"})
    self._put("roles", {"title": "Global Admin"})
    self._put("groups", {"name": "global"})
    self._put("accounts",
              {"username": "metson",   "passwd": "*"},
	      {"username": "lat",      "passwd": "*"},
	      {"username": "pkreuzer", "passwd": "*"},
	      {"username": "rossman",  "passwd": "*"})
    self._put("people",
	      {"email": "simon.metson@cern.ch", "forename": "Simon", "surname": "Metson",
	       "dn": "/C=UK/O=eScience/OU=Bristol/L=IS/CN=simon metson",
	       "username": "metson", "phone1": "", "phone2": "", "im_handle": ""},
	      {"email": "lat@cern.ch", "forename": "Lassi", "surname": "Tuura",
	       "dn": "/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=lat/CN=437145/CN=Lassi Tuura",
	       "username": "lat", "phone1": "", "phone2": "", "im_handle": ""},
	      {"email": "peter.kreuzer@cern.ch", "forename": "Peter", "surname": "Kreuzer",
	       "dn": "/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=pkreuzer/CN=406463/CN=Peter Kreuzer",
	       "username": "pkreuzer", "phone1": "", "phone2": "", "im_handle": ""},
	      {"email": "rossman@fnal.gov", "forename": "Paul", "surname": "Rossman",
	       "dn": "/DC=org/DC=doegrids/OU=People/CN=Paul Rossman 364403",
	       "username": "rossman", "phone1": "", "phone2": "", "im_handle": ""})
    self._put("group-responsibilities",
	      {"contact": "simon.metson@cern.ch", "role": "Global Admin", "group": "global"},
	      {"contact": "lat@cern.ch", "role": "Global Admin", "group": "global"},
	      {"contact": "peter.kreuzer@cern.ch", "role": "Global Admin", "group": "global"},
	      {"contact": "rossman@fnal.gov", "role": "Global Admin", "group": "global"})

def init_server_auth(user, service, password = None, schema = None):
  """Configure authentication and schema information.

  :arg str user: User name.
  :arg str service: Database service name, usually TNS entry name.
  :arg str password: Password. If None, will prompt for password.
  :arg str schema: Schema name. If None, uses :ref:`user`."""
  p = AUTH["admin"]["*"]
  p["dsn"] = service
  p["schema"] = schema or user
  p["user"] = user
  p["password"] = password or getpass("%s@%s password: " % (user, service))

def setup_server():
  """Create and set up an internal REST server for admin operations."""
  global server, authz_key
  authz_key = fake_authz_key_file()
  cfg = Config(authkey = authz_key.name)
  delattr(cfg.views, 'ui')
  cfg.main.index = 'data'
  cfg.main.silent = True
  cfg.views.data.object = "SiteDB.Admin.AdminServer"
  cfg.views.data.db = "SiteDB.Admin.AUTH"
  server = RESTMain(cfg, os.getcwd())
  server.validate_config()
  server.setup_server()
  server.install_application()
  cherrypy.config.update({'server.socket_port': 8888})
  cherrypy.config.update({'server.socket_host': '127.0.0.1'})
  cherrypy.config.update({'request.show_tracebacks': True})
  cherrypy.config.update({'environment': 'test_suite'})
  cherrypy.config.update({'log.screen': 'True'})
  #for app in cherrypy.tree.apps.values():
  #  app.config["/"]["request.show_tracebacks"] = True
