import random

class RESTError(Exception):
  http_code = None
  app_code = None
  message = None
  info = None
  errid = None
  errobj = None
  trace = None

  def __init__(self, info = None, errobj = None, trace = None):
    self.errid = "%032x" % random.randrange(1 << 128)
    self.errobj = errobj
    self.info = info
    self.trace = trace

  def __repr__(self):
    return "%s %s [HTTP %d, APP %d, MSG %s, INFO %s, ERR %s]" \
      % (self.__class__.__name__, self.errid, self.http_code, self.app_code,
         repr(self.message).replace("\n", " ~~ "),
         repr(self.info).replace("\n", " ~~ "),
         repr(self.errobj).replace("\n", " ~~ "))

class NotAcceptable(RESTError):
  "Client did not specify format it accepts, or no compatible format was found."
  http_code = 406
  app_code = 201
  message = "Not acceptable"

class UnsupportedMethod(RESTError):
  "Client used HTTP request method which isn't supported for any API call."
  http_code = 405
  app_code = 202
  message = "Request method not supported"

class MethodWithoutQueryString(RESTError):
  "Client provided a query string which isn't acceptable for this request method."
  http_code = 405
  app_code = 203
  message = "Query arguments not supported for this request method"

class APIMethodMismatch(RESTError):
  "Both the API and HTTP request methods are supported, but not in that combination."
  http_code = 405
  app_code = 204
  message = "API not supported for this request method"

class APINotSpecified(RESTError):
  "The request URL is missing API argument."
  http_code = 400
  app_code = 205
  message = "API not specified"

class NoSuchInstance(RESTError):
  "The request URL is missing instance argument or the specified instance does not exist."
  http_code = 404
  app_code = 206
  message = "No such instance"

class DatabaseError(RESTError):
  """Parent class for database-related errors."""
  lastsql = None
  def __init__(self, info = None, errobj = None, trace = None, lastsql = None):
    RESTError.__init__(self, info, errobj, trace)
    self.lastsql = lastsql

class DatabaseUnavailable(DatabaseError):
  """The instance argument is correct, but cannot connect to the database.
  This error will only occur at initial attempt to connect to the database,
  DatabaseConnectionError is raised instead if the connection ends prematurely
  after the transaction has already begun successfully."""
  http_code = 503
  app_code = 401
  message = "Database unavailable"

class DatabaseConnectionError(DatabaseError):
  """Database was available when the operation started, but the connection
  was lost or otherwise failed during the application operation."""
  http_code = 504
  app_code = 402
  message = "Database connection failure"

class DatabaseExecutionError(DatabaseError):
  """Database operation failed."""
  http_code = 500
  app_code = 403
  message = "Execution error"

class MissingParameter(RESTError):
  "Client did not supply a parameter which is required."
  http_code = 400
  app_code = 301
  message = "Missing required parameter"

class InvalidParameter(RESTError):
  "Client supplied invalid value for a parameter."
  http_code = 400
  app_code = 302
  message = "Invalid input parameter"

class MissingObject(RESTError):
  """An object required for the operation is missing. This might be a
  pre-requisite needed to create a reference, or attempt to delete
  an object which does not exist."""
  http_code = 400
  app_code = 303
  message = "Required object is missing"

class TooManyObjects(RESTError):
  """Too many objects matched specified criteria. Usually this means
  more than one object was matched, deleted, or inserted, when only
  exactly one should have been subject to the operation."""
  http_code = 400
  app_code = 304
  message = "Too many objects"

class ObjectAlreadyExists(RESTError):
  """An already existing object is on the way of the operation. This
  is usually caused by uniqueness constraint violations when creating
  new objects."""
  http_code = 400
  app_code = 305
  message = "Object already exists"

class InvalidObject(RESTError):
  "The specified object is invalid."
  http_code = 400
  app_code = 306
  message = "Invalid object"

class ExecutionError(RESTError):
  """Input was in principle correct but there was an error processing
  the request. This normally means either programming error, timeout, or
  an unusual and unexpected problem with the database. For security reasons
  little additional information is returned. If the problem persists, client
  should contact service operators. The returned error id can be used as a
  reference."""
  http_code = 500
  app_code = 403
  message = "Execution error"
