import re, cherrypy, traceback, random, xml, cjson, inspect, time, hashlib, imp
from cherrypy import expose, request, response, HTTPError
from cherrypy.lib.cptools import accept
from rfc822 import formatdate as HTTPDate
from collections import namedtuple
from traceback import format_exc
from functools import wraps
from RESTError import *
from RESTValidation import validate_no_more_input
import xml.sax.saxutils

_METHODS = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE')
_RX_CENSOR = re.compile(r"(identified by) \S+", re.I)

def _error_header(header, val):
  if val:
    val = val.replace("\n", "; ")
    if len(val) > 200: val = val[:197] + "..."
    response.headers[header] = val

def _rest_error(err, trace, throw):
  if isinstance(err, DatabaseError) and err.errobj:
    offset = None
    sql, binds, kwbinds = err.lastsql
    if sql and err.errobj.args and hasattr(err.errobj.args[0], 'offset'):
      offset = err.errobj.args[0].offset
      sql = sql[:offset] + "<**>" + sql[offset:]
    cherrypy.log("SERVER DATABASE ERROR %s.%s %s (%s); last statement:"
                 " %s; binds: %s, %s; offset: %s"
                 % (getattr(err.errobj, "__module__", "__builtins__"),
                    err.errobj.__class__.__name__,
                    err.errid, str(err.errobj).rstrip(), sql, binds, kwbinds,
                    offset))
    for line in err.trace.rstrip().split("\n"): cherrypy.log("  " + line)
    response.headers["X-REST-Status"] = str(err.app_code)
    response.headers["X-Error-HTTP"] = str(err.http_code)
    response.headers["X-Error-ID"] = err.errid
    _error_header("X-Error-Detail", err.message)
    _error_header("X-Error-Info", err.info)
    if throw: raise HTTPError(err.http_code, err.message)
  elif isinstance(err, RESTError):
    if err.errobj:
      cherrypy.log("SERVER REST ERROR %s.%s %s (%s); derived from %s.%s (%s)"
                   % (err.__module__, err.__class__.__name__,
                      err.errid, err.message,
                      getattr(err.errobj, "__module__", "__builtins__"),
                      err.errobj.__class__.__name__,
		      str(err.errobj).rstrip()))
      trace = err.trace
    else:
      cherrypy.log("SERVER REST ERROR %s.%s %s (%s)"
                   % (err.__module__, err.__class__.__name__,
                      err.errid, err.message))
    for line in trace.rstrip().split("\n"): cherrypy.log("  " + line)
    response.headers["X-REST-Status"] = str(err.app_code)
    response.headers["X-Error-HTTP"] = str(err.http_code)
    response.headers["X-Error-ID"] = err.errid
    _error_header("X-Error-Detail", err.message)
    _error_header("X-Error-Info", err.info)
    if throw: raise HTTPError(err.http_code, err.message)
  elif isinstance(err, HTTPError):
    errid = "%032x" % random.randrange(1 << 128)
    cherrypy.log("SERVER HTTP ERROR %s.%s %s (%s)"
                 % (err.__module__, err.__class__.__name__,
                    errid, str(err).rstrip()))
    for line in trace.rstrip().split("\n"): cherrypy.log("  " + line)
    response.headers["X-REST-Status"] = str(200)
    response.headers["X-Error-HTTP"] = str(err.status)
    response.headers["X-Error-ID"] = errid
    _error_header("X-Error-Detail", err.message)
    if throw: raise err
  else:
    errid = "%032x" % random.randrange(1 << 128)
    cherrypy.log("SERVER OTHER ERROR %s.%s %s (%s)"
                 % (getattr(err, "__module__", "__builtins__"),
                    err.__class__.__name__,
                    errid, str(err).rstrip()))
    for line in trace.rstrip().split("\n"): cherrypy.log("  " + line)
    response.headers["X-REST-Status"] = 400
    response.headers["X-Error-HTTP"] = 500
    response.headers["X-Error-ID"] = errid
    if throw: raise HTTPError(500, "Server error")

def _is_iterable(obj):
  try: iter(obj)
  except TypeError: return False
  else: return True

def _xml_obj_format(obj):
  if isinstance(obj, type(None)):
    result = ""
  elif isinstance(obj, (str, int, float, bool)):
    result = xml.sax.saxutils.escape(str(obj).encode("utf-8"))
  elif isinstance(obj, dict):
    result = "<dict>"
    for k, v in obj.iteritems():
      assert re.match(r"^[-A-Za-z0-9_]+$", k)
      result += "<%s>%s</%s>" % (k, _xml_obj_format(v), k)
    result += "</dict>"
  elif _is_iterable(obj):
    result = "<array>"
    for v in obj:
      result += "<i>%s</i>" % _xml_obj_format(v)
    result += "</array>"
  else:
    cherrypy.log("cannot represent object of type %s in xml (%s)"
                 % (type(obj).__class__.__name__, repr(obj)))
    raise ExecutionError("cannot represent object in xml")
  return result

