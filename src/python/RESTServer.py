import re, signal, cherrypy, traceback, random, xml, cjson, inspect, time, imp
from cherrypy import expose, request, response, HTTPError
from cherrypy.lib.cptools import accept
from rfc822 import formatdate as HTTPDate
from collections import namedtuple
from traceback import format_exc
from functools import wraps
from RESTError import *
from RESTFormat import *
from RESTValidation import validate_no_more_input

_METHODS = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE')
_RX_CENSOR = re.compile(r"(identified by) \S+", re.I)
RESTArgs = namedtuple("RESTArgs", ["args", "kwargs"])

class MiniRESTApi:
  def __init__(self, app, config):
    self.app = app
    self.config = config
    self.formats = [ ('application/json', JSONFormat()),
                     ('application/xml', XMLFormat(self.app.appname)) ]
    self.methods = {}
    self.default_expire = 3600

  ####################################################################
  def _addAPI(self, method, api, callable, args, validation, **kwargs):
    if method not in _METHODS:
      raise UnsupportedMethod()

    if method not in self.methods:
      self.methods[method] = {}

    if api in self.methods[method]:
      raise ObjectAlreadyExists()

    if not isinstance(args, list):
      raise TypeError("args is required to be a list")

    if not isinstance(validation, list):
      raise TypeError("validation is required to be a list")

    if args and not validation:
      raise ValueError("non-empty validation required for api taking arguments")

    apiobj = { "args": args, "validation": validation, "call": callable }
    apiobj.update(**kwargs)
    self.methods[method][api] = apiobj

  ####################################################################
  @expose
  def default(self, *args, **kwargs):
    try:
      return self._call(RESTArgs(list(args), kwargs))
    except Exception, e:
      report_rest_error(e, format_exc(), True)
    finally:
      if getattr(request, 'start_time', None):
        response.headers["X-REST-Time"] = "%.3f us" % \
          (1e6 * (time.time() - request.start_time))
  default._cp_config = { 'response.stream': True }

  ####################################################################
  def _call(self, param):
    # Check what format the caller requested. At least one is required; HTTP
    # spec says no "Accept" header means accept anything, but that is too
    # error prone for a REST data interface as that establishes a default we
    # cannot then change later. So require the client identifies a format.
    # Browsers will accept at least */*; so can clients who don't care.
    # Note that accept() will raise HTTPError(406) if no match is found.
    try:
      if not request.headers.elements('Accept'):
        raise NotAcceptable()
      format = accept([x[0] for x in self.formats])
      fmthandler = [x[1] for x in self.formats if x[0] == format][0]
    except HTTPError, e:
      raise NotAcceptable(e.message)

    # Make sure the request method is something we actually support.
    if request.method not in self.methods:
      response.headers['Allow'] = " ".join(sorted(self.methods.keys()))
      raise UnsupportedMethod()

    # If this isn't a GET/HEAD request, prevent use of query string to
    # avoid cross-site request attacks and evil silent form submissions.
    # We'd prefer perl cgi behaviour where query string and body args remain
    # separate, but that's not how cherrypy works - it mixes everything
    # into one big happy kwargs.
    if (request.method != 'GET' and request.method != 'HEAD') \
       and request.query_string:
      response.headers['Allow'] = 'GET HEAD'
      raise MethodWithoutQueryString()

    # Give derived class a chance to look at arguments.
    self._precall(param)

    # Make sure caller identified the API to call and it is available for
    # the request method.
    if len(param.args) == 0:
      raise APINotSpecified()
    api = param.args.pop(0)
    if api not in self.methods[request.method]:
      response.headers['Allow'] = \
        " ".join(sorted([m for m, d in self.methods.iteritems() if api in d]))
      raise APIMethodMismatch()
    apiobj = self.methods[request.method][api]

    # Validate arguments. May convert arguments too, e.g. str->int.
    safe = RESTArgs([], {})
    for v in apiobj['validation']:
      v(apiobj, request.method, api, param, safe)
    validate_no_more_input(param)

    # Invoke the method.
    obj = apiobj['call'](*safe.args, **safe.kwargs)

    # FIXME: arbitrary data, e.g. images, octet streams, etc?

    # Format the response.
    response.headers["Content-Type"] = format
    response.headers["Trailer"] = "ETag X-REST-Status"
    reply = fmthandler(obj, apiobj.get('etagger', md5etag))

    # Set expires header if applicable. Note that POST/PUT/DELETE are not
    # cacheable to begin with according to HTTP/1.1 specification.
    if request.method == 'GET' or request.method == 'HEAD':
      expires = apiobj.get('expires', self.default_expire)
      if expires < 0:
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = 'Sun, 19 Nov 1978 05:00:00 GMT'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate,' \
                                            ' post-check=0, pre-check=0'
      elif expires != None:
        response.headers['Expires'] = HTTPDate(time.time() + expires)

    # Indicate success.
    response.headers["X-REST-Status"] = 100
    return reply

  def _precall(self, param):
    pass

