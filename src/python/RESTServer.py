import os, re, hashlib, signal, cherrypy, traceback, random, string, inspect, time
from cherrypy import engine, expose, request, response, HTTPError, HTTPRedirect, tools
from threading import Thread, Condition, Lock
from rfc822 import formatdate as rfc822_date
from collections import namedtuple
from traceback import format_exc
from functools import wraps
from RESTError import *
from RESTFormat import *
from RESTValidation import validate_no_more_input

_METHODS = ('GET', 'HEAD', 'POST', 'PUT', 'DELETE')
_RX_CENSOR = re.compile(r"(identified by) \S+", re.I)
RESTArgs = namedtuple("RESTArgs", ["args", "kwargs"])

######################################################################
######################################################################
class RESTFrontPage:
  """Base class for a trivial front page intended to hand everything
  over to a javascript-based user interface implementation.

  This front-page simply serves static content like HTML pages, CSS,
  JavaScript and images from number of configurable document roots.
  Text content such as CSS and JavaScript can be scrunched together,
  or combo-loaded, from several files. All the content supports the
  standard ETag and last-modified validation for optimal caching.

  The base class assumes the actual application consists of a single
  front-page, which loads JavaScript and other content dynamically,
  and uses HTML5 URL history features to figure out what to do. That
  is, given application mount point <https://cmsweb.cern.ch/app>, all
  links such as <https://cmsweb.cern.ch/app/foo/bar?q=xyz> get mapped
  to the same page, which then figures out what to do at /foo/bar
  relative location or with the query string part.

  There is a special response for ``rest/preamble.js`` static file.
  This will automatically generate a scriptlet of the following form,
  plus any additional content passed in :ref:`javascript_preamble`::

    var REST_DEBUG = (debug_mode),
        REST_SERVER_ROOT = "(mount)",
        REST_INSTANCES = [{ "id": "...", "title": "...", "rank": N }...];

  REST_DEBUG, ``debug_mode``
    Is set to true/false depending on the value of the constructor
    :ref:`debug_mode` parameter, or if the default None, it's set
    to false if running with minimised assets, i.e. frontpage matches
    ``*-min.html``, true otherwise.

  REST_SERVER_ROOT, ``mount``
    The URL mount point of this object, needed for history init. Taken
    from the constructor argument.

  REST_INSTANCES
    If the constructor is given `instances`, its return value is turned
    into a sorted JSON list of available instances for JavaScript. Each
    database instance should have the dictionary keys "``.title``" and
    "``.order``" which will be used for human visible instance label and
    order of appearance, respectively. The ``id`` is the label to use
    for REST API URL construction: the instance dictionary key. This
    variable will not be emitted at all if :ref:`instances` is None.

  .. rubric:: Attributes

  .. attribute:: _app

     Reference to the application object given to the constructor.

  .. attribute:: _mount

     The mount point given in the constructor.

  .. attribute:: _static

     The roots given to the constructor, with ``rest/preamble.js`` added.

  .. attribute:: _frontpage

     The name of the front page file.

  .. attribute:: _preamble

     The ``rest/preamble.js`` computed as described above.

  .. attribute:: _time

     Server start-up time, used as mtime for ``rest/preamble.js``.
  """

  def __init__(self, app, config, mount, frontpage, roots,
               instances = None, preamble = None, debug_mode = None):
    """.. rubric:: Constructor

    :arg app:                Reference to the :ref:`~.RESTMain` application.
    :arg config:             :ref:`~.WMCore.Configuration` section for me.
    :arg mount str:          URL tree mount point for this object.
    :arg frontpage str:      Name of the front-page file, which must exist in
                             one of the `roots`. If `debug_mode` is None and
                             the name matches ``*-min.html``, then debug mode
                             is set to False, True otherwise.
    :arg roots dict:         Dictionary of roots for serving static files.
                             Each key defines the label and path root for URLs,
                             and the value should have keys "``root``" for the
                             path to start looking up files, and "``rx``" for
                             the regular expression to define valid file names.
                             **All the root paths must end in a trailing slash.**
    :arg instances callable: Callable which returns database instances, often::
                               lambda: return self._app.views["data"]._db
    :arg preamble str:       Optional string for additional content for the
                             pseudo-file ``rest/preamble.js``.
    :arg debug_mode bool:    Specifies how to set REST_DEBUG, see above."""

    # Verify all roots do end in a slash.
    for origin, info in roots.iteritems():
      if not re.match(r"^[-a-z0-9]+$", origin):
        raise ValueError("invalid root label")
      if not info["root"].endswith("/"):
        raise ValueError("%s 'root' must end in a slash" % origin)

    # Add preamble pseudo-root.
    roots["rest"] = { "root": None, "rx": re.compile(r"^preamble(?:-min)?\.js$") }

    # Save various things.
    self._start = time.time()
    self._app = app
    self._mount = mount
    self._frontpage = frontpage
    self._static = roots
    if debug_mode is None:
      debug_mode = not frontpage.endswith("-min.html")

    # Delay preamble setup until server start-up so that we don't try to
    # dereference instances() until after it's been finished constructing.
    engine.subscribe("start", lambda: self._init(debug_mode, instances, preamble), 0)

  def _init(self, debug_mode, instances, preamble):
    """Delayed preamble initialisation after server is fully configured."""
    self._preamble = ("var REST_DEBUG = %s" % ((debug_mode and "true") or "false"))
    self._preamble += (", REST_SERVER_ROOT = '%s'" % self._mount)

    if instances:
       instances = [dict(id=k, title=v[".title"], order=v[".order"])
                    for k, v in instances().iteritems()]
       instances.sort(lambda a, b: a["order"] - b["order"])
       self._preamble += (", REST_INSTANCES = %s" % cjson.encode(instances))

    self._preamble += ";\n%s" % (preamble or "")

  def _serve(self, items):
    """Serve static assets.

    Serve one or more files. If there is just one file, it can be text or
    an image. If there are several files, they are smashed together as a
    combo load operation. In that case it's assume the files are compatible,
    for example all JavaScript or all CSS.

    All normal response headers are set correctly, including Content-Type,
    Last-Modified, Cache-Control and ETag. Automatically handles caching
    related request headers If-Match, If-None-Match, If-Modified-Since,
    If-Unmodified-Since and responds appropriately. The caller should use
    CherryPy gzip tool to handle compression-related headers appropriately.

    In general files are passed through unmodified. The only exception is
    that HTML files will have @MOUNT@ string replaced with the mount point.

    :arg items list(str): One or more file names to serve.
    :returns: File contents combined as a single string."""
    mtime = 0
    result = ""
    ctype = ""

    if not items:
      raise HTTPError(404, "No such file")

    for item in items:
      # There must be at least one slash in the file name.
      if item.find("/") < 0:
        raise HTTPError(404, "No such file")

      # Split the name to the origin part - the name we look up in roots,
      # and the remaining path part for the rest of the name under that
      # root. For example 'yui/yui/yui-min.js' means we'll look up the
      # path 'yui/yui-min.js' under the 'yui' root.
      origin, path = item.split("/", 1)
      if origin not in self._static:
        raise HTTPError(404, "No such file")

      # Look up the description and match path name against validation rx.
      desc = self._static[origin]
      if not desc["rx"].match(path):
        raise HTTPError(404, "No such file")

      # If this is not the pseudo-preamble, make sure the requested file
      # exists, and if it does, read it and remember its mtime. For the
      # pseudo preamble use the precomputed string and server start time.
      if origin != "rest":
        fpath = desc["root"] + path
        if not os.access(fpath, os.R_OK):
          raise HTTPError(404, "No such file")
        try:
          mtime = max(mtime, os.stat(fpath).st_mtime)
          data = file(fpath).read()
        except:
          raise HTTPError(404, "No such file")
      elif self._preamble:
        mtime = max(mtime, self._start)
        data = self._preamble
      else:
        raise HTTPError(404, "No such file")

      # Concatenate contents and set content type based on name suffix.
      ctypemap = { "js": "text/javascript",
                   "css": "text/css",
                   "html": "text/html" }
      suffix = path.rsplit(".", 1)[-1]
      if suffix in ctypemap:
        if not ctype:
          ctype = ctypemap[suffix]
        elif ctype != ctypemap[suffix]:
          ctype = "text/plain"
        if suffix == "html":
          data = data.replace("@MOUNT@", self._mount)
        if result:
          result += "\n"
        result += data
        if not result.endswith("\n"):
          result += "\n"
      elif suffix == "gif":
        ctype = "image/gif"
        result = data
      elif suffix == "png":
        ctype = "image/png"
        result = data
      else:
        raise HTTPError(404, "Unexpected file type")

    # Build final response + headers.
    response.headers['Content-Type'] = ctype
    response.headers['Last-Modified'] = cherrypy.lib.http.HTTPDate(mtime)
    response.headers['Cache-Control'] = "public, max-age=%d" % 86400
    response.headers['ETag'] = '"%s"' % hashlib.sha1(result).hexdigest()
    cherrypy.lib.cptools.validate_since()
    cherrypy.lib.cptools.validate_etags()
    return result

  @expose
  @tools.gzip()
  def static(self, *args, **kwargs):
    """Serve static assets.

    Assumes a query string in the format used by YUI combo loader, with one
    or more file names separated by ampersands (&). Each name must be a plain
    file name, to be found in one of the roots given to the constructor.

    Path arguments must be empty, or consist of a single 'yui' string, for
    use as the YUI combo loader. In that case all file names are prefixed
    with 'yui/' to make them compatible with the standard combo loading.

    Serves assets as documented in :py:func:`serve`."""
    if len(args) > 1 or (args and args[0] != "yui"):
      raise HTTPError(404, "No such file")
    paths = request.query_string.split("&")
    if not paths:
      raise HTTPError(404, "No such file")
    if args:
      paths = [args[0] + "/" + p for p in paths]
    return self._serve(paths)

  @expose
  def feedback(self, *args, **kwargs):
    """Receive browser problem feedback. Doesn't actually do anything, just
    returns an empty string response."""
    return ""

  @expose
  @tools.gzip()
  def default(self, *args, **kwargs):
    """Generate the front page, as documented in :py:func:`serve`. The
    JavaScript will actually work out what to do with the rest of the
    URL arguments; they are not used here."""
    return self._serve([self._frontpage])