def _xml_stream_chunker(preamble, trailer, stream, etag):
  etagval = None

  try:
    preamble = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n" + (preamble or "")
    etagval = etag(etagval, preamble)
    yield preamble

    for obj in stream:
      chunk = _xml_obj_format(obj)
      etagval = etag(etagval, chunk)
      yield chunk

    if trailer:
      etagval = etag(etagval, trailer)
      yield trailer

    etagval = etag(etagval, None)
    response.headers["X-REST-Status"] = 100
  except RESTError, e:
    _rest_error(e, format_exc(), False)
  except Exception, e:
    _rest_error(ExecutionError(), format_exc(), False)
  finally:
    if etagval:
      response.headers["ETag"] = etagval

def _json_stream_chunker(preamble, trailer, stream, etag):
  etagval = None
  comma = " "

  try:
    if preamble:
      etagval = etag(etagval, preamble)
      yield preamble

    for obj in stream:
      chunk = comma + cjson.encode(obj) + "\n"
      etagval = etag(etagval, chunk)
      yield chunk
      comma = ","

    if trailer:
      etagval = etag(etagval, trailer)
      yield trailer

    etagval = etag(etagval, None)
    response.headers["X-REST-Status"] = 100
  except RESTError, e:
    _rest_error(e, format_exc(), False)
  except Exception, e:
    _rest_error(ExecutionError(), format_exc(), False)
  finally:
    response.headers["ETag"] = etagval

RESTArgs = namedtuple("RESTArgs", ["args", "kwargs"])

class MiniRESTApi:
  def __init__(self, app, config):
    self.app = app
    self.config = config
    self.formats = [ ('application/json', self._json),
                     ('application/xml', self._xml) ]
    self.methods = {}

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
      _rest_error(e, format_exc(), True)
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

  ####################################################################
  def _json(self, stream, etag):
    comma = ""
    preamble = "{"
    trailer = "}\n"
    if request.rest_generate_preamble:
      preamble += '"desc": %s' % cjson.encode(request.rest_generate_preamble)
      comma = ", "
    if request.rest_generate_data:
      preamble += '%s"%s": [\n' % (comma, request.rest_generate_data)
      trailer = "]" + trailer
    return _json_stream_chunker(preamble, trailer, stream, etag)

  def _xml(self, stream, etag):
    preamble = "<%s>" % self.app.appname
    trailer = "</%s>" % self.app.appname
    if request.rest_generate_preamble:
      preamble += "<desc>%s</desc>" % _xml_obj_format(request.rest_generate_preamble)
    if request.rest_generate_data:
      preamble += "<%s>" % request.rest_generate_data
      trailer = ("</%s>" % request.rest_generate_data) + trailer
    return _xml_stream_chunker(preamble, trailer, stream, etag)


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

class DatabaseRESTApi(MiniRESTApi):
  def __init__(self, app, config):
    class DBFactory: pass
    MiniRESTApi.__init__(self, app, config)
    factory = DBFactory()
    mod, fun, args = config.db[0], config.db[1], config.db[2:]
    exec ("from %s import %s\nf.__call__ = %s\n" % (mod, fun, fun)) in {}, {"f": factory}
    self._db = factory(*args)
    self._myid = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
    self.default_expire = 3600

  def _wrap(self, handler):
    @wraps(handler)
    def dbapi_wrapper(*xargs, **xkwargs):
      try:
        return handler(*xargs, **xkwargs)
      except Exception, e:
        self._dberror(request.dbpool, request.dbtype, request.dbconn,
                      e, format_exc(), False)
    return dbapi_wrapper

  def _add(self, entities):
    for label, entity in entities.iteritems():
      for method in _METHODS:
        handler = getattr(entity, method.lower(), None)
        if not handler and method == 'HEAD':
          handler = getattr(entity, 'get', None)
        if handler and getattr(handler, 'rest.exposed', False):
          rest_args = getattr(handler, 'rest.args')
          rest_params = getattr(handler, 'rest.params')
          self._addAPI(method, label, self._wrap(handler), rest_args,
                       [entity.validate, self._dbenter],
                       entity = entity, **rest_params)

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
      raise DatabaseConnectionFailure(errobj = errobj, trace = trace, lastsql = sql)
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
        return
      except Exception, e:
        lasterr = (e, format_exc())
        time.sleep(0.1)

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

def md5etag(curtag, val):
  if val == None:
    if curtag:
      return curtag.hexdigest()
    else:
      return None

  if curtag == None:
    curtag = hashlib.md5()

  curtag.update(val)
  return curtag

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