######################################################################
######################################################################
class RESTApi(MiniRESTApi):
  def _addEntities(self, entities, entry, wrapper = None):
    for label, entity in entities.iteritems():
      for method in _METHODS:
        handler = getattr(entity, method.lower(), None)
        if not handler and method == 'HEAD':
          handler = getattr(entity, 'get', None)
        if handler and getattr(handler, 'rest.exposed', False):
          rest_args = getattr(handler, 'rest.args')
          rest_params = getattr(handler, 'rest.params')
	  if wrapper: handler = wrapper(handler)
          self._addAPI(method, label, handler, rest_args,
                       [entity.validate, entry],
		       entity = entity, **rest_params)

  def _add(self, entities):
    self._addEntities(entities, self._enter)

  def _enter(self, apiobj, method, api, param, safe):
    request.rest_generate_data = apiobj.get("generate", None)
    request.rest_generate_preamble = {}
    cols = apiobj.get("columns", None)
    if cols:
      request.rest_generate_preamble["columns"] = cols

######################################################################
######################################################################
# - get connection from pool; verify it's ok before using it
# - set c.client_identifier, c.clientinfo, c.module, c.action
#    - program -> sitedb web server @ host
#    - module -> data api
#    - action -> GET/HEAD/PUT/POST/DELETE, method (users, sites, ...)
# - use 'with ... as conn:'
# - check connection liveness with c.ping(), c.execute('select 1 from dual'), etc.
# - check for connection exceptions and retry operation; make sure connection is
#   propery disposed (can throw exceptions?) and if necessary recreate the session
#   pool; auto roll back if some exception happens
# - provide standard wrapper functions to clean up sql before execution
# - use a statement cache (c.stmtcache) [-> automatic with session pool]
# - verify autocommit is off
# - use c.current_schema / alter session set current_schema = foo