######################################################################
######################################################################
class MiniRESTApi:
  def __init__(self, app, config, mount):
    self.app = app
    self.config = config
    self.etag_limit = 8 * 1024 * 1024
    self.compression_level = 9
    self.compression_chunk = 64 * 1024
    self.compression = ['deflate']
    self.formats = [ ('application/json', JSONFormat()),
                     ('application/xml', XMLFormat(self.app.appname)) ]
    self.methods = {}
    self.default_expires = 3600
    self.default_expires_opts = []

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
    except HTTPRedirect:
      raise
    except Exception, e:
      report_rest_error(e, format_exc(), True)
    finally:
      if getattr(request, 'start_time', None):
        response.headers["X-REST-Time"] = "%.3f us" % \
          (1e6 * (time.time() - request.start_time))
  default._cp_config = { 'response.stream': True }

  ####################################################################
  def _call(self, param):
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

    # Check what format the caller requested. At least one is required; HTTP
    # spec says no "Accept" header means accept anything, but that is too
    # error prone for a REST data interface as that establishes a default we
    # cannot then change later. So require the client identifies a format.
    # Browsers will accept at least */*; so can clients who don't care.
    # Note that accept() will raise HTTPError(406) if no match is found.
    # Available formats are either specified by REST method, or self.formats.
    try:
      if not request.headers.elements('Accept'):
        raise NotAcceptable('Accept header required')
      formats = apiobj.get('formats', self.formats)
      format = cherrypy.lib.cptools.accept([f[0] for f in formats])
      fmthandler = [f[1] for f in formats if f[0] == format][0]
    except HTTPError, e:
      format_names = ', '.join(f[0] for f in formats)
      raise NotAcceptable('Available types: %s' % format_names)

    # Validate arguments. May convert arguments too, e.g. str->int.
    safe = RESTArgs([], {})
    for v in apiobj['validation']:
      v(apiobj, request.method, api, param, safe)
    validate_no_more_input(param)

    # Invoke the method.
    obj = apiobj['call'](*safe.args, **safe.kwargs)

    # Add Vary: Accept header.
    vary_by('Accept')

    # Set expires header if applicable. Note that POST/PUT/DELETE are not
    # cacheable to begin with according to HTTP/1.1 specification. We must
    # do this before actually streaming out the response below in case the
    # ETag matching decides the previous response remains valid.
    if request.method == 'GET' or request.method == 'HEAD':
      expires = self.default_expires
      cpcfg = getattr(apiobj['call'], '_cp_config', None)
      if cpcfg and 'tools.expires.on' in cpcfg:
        expires = cpcfg.get('tools.expires.secs', expires)
      expires = apiobj.get('expires', expires)
      if response.headers.has_key('Cache-Control'):
        pass
      elif expires < 0:
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = 'Sun, 19 Nov 1978 05:00:00 GMT'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate,' \
                                            ' post-check=0, pre-check=0'
      elif expires != None:
        expires_opts = apiobj.get('expires_opts', self.default_expires_opts)
        expires_opts = (expires_opts and ', '.join([''] + expires_opts)) or ''
        response.headers['Cache-Control'] = 'max-age=%d%s' % (expires, expires_opts)

    # Format the response.
    response.headers['X-REST-Status'] = 100
    response.headers['Content-Type'] = format
    etagger = apiobj.get('etagger', None) or SHA1ETag()
    reply = stream_compress(fmthandler(obj, etagger),
                            apiobj.get('compression', self.compression),
                            apiobj.get('compression_level', self.compression_level),
                            apiobj.get('compression_chunk', self.compression_chunk))
    return stream_maybe_etag(apiobj.get('etag_limit', self.etag_limit), etagger, reply)

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
class DBConnectionPool(Thread):
  """Asynchronous and robust database connection pool.

  .. rubric:: The pool

  This class provides a database connection pool that is thread safe
  and recovers as gracefully as possible from server side and network
  outages. Thread safety means that multiple threads may check out and
  return connections from or to the pool conncurrently. All connection
  management operations are internally transferred to a separate thread
  in order to guarantee client web server threads never block even if
  the database layer blocks or hangs in connection-related calls.

  In other words the effective purpose of this class is to guarantee
  web servers autonomously and gracefully enter a degraded state when
  the underlying database or network goes out, responding with "503
  database unavailable" but continuing to serve requests otherwise.
  Once database returns to operation the servers normally recover on
  their own without having to be manually restarted. While the main
  intent is to avoid requiring intervention on a production service,
  as a side effect this class makes database-based web services more
  usable on mobile devices with unstable network connections.

  The primary pooling purpose is to cache connections for databases
  for which connections are expensive, in particular Oracle. Instead
  of creating a new connection for each use, much of the time the pool
  returns a compatible idle connection which the application was done
  using. Connections unused for more than a pool-configured timeout are
  automatically closed.

  Between uses the connections are reset by rolling back any pending
  operations, and tested for validity by probing the server for
  "liveness" response. Connections failing tests are automatically
  disposed; when returning conections to the pool clients may indicate
  they've had trouble with it, and the pool will reclaim the connection
  instead of queuing it for reuse. In general it is hard to tell which
  errors involved connection-related issues, so it is safer to flag all
  errors on returning the connection. It is however better to filter
  out frequent benign errors such as integrity violations to avoid
  excessive connectin churn.

  Other database connection pool implementations exist, including for
  instance a session pool in the Oracle API (cx_Oracle's SessionPool).
  The reason this class implements pooling and not just validation is
  to side-step blocking or thread unsafe behaviour in the others. All
  connection management operations are passed to a worker thread. If
  the database connection layer stalls, HTTP server threads requesting
  connections will back off gracefully, reporting to their own clients
  that the database is currently unavailable. On the other hand no
  thread is able to create a connection to database if one connection
  stalls, but usually that would happen anyway with at least Oracle.

  The hand-over to the worker thread of course adds overhead, but the
  increased robustness and gracefulness in face of problems in practice
  outweighs the cost by far, and is in any case cheaper than creating
  a new connection each time. The level of overhead can be tuned by
  adjusting condition variable contention (cf. `num_signals`).

  The connections returned to clients are neither garbage collected
  nor is there a ceiling on a maximum number of connections returned.
  The client needs to be careful to `put()` as many connections as it
  received from `get()` to avoid leaking connections.

  .. rubric:: Pool specifications

  The database specification handed to the constructor should be a
  dictionary with the members:

  ``type``
    Reference to the DB API module, aka connection type.

  ``schema``
    String, name of the database schema the connection references.
    Sets connection ``current_schema`` attribute.

  ``clientid``
    String, identifies the client to session monitor, normally this
    should be `service-label@fully.qualified.domain`. Sets connection
    ``client_identifier`` attribute.

  ``liveness``
    String, SQL to execute to verify the connection remain usable,
    normally "``select sysdate from dual``" or alike. The statement
    should require a fresh response from the server on each execution
    so avoid "``select 1 from dual``" style cacheable queries.

  ``user``
    String, login user name.

  ``password``
    String, login password for ``user``.

  ``dsn``
    String, login data source name, usually the TNS entry name.

  ``timeout``
    Integer or float, number of seconds to retain unused idle
    connections before closing them. Note that this only applies to
    connections handed back to `put()`; connections given by `get()`
    but never returned to the pool are not considered idle, not even
    if the client loses the handle reference.

  ``stmtcache``
    Optional integer, overrides the default statement cache size 50.

  ``trace``
    Optional boolean flag, if set enables tracing of database activity
    for this pool, including connection ops, SQL executed, commits and
    rollbacks, and pool activity on the handles. If True, connections
    are assigned random unique labels which are used in activity log
    messages. Recycled idle connections also get a new label, but the
    connection log message will include the old label which allows
    previous logs on that connection to be found. Not to be confused
    with database server side logging; see ``session-sql`` for that.

  ``auth-role``
    Optional, (NAME, PASSWORD) string sequence. If set, connections
    acquire the database role *NAME* before use by executing the SQL
    "``set role none``", "``set role NAME identified by PASSWORD``"
    on each `get()` of the connection. In other words, if the role is
    removed or the password is changed, the client will automatically
    shed the role and fail with an error, closing the connection in
    the process, despite connection caching.

  ``session-sql``
    Optional sequence of SQL statement strings. These are executed on
    each connection `get()`. Use with session trace statements such as
    "``alter session set sql_trace = true``",
    "``alter session set events '10046 trace name context forever,
    level 12'``". It's not recommended to make any database changes.

  .. rubric:: Connection handles

  The `get()` method returns a database connection handle, a dict with
  the following members. The exact same dict needs to be returned to
  `put()` -- not a copy of it.

  ``type``
    Reference to DB API module.

  ``pool``
    Reference to this pool object.

  ``connection``
    Reference to the actual DB API connection object.

  ``trace``
    Always present, but may be either boolean False, or a non-empty
    string with the trace message prefix to use for all operations
    concerning this connection.

  .. rubric:: Attributes

  .. attribute:: connection_wait_time

     Number, the maximum time in seconds to wait for a connection to
     complete after which the client will be told the database server
     is unavailable.  This should be large enough to avoid triggering
     unnecessary database unavailability errors in sporadic delays in
     production use, but low enough to bounce clients off when the
     database server is having difficulty making progress.

     In particular client HTTP threads will be tied up this long if
     the DB server is completely hanging: completing TCP connections
     but not the full database handshake, or if TCP connection itself
     is experiencing significant delays. Hence it's important to keep
     this value low enough for the web server not to get dogged down
     or fail with time-out errors itself.

  .. attribute:: wakeup_period

     Number, maximum time in seconds to wait in the worker thread main
     loop before checking any timed out connections. The server does
     automatically adjust the wake-up time depending on work needed,
     so there usually isn't any need to change this value. The value
     should not be decreased very low to avoid an idle server from
     waking up too often.

  .. attribute:: num_signals

     Number of condition variables to use for signalling connection
     completion. The pool creates this many condition variables and
     randomly picks one to signal connection completion between the
     worker and calling threads. Increase this if there is a high
     degree of thread contention on concurrent threads waiting for
     connection completion. The default should be fine for all but
     highest connection reuse rates.

  .. attribute:: max_tries

     The maximum number of times to attempt creating a connection
     before giving up. If a connection fails tests, it is discarded
     and another attempt is made with another connection, either an
     idle one or an entirely new connection if no idle ones remain.
     This variable sets the limit on how many times to try before
     giving up. This should be high enough a value to consume any
     cached bad connections rapidly enough after network or database
     failure. Hence the pool will reclaim any bad connections at the
     maximum rate of `get()` calls times `max_tries` per
     `connection_wait_time`.

     Do not set this value to a very high value if there is a real
     possibility of major operational flukes leading to connection
     storms or account lock-downs, such as using partially incorrect
     credentials or applications with invalid/non-debugged SQL which
     cause connection to be black-listed and recycled. In other words,
     only change this parameter for applications which have undergone
     significant testing in a production environment, with clear data
     evidence the default value is not leading to sufficiently fast
     recovery after connections have started to go sour.

  .. attribute:: dbspec

     Private, the database specification given to the constructor.

  .. attribute:: id

     Private, the id given to the constructor for trace logging.

  .. attribute:: sigready

     Private, `num_signals` long list of condition variables for
     signalling connection attempt result.

  .. attribute:: sigqueue

     Private, condition variable for signalling changes to `queue`.

  .. attribute:: queue

     Private, list of pending requests to the worker thread, access
     to which is protected by `sigqueue`. Connection release requests
     go to the front of the list, connection create requests at the
     end. The worker thread takes the first request in queue, then
     executes the action with `sigqueue` released so new requests can
     be added while the worker is talking to the database.

  .. attribute:: inuse

     Private, list of connections actually handed out by `get()`. Note
     that if the client has already given up on the `get()` request by
     the time the connection is finally established, the connection is
     automatically discarded and not put no this list. This list may be
     accessed only in the worker thread as no locks are available to
     protect the access; `logstatus()` method provides the means to log
     the queue state safely in the worker thread.

  .. attribute:: idle

     Private, list of idle connections, each of which has ``expires``
     element to specify the absolute time when it will expire. The
     worker thread schedules to wake up within five seconds after the
     next earliest expire time, or in `wakeup_period` otherwise, and
     of course whenever new requests are added to `queue`. This list
     may be accessed only in the work thread as no locks are available
     to protect the access; `logstatus()` method provides the means to
     log the queue state safely in the worker thread.

  .. rubric:: Constructor

  The constructor automatically attaches this object to the cherrypy
  engine start/stop messages so the background worker thread starts or
  quits, respectively. The pool does not attempt to connect to the
  database on construction, only on the first call to `get()`, so it's
  safe to create the pool even if network or database are unavailable.

  :arg dbspec dict: Connection specification as described above.
  :arg id str: Identifier used to label trace connection messages for
               this pool, such as the full class name of the owner."""

  connection_wait_time = 8
  wakeup_period = 60
  num_signals = 4
  max_tries = 5

  def __init__(self, id, dbspec):
    Thread.__init__(self, name=self.__class__.__name__)
    self.sigready = [Condition() for _ in xrange(0, self.num_signals)]
    self.sigqueue = Condition()
    self.queue = []
    self.idle = []
    self.inuse = []
    self.dbspec = dbspec
    self.id = id
    engine.subscribe("start", self.start, 100)
    engine.subscribe("stop", self.stop, 100)

  def logstatus(self):
    """Pass a request to the worker thread to log the queue status.

    It's recommended that the owner hook this method to a signal such
    as SIGUSR2 so it's possible to get the process dump its database
    connections status, especially the number of `inuse` connections,
    from outside the process.

    The request is inserted in the front of current list of pending
    requests, but do note the request isn't executed directly. If the
    worker thread is currently blocked in a database or network call,
    log output is only generated when the worker resumes control.

    :returns: Nothing."""
    self.sigqueue.acquire()
    self.queue.insert(0, (self._status, None))
    self.sigqueue.notifyAll()
    self.sigqueue.release()

  def stop(self):
    """Tell the pool to stop processing requests and to exit from the
    worker thread.

    The request is inserted in the front of current list of pending
    requests. The worker thread will react to it as soon as it's done
    processing any currently ongoing database or network call. If the
    database API layer is completely wedged, that might be never, in
    which case the application should arrange for other means to end,
    either by using a suicide alarm -- for example by calling
    signal.alarm() but not setting SIGALRM handler -- or externally
    by arranging SIGKILL to be delivered.

    Since this request is inserted in the front of pending requests,
    existing connections, whether idle or in use, will not be closed
    or even rolled back. It's assumed the database server will clean
    up the connections once the process exits.

    The constructor automatically hooks the cherrypy engine 'stop'
    message to call this method.

    :returns: Nothing."""
    self.sigqueue.acquire()
    self.queue.insert(0, (None, None))
    self.sigqueue.notifyAll()
    self.sigqueue.release()

  def get(self, id, module):
    """Get a new connection from the pool, identified to server side and
    the session monitor as to be used for action `id` by `module`.

    This retrieves the next available idle connection from the pool, or
    creates a new connection if none are available. Before handing back
    the connection, it's been tested to be actually live and usable.
    If the database connection specification included a role attribute
    or session statements, they will have been respectively set and
    executed.

    The connection request is appended to the current queue of requests.
    If the worker thread does not respond in `connection_wait_time`, the
    method gives up and indicates the database is not available. When
    that happens, the worker thread will still attempt to complete the
    connection, but will then discard it.

    :arg id     str: Identification string for this connection request.
                     This will set the ``clientinfo`` and ``action``
                     attributes on the connection for database session
                     monitoring tools to visualise and possibly remote
                     debugging of connection use.

    :arg module str: Module using this connection, typically the fully
                     qualified python class name. This will set the
                     ``module`` attribute on the connection object for
                     display in database session monitoring tools.

    :returns: A `(HANDLE, ERROR)` tuple. If a connection was successfully
              made, `HANDLE` will contain a dict with connection data as
              described in the class documentation and `ERROR` is `None`.
              If no connection was made at all, returns `(None, None)`.
              Returns `(None, (ERROBJ, TRACEBACK))` if there was an error
              making the connection that wasn't resolved in `max_tries`
              attempts; `ERROBJ` is the last exception thrown, `TRACEBACK`
              the stack trace returned by `format_exc()` for it."""

    sigready = random.choice(self.sigready)
    arg = { "error": None, "handle": None, "signal": sigready,
            "abandoned": False, "id": id, "module": module }

    self.sigqueue.acquire()
    self.queue.append((self._connect, arg))
    self.sigqueue.notifyAll()
    self.sigqueue.release()

    sigready.acquire()
    now = time.time()
    until = now + self.connection_wait_time
    while True:
      dbh = arg["handle"]
      err = arg["error"]
      if dbh or err or now >= until:
        arg["abandoned"] = True
        break
      sigready.wait(until - now)
      now = time.time()
    sigready.release()
    return dbh, err

  def put(self, dbh, bad=False):
    """Add a database handle `dbh` back to the pool.

    Normally `bad` would be False and the connection is added back to
    the pool as an idle connection, and will be reused for a subsequent
    connection.

    Any pending operations on connections are automatically cancalled
    and rolled back before queuing them into the idle pool. These will
    be executed asynchronously in the database connection worker thread,
    not in the caller's thread. However note that if the connection
    became unusable, attempting to roll it back may block the worker.
    That is normally fine as attempts to create new connections will
    start to fail with timeout, leading to "database unavailable" errors.

    If the client has had problems with the connection, it should most
    likely set `bad` to True, so the connection will be closed and
    discarded. It's safe to reuse connections after benign errors such
    as basic integrity violations. However there are a very large class
    of obscure errors which actually mean the connection handle has
    become unusable, so it's generally safer to flag the handle invalid
    on error -- with the caveat that errors should be rare to avoid
    excessive connection churn.

    :arg dbh dict: A database handle previously returned by `get()`. It
                   must be the exact same dict object, not a copy.
    :arg bad bool: If True, `dbh` is likely bad, so please try close it
                   instead of queuing it for reuse.
    :returns: Nothing."""

    self.sigqueue.acquire()
    self.queue.insert(0, ((bad and self._disconnect) or self._release, dbh))
    self.sigqueue.notifyAll()
    self.sigqueue.release()

  def run(self):
    """Run the connection management thread."""

    # Run forever, pulling work from "queue". Round wake-ups scheduled
    # from timeouts to five-second quantum to maximise the amount of
    # work done per round of clean-up and reducing wake-ups.
    next = self.wakeup_period
    while True:
      # Whatever reason we woke up, even if sporadically, process any
      # pending requests first.
      self.sigqueue.acquire()
      self.sigqueue.wait(max(next, 5))
      while self.queue:
        # Take next action and execute it. "None" means quit. Release
        # the queue lock while executing actions so callers can add
        # new requests, e.g. release connections while we work here.
        # The actions are not allowed to throw any exceptions.
        action, arg = self.queue.pop(0)
        self.sigqueue.release()
        if action:
          action(arg)
        else:
          return
	self.sigqueue.acquire()
      self.sigqueue.release()

      # Check idle connections for timeout expiration. Calculate the
      # next wake-up as the earliest expire time, but note that it
      # gets rounded to minimum five seconds above to scheduling a
      # separate wake-up for every handle. Note that we may modify
      # 'idle' while traversing it, so need to clone it first.
      now = time.time()
      next = self.wakeup_period
      for old in self.idle[:]:
        if old["expires"] <= now:
	  self.idle.remove(old)
          self._disconnect(old)
        else:
          next = min(next, old["expires"] - now)

  def _status(self, *args):
    """Action handler to dump the queue status."""
    cherrypy.log("DATABASE CONNECTIONS: %s@%s %s: timeout=%d inuse=%d idle=%d"
                 % (self.dbspec["user"], self.dbspec["dsn"], self.id,
                    self.dbspec["timeout"], len(self.inuse), len(self.idle)))

  def _error(self, title, rest, err, where):
    """Internal helper to generate error message somewhat similar to
    :ref:`~.RESTError.report_rest_error()`.

    :arg title str: All-capitals error message title part.
    :arg rest str: Possibly non-empty trailing error message part.
    :arg err Exception: Exception object reference.
    :arg where str: Traceback for `err` as returned by :ref:`format_exc()`."""
    errid = "%032x" % random.randrange(1 << 128)
    cherrypy.log("DATABASE THREAD %s ERROR %s@%s %s %s.%s %s%s (%s)"
                 % (title, self.dbspec["user"], self.dbspec["dsn"], self.id,
                    getattr(err, "__module__", "__builtins__"),
                    err.__class__.__name__, errid, rest, str(err).rstrip()))
    for line in where.rstrip().split("\n"):
      cherrypy.log("  " + line)

  def _connect(self, req):
    """Action handler to fulfill a connection request."""
    s = self.dbspec
    dbh, err = None, None

    # If tracing, issue log line that identifies this connection series.
    trace = s["trace"] and ("RESTSQL:" + "".join(random.sample(string.letters, 12)))
    trace and cherrypy.log("%s ENTER %s@%s %s (%s) inuse=%d idle=%d" %
                           (trace, s["user"], s["dsn"], self.id, req["id"],
                            len(self.inuse), len(self.idle)))

    # Attempt to connect max_tries times.
    for i in xrange(0, self.max_tries):
      try:
        # Take next idle connection, or make a new one if none exist.
        # Then test and prepare that connection, linking it in trace
        # output to any previous uses of the same object.
        dbh = (self.idle and self.idle.pop()) or self._new(s, trace)
        assert dbh["pool"] == self
        assert dbh["connection"]
        prevtrace = dbh["trace"]
        dbh["trace"] = trace
        self._test(s, prevtrace, trace, req, dbh)

        # The connection is ok. Kill expire limit and return this one.
        if "expires" in dbh:
	  del dbh["expires"]
        break
      except Exception, e:
        # The connection didn't work, report and remember this exception.
        # Note that for every exception reported for the server itself
        # we may report up to max_tries exceptions for it first. That's
        # a little verbose, but it's more useful to have all the errors.
        err = (e, format_exc())
        self._error("CONNECT", "", *err)
        dbh and self._disconnect(dbh)
        dbh = None

    # Return the result, and see if the caller abandoned this attempt.
    req["signal"].acquire()
    req["error"] = err
    req["handle"] = dbh
    abandoned = req["abandoned"]
    req["signal"].notifyAll()
    req["signal"].release()

    # If the caller is known to get our response, record the connection
    # into 'inuse' list. Otherwise discard any connection we made.
    if not abandoned and dbh:
      self.inuse.append(dbh)
    elif abandoned and dbh:
      cherrypy.log("DATABASE THREAD CONNECTION ABANDONED %s@%s %s"
                   % (self.dbspec["user"], self.dbspec["dsn"], self.id))
      self._disconnect(dbh)

  def _new(self, s, trace):
    """Helper function to create a new connection with `trace` identifier."""
    trace and cherrypy.log("%s instantiating a new connection" % trace)
    return { "pool": self, "trace": trace, "type": s["type"], "connection":
             s["type"].connect(s["user"], s["password"], s["dsn"], threaded=True) }

  def _test(self, s, prevtrace, trace, req, dbh):
    """Helper function to prepare and test an existing connection object."""
    # Set statement cache. Default is 50 statments but spec can override.
    c = dbh["connection"]
    c.stmtcachesize = s.get("stmtcache", 50)

    # Emit log message to identify this connection object. If it was
    # previously used for something else, log that too for detailed
    # debugging involving problems with connection reuse.
    client_version = ".".join(str(x) for x in s["type"].clientversion())
    prevtrace = ((prevtrace and prevtrace != trace and
                  " (previously %s)" % prevtrace.split(":")[1]) or "")
    trace and cherrypy.log("%s%s connected, client: %s, server: %s, stmtcache: %d"
                           % (trace, prevtrace, client_version,
                              c.version, c.stmtcachesize))

    # Set the target schema and identification attributes on this one.
    c.current_schema = s["schema"]
    c.client_identifier = s["clientid"]
    c.clientinfo = req["id"]
    c.module = req["module"]
    c.action = req["id"]

    # Ping the server. This will detect some but not all dead connections.
    trace and cherrypy.log("%s ping" % trace)
    c.ping()

    # At least server responded, now try executing harmless SQL but one
    # that requires server to actually respond. This detects remaining
    # bad connections.
    trace and cherrypy.log("%s check [%s]" % (trace, s["liveness"]))
    c.cursor().execute(s["liveness"])

    # If the pool requests authentication role, set it now. First reset
    # any roles we've acquired before, then attempt to re-acquire the
    # role. Hence if the role is deleted or its password is changed by
    # application admins, we'll shed any existing privileges and close
    # the connection right here. This ensures connection pooling cannot
    # be used to extend role privileges forever.
    if "auth-role" in s:
      trace and cherrypy.log("%s set role none")
      c.cursor().execute("set role none")
      trace and cherrypy.log("%s set role %s" % (trace, s["auth-role"][0]))
      c.cursor().execute("set role %s identified by %s" % s["auth-role"])

    # Now execute session statements, e.g. tracing event requests.
    if "session-sql" in s:
      for sql in s["session-sql"]:
        trace and cherrypy.log("%s session-sql [%s]" % (trace, sql))
        c.cursor().execute(sql)

    # OK, connection's all good.
    trace and cherrypy.log("%s connection established" % trace)

  def _release(self, dbh):
    """Action handler to release a connection back to the pool."""
    try:
      # Check the handle didn't get corrupted.
      assert dbh["pool"] == self
      assert dbh["connection"]
      assert dbh in self.inuse
      assert dbh not in self.idle
      assert "expires" not in dbh

      # Remove from 'inuse' list first in case the rest throws/hangs.
      s = self.dbspec
      trace = dbh["trace"]
      self.inuse.remove(dbh)

      # Roll back any started transactions. Note that we don't want to
      # call cancel() on the connection here as it will most likely just
      # degenerate into useless "ORA-25408: can not safely replay call".
      trace and cherrypy.log("%s release with rollback" % trace)
      dbh["connection"].rollback()

      # Record expire time and put to end of 'idle' list; _connect()
      # takes idle connections from the back of the list, so we tend
      # to reuse most recently used connections first, and to prune
      # the number of connections in use to the minimum.
      dbh["expires"] = time.time() + s["timeout"]
      self.idle.append(dbh)
      trace and cherrypy.log("%s RELEASED %s@%s timeout=%d inuse=%d idle=%d"
                             % (trace, s["user"], s["dsn"], s["timeout"],
                                len(self.inuse), len(self.idle)))
    except Exception, e:
      # Something went wrong, nuke the connection from orbit.
      self._error("RELEASE", " failed to release connection", e, format_exc())

      try: self.inuse.remove(dbh)
      except ValueError: pass

      try: self.idle.remove(dbh)
      except ValueError: pass

      self._disconnect(dbh)

  def _disconnect(self, dbh):
    """Action handler to discard the connection entirely."""
    try:
      # Assert internal consistency invariants.
      assert dbh not in self.inuse
      assert dbh not in self.idle

      # Close the connection.
      s = self.dbspec
      trace = dbh["trace"]
      trace and cherrypy.log("%s disconnecting" % trace)
      dbh["connection"].close()

      # Remove references to connection object as much as possible.
      del dbh["connection"]
      dbh["connection"] = None

      # Note trace that this is now gone.
      trace and cherrypy.log("%s DISCONNECTED %s@%s timeout=%d inuse=%d idle=%d"
                             % (trace, s["user"], s["dsn"], s["timeout"],
                                len(self.inuse), len(self.idle)))
    except Exception, e:
      self._error("DISCONNECT", " (ignored)", e, format_exc())