class DatabaseRESTApi(RESTApi):
  def __init__(self, app, config):
    class DBFactory: pass
    MiniRESTApi.__init__(self, app, config)
    factory = DBFactory()
    mod, fun, args = config.db[0], config.db[1], config.db[2:]
    exec ("from %s import %s\nf.__call__ = %s\n" % (mod, fun, fun)) in {}, {"f": factory}
    self._db = factory(*args)
    self._myid = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)

  def _add(self, entities):
    self._addEntities(entities, self._dbenter, self._wrap)

  def _wrap(self, handler):
    @wraps(handler)
    def dbapi_wrapper(*xargs, **xkwargs):
      try:
        return handler(*xargs, **xkwargs)
      except Exception, e:
        self._dberror(request.dbpool, request.dbtype, request.dbconn,
                      e, format_exc(), False)
    return dbapi_wrapper

  def _dberror(self, dbpool, dbtype, dbconn, errobj, trace, inconnect):
    # If this was a connection failure and we have a connection object,
    # drop the connection now. Ignore any errors from this.
    if inconnect:
      if dbconn:
        try: dbpool.drop(dbconn)
        except: pass

    # If this wasn't connection failure, just release the connection.
    # If that fails, force drop the connection. We ignore errors from
    # this since we are attempting to report another earlier error.
    elif dbpool:
      try:
        dbpool.release(dbconn)
      except:
        try: dbpool.drop(dbconn)
        except: pass

    # Grab last sql executed and whatever binds were used so far.
    sql = (request.last_statement_sql,) + request.last_statement_binds
    request.last_statement_binds = None, None
    request.last_statement_sql = None

    # Null out connection in request object so post-request and any
    # nested error handling will ignore it.
    request.dbtype = None
    request.dbconn = None
    request.dbpool = None

    # Raise an error of appropriate type.
    if inconnect:
      raise DatabaseUnavailable(errobj = errobj, trace = trace, lastsql = sql)
    elif isinstance(errobj, dbtype.IntegrityError):
      if errobj.args[0].code in (1, 2292):
        # ORA-00001: unique constraint (x) violated
        # ORA-02292: integrity constraint (x) violated - child record found
        raise ObjectAlreadyExists(errobj = errobj, trace = trace)
      elif errobj.args[0].code in (1400, 2290):
        # ORA-01400: cannot insert null into (x)
        # ORA-02290: check constraint (x) violated
        raise InvalidParameter(errobj = errobj, trace = trace)
      elif errobj.args[0].code == 2291:
        # ORA-02291: integrity constraint (x) violated - parent key not found
        raise MissingObject(errobj = errobj, trace = trace)
      else:
        raise DatabaseExecutionError(errobj = errobj, trace = trace, lastsql = sql)
    elif isinstance(errobj, dbtype.OperationalError):
      raise DatabaseUnavailable(errobj = errobj, trace = trace, lastsql = sql)
    elif isinstance(errobj, dbtype.InterfaceError):
      raise DatabaseConnectionError(errobj = errobj, trace = trace, lastsql = sql)
    elif isinstance(errobj, RESTError):
      raise
    else:
      raise DatabaseExecutionError(errobj = errobj, trace = trace, lastsql = sql)

  def _precall(self, param):
    # Check we were given an instance argument and it's known.
    if not param.args or param.args[0] not in self._db:
      raise NoSuchInstance()
    if not re.match(r"^[a-z]+$", param.args[0]):
      raise NoSuchInstance("Invalid instance name")

    instance = param.args.pop(0)

    # Get database object.
    if request.method in self._db[instance]:
      db = self._db[instance][request.method]
    elif request.method == 'HEAD' and 'GET' in self._db[instance]:
      db = self._db[instance]['GET']
    elif '*' in self._db[instance]:
      db = self._db[instance]['*']
    else:
      raise DatabaseUnavailable()

    # Remember database instance choice, but don't do anything about it yet.
    request.db = db
    request.dbinst = instance

  def _dbenter(self, apiobj, method, api, param, safe):
    assert getattr(request, 'db', None), "Expected instance from _precall"
    assert getattr(request, 'dbinst', None), "Expected instance from _precall"

    # Set up 5-second timer and commit suicide once it expires. This is
    # needed because sometimes database connection stuff simply hangs in
    # unrecoverable ways. As ugly as it is, the cleanest solution is to
    # let the entire process die and have the watchdog parent restart it.
    signal.alarm(5)

    # Get a pool connection to the instance.
    db = request.db
    instance = request.dbinst
    action = "%s %s" % (method, api)
    dbtype = db['type']
    dbtrace = db.get('trace', False)
    lasterr = None
    request.dbpool = None
    request.dbtype = None
    request.dbconn = dbconn = None
    request.dbtrace = False
    request.last_statement_binds = None, None
    request.last_statement_sql = None
    request.rest_generate_preamble = {}
    request.rest_generate_data = None

    for i in xrange(0, 5):
      try:
        if dbtrace: cherrypy.log("TRACE SQL connecting")
        dbconn = db['pool'].acquire()
        dbconn.current_schema = db['schema']
        dbconn.client_identifier = db['clientid']
        dbconn.clientinfo = self._myid
        dbconn.module = "%s.%s" % (apiobj['entity'].__class__.__module__,
                                   apiobj['entity'].__class__.__name__)
        dbconn.action = action

        if dbtrace: cherrypy.log("TRACE SQL ping")
        dbconn.ping()

        if dbtrace: cherrypy.log("TRACE SQL liveness: %s" % db['liveness'])
        dbconn.cursor().execute(db['liveness'])

	if 'auth-role' in db:
          if dbtrace: cherrypy.log("TRACE SQL acquire role")
          dbconn.cursor().execute("set role %s identified by %s" % db['auth-role'])

        if 'session-sql' in db:
          for sql in db['session-sql']:
            if dbtrace: cherrypy.log("TRACE SQL session-sql: %s" % sql)
            dbconn.cursor().execute(sql)

        if dbtrace: cherrypy.log("TRACE SQL connected")
        request.dbpool = db['pool']
        request.dbtrace = dbtrace
        request.dbtype = dbtype
        request.dbconn = dbconn
        request.rest_generate_data = apiobj.get("generate", None)
        request.hooks.attach('on_end_request', self._dbexit, failsafe = True)
	signal.alarm(0)
        return
      except Exception, e:
        lasterr = (e, format_exc())
        time.sleep(0.1)

    signal.alarm(0)
    if dbtrace: cherrypy.log("TRACE SQL connection failed: %s" % lasterr)
    self._dberror(db['pool'], dbtype, dbconn, lasterr[0], lasterr[1], True)

  def _dbexit(self):
    if request.dbconn:
      if request.dbtrace: cherrypy.log("TRACE SQL exit")
      request.dbconn.rollback()
      request.dbpool.release(request.dbconn)
    request.db = None
    request.dbinst = None
    request.dbtype = None
    request.dbconn = None
    request.dbpool = None
    request.dbtrace = False
    request.last_statement_binds = None, None
    request.last_statement_sql = None

  def sqlformat(self, schema, sql):
    sql = re.sub(r"--.*", "", sql)
    sql = re.sub(r"^\s+", "", sql)
    sql = re.sub(r"\s+$", "", sql)
    sql = re.sub(r"\n\s+", " ", sql)
    if schema:
      sql = re.sub(r"(?<=\s)((t|seq|ix|pk|fk)_[A-Za-z0-9_]+)(?!\.)",
                   r"%s.\1" % schema, sql)
      sql = re.sub(r"(?<=\s)((from|join)\s+)([A-Za-z0-9_]+)(?=$|\s)",
		   r"\1%s.\3" % schema, sql)
    return sql

  def prepare(self, sql):
    assert request.dbconn, "DB connection missing"
    sql = self.sqlformat(None, sql) # FIXME: schema prefix?
    request.last_statement_sql = re.sub(_RX_CENSOR, r"\1 <censored>", sql)
    request.last_statement_binds = None, None
    if request.dbtrace: cherrypy.log("TRACE SQL prepare: %s" % sql)
    c = request.dbconn.cursor()
    c.prepare(sql)
    return c

  def execute(self, sql, *binds, **kwbinds):
    c = self.prepare(sql)
    request.last_statement_binds = (binds, kwbinds)
    if request.dbtrace: cherrypy.log("TRACE SQL execute: %s %s" % (binds, kwbinds))
    return c, c.execute(None, *binds, **kwbinds)

  def executemany(self, sql, *binds, **kwbinds):
    c = self.prepare(sql)
    request.last_statement_binds = (binds, kwbinds)
    if request.dbtrace: cherrypy.log("TRACE SQL executemany: %s %s" % (binds, kwbinds))
    return c, c.executemany(None, *binds, **kwbinds)

  def query(self, match, select, sql, *binds, **kwbinds):
    c, _ = self.execute(sql, *binds, **kwbinds)
    request.rest_generate_preamble["columns"] = \
      [x[0].lower() for x in c.description]
    if match:
      return rxfilter(match, select, c)
    else:
      return rows(c)

  def modify(self, sql, *binds, **kwbinds):
    if binds:
      c, _ = self.executemany(sql, *binds, **kwbinds)
      expected = len(binds[0])
    else:
      kwbinds = self.bindmap(**kwbinds)
      c, _ = self.executemany(sql, kwbinds, *binds)
      expected = len(kwbinds)
    result = self.rowstatus(c, expected)
    if request.dbtrace: cherrypy.log("TRACE SQL commit")
    request.dbconn.commit()
    return result

  def rowstatus(self, c, expected):
    if c.rowcount < expected:
      raise MissingObject(info = "%d vs. %d expected" % (c.rowcount, expected))
    elif c.rowcount > expected:
      raise TooManyObjects(info = "%d vs. %d expected" % (c.rowcount, expected))
    return rows([{ "modified": c.rowcount }])

  def bindmap(self, **kwargs):
    """Given `kwargs` of equal length list keyword arguments, returns the
    data transposed as list of dictionaries each of which has a value for
    every key from each of the lists.

    This method is convenient for arranging HTTP request keyword array
    parameters for bind arrays suitable for `executemany` call.

    For example given the call `_bindmap(a = [1, 2], b = [3, 4])`, returns
    a list of dictionaries `[{ "a": 1, "b": 3 }, { "a": 2, "b": 4 }]`."""
    keys = kwargs.keys()
    return [dict(zip(keys, vals)) for vals in zip(*kwargs.values())]

class RESTEntity:
  def __init__(self, app, api, config):
    self.app = app
    self.api = api
    self.config = config

def restcall(func=None, args=None, generate="result", **kwargs):
  if not func:
    raise ValueError("'restcall' must be applied to a function")
  if args == None:
    args = [a for a in inspect.getargspec(func).args if a != 'self']
  if args == None or not isinstance(args, list):
    raise ValueError("'args' must be defined")
  kwargs.update(generate = generate)
  setattr(func, 'rest.exposed', True)
  setattr(func, 'rest.args', args or [])
  setattr(func, 'rest.params', kwargs)
  return func

def rows(cursor):
  for row in cursor:
    yield row

def filter(match, cursor):
  for row in cursor:
    if match(*row):
      yield row

def rxfilter(rx, select, cursor):
  for row in cursor:
    if rx.match(select(row)):
      yield row