class DatabaseRESTApi(RESTApi):
  _ALL_POOLS = []

  def __init__(self, app, config, mount):
    RESTApi.__init__(self, app, config, mount)
    signal.signal(signal.SIGUSR2, self._logconnections)
    modname, item = config.db.rsplit(".", 1)
    module = __import__(modname, globals(), locals(), [item])
    self._db = getattr(module, item)
    myid = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
    for spec in self._db.values():
      for db in spec.values():
        if isinstance(db, dict):
          db["pool"] = DBConnectionPool(myid, db)
          DatabaseRESTApi._ALL_POOLS.append(db["pool"])

  @staticmethod
  def _logconnections(*args):
    map(lambda p: p.logstatus(), DatabaseRESTApi._ALL_POOLS)

  def _add(self, entities):
    self._addEntities(entities, self._dbenter, self._wrap)

  def _wrap(self, handler):
    @wraps(handler)
    def dbapi_wrapper(*xargs, **xkwargs):
      try:
        return handler(*xargs, **xkwargs)
      except Exception, e:
        self._dberror(e, format_exc(), False)
    return dbapi_wrapper

  def _dberror(self, errobj, trace, inconnect):
    # Grab last sql executed and whatever binds were used so far,
    # the database type object, and null out the rest so that
    # post-request and any nested error handling will ignore it.
    db = request.db
    type = db["type"]
    instance = db["instance"]
    sql = (db["last_sql"],) + db["last_bind"]

    # If this wasn't connection failure, just release the connection.
    # If that fails, force drop the connection. We ignore errors from
    # this since we are attempting to report another earlier error.
    db["handle"] and db["pool"].put(db["handle"], True)
    del request.db
    del db

    # Raise an error of appropriate type.
    errinfo = { "errobj": errobj, "trace": trace }
    dberrinfo = { "errobj": errobj, "trace": trace,
                  "lastsql": sql, "instance": instance }
    if inconnect:
      raise DatabaseUnavailable(**dberrinfo)
    elif isinstance(errobj, type.IntegrityError):
      if errobj.args[0].code in (1, 2292):
        # ORA-00001: unique constraint (x) violated
        # ORA-02292: integrity constraint (x) violated - child record found
        raise ObjectAlreadyExists(**errinfo)
      elif errobj.args[0].code in (1400, 2290):
        # ORA-01400: cannot insert null into (x)
        # ORA-02290: check constraint (x) violated
        raise InvalidParameter(**errinfo)
      elif errobj.args[0].code == 2291:
        # ORA-02291: integrity constraint (x) violated - parent key not found
        raise MissingObject(**errinfo)
      else:
        raise DatabaseExecutionError(**dberrinfo)
    elif isinstance(errobj, type.OperationalError):
      raise DatabaseUnavailable(**dberrinfo)
    elif isinstance(errobj, type.InterfaceError):
      raise DatabaseConnectionError(**dberrinfo)
    elif isinstance(errobj, (HTTPRedirect, RESTError)):
      raise
    else:
      raise DatabaseExecutionError(**dberrinfo)

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
    request.db = { "instance": instance, "type": db["type"], "pool": db["pool"],
                   "handle": None, "last_sql": None, "last_bind": (None, None) }

  def _dbenter(self, apiobj, method, api, param, safe):
    assert getattr(request, "db", None), "Expected DB args from _precall"
    assert isinstance(request.db, dict), "Expected DB args from _precall"

    # Get a pool connection to the instance.
    request.rest_generate_data = None
    request.rest_generate_preamble = {}
    module = "%s.%s" % (apiobj['entity'].__class__.__module__,
                        apiobj['entity'].__class__.__name__)
    id = "%s %s %s" % (method, request.db["instance"], api)
    dbh, err = request.db["pool"].get(id, module)

    if err:
      self._dberror(err[0], err[1], True)
    elif not dbh:
      del request.db
      raise DatabaseUnavailable()
    else:
      request.db["handle"] = dbh
      request.rest_generate_data = apiobj.get("generate", None)
      request.hooks.attach('on_end_request', self._dbexit, failsafe = True)

  def _dbexit(self):
    if getattr(request, "db", None) and request.db["handle"]:
      request.db["pool"].put(request.db["handle"], False)

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
    assert request.db["handle"], "DB connection missing"
    sql = self.sqlformat(None, sql) # FIXME: schema prefix?
    trace = request.db["handle"]["trace"]
    request.db["last_bind"] = None, None
    request.db["last_sql"] = re.sub(_RX_CENSOR, r"\1 <censored>", sql)
    trace and cherrypy.log("%s prepare [%s]" % (trace, sql))
    c = request.db["handle"]["connection"].cursor()
    c.prepare(sql)
    return c

  def execute(self, sql, *binds, **kwbinds):
    c = self.prepare(sql)
    trace = request.db["handle"]["trace"]
    request.db["last_bind"] = (binds, kwbinds)
    trace and cherrypy.log("%s execute: %s %s" % (trace, binds, kwbinds))
    return c, c.execute(None, *binds, **kwbinds)

  def executemany(self, sql, *binds, **kwbinds):
    c = self.prepare(sql)
    trace = request.db["handle"]["trace"]
    request.db["last_bind"] = (binds, kwbinds)
    trace and cherrypy.log("%s executemany: %s %s" % (trace, binds, kwbinds))
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
    trace = request.db["handle"]["trace"]
    trace and cherrypy.log("%s commit" % trace)
    request.db["handle"]["connection"].commit()
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
  def __init__(self, app, api, config, mount):
    self.app = app
    self.api = api
    self.config = config
    self.mount = mount

def restcall(func=None, args=None, generate="result", **kwargs):
  def apply_restcall_opts(func, args=args, generate=generate, kwargs=kwargs):
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
  return (func and apply_restcall_opts(func)) or apply_restcall_opts

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
