import re, cherrypy, cjson, types, hashlib, xml.sax.saxutils
from RESTError import RESTError, ExecutionError, report_rest_error
from traceback import format_exc

def md5etag(curtag, val):
  """Compute MD5 hash over contents for ETag header.

  If `curtag` is `None`, instantiates a new MD5 engine.
  Otherwise `curtag` is an existing MD5 engine, presumably
  from a previous call to this function.

  If `val` is not `None`, cranks the MD5 engine with it
  and returns the reference to engine, to be passed back
  in a later call.

  If `val` is `None`, returns the final hex string digest."""
  if val == None:
    if curtag:
      return curtag.hexdigest()
    else:
      return None

  if curtag == None:
    curtag = hashlib.md5()

  curtag.update(val)
  return curtag

def is_iterable(obj):
  """Check if `obj` is iterable."""
  try:
    iter(obj)
  except TypeError:
    return False
  else:
    return True

class XMLFormat:
  """Format an iterable of objects into XML encoded in UTF-8.

  Generates normally first a preamble, a stream of XML-rendered objects,
  then the trailer, computing an ETag on the output string in the process.
  This is designed exclusively for use with iterables for chunked transfer
  encoding HTTP responses; it's not a general purpose formatting utility.

  Outputs first a preamble, then XML encoded output of input stream, and
  finally a trailer. At the end sets ETag response header to the value
  computed and X-REST-Status to 100. Any exceptions raised by input stream
  are reported to `report_rest_error` and swallowed, as this is normally
  used to generate output for CherryPy responses, which cannot handle
  exceptions reasonably after the output generation begins. Once the
  preamble has been emitted, the trailer is also emitted even if input
  stream raises an exception, in order to make the output well-formed;
  the client must inspect the X-REST-Status trailer header to find out
  if it got the complete output. The ETag header is generated for output
  produced, even if an exception is raised.

  The ETag generation is deterministic only if iterating over input is
  deterministic. Beware in particular the key order for a dict is
  arbitrary and may differ for two semantically identical dicts.

  The output is generated as an XML document whose top-level entity name
  is defined by the label given at the formatter construction time. The
  caller must define ``cherrypy.request.rest_generate_data`` to element
  name for wrapping stream contents. Usually the top-level entity is the
  application name and the ``cherrypy.request.rest_generate_data`` is
  ``result``.

  Iterables are output as ``<array><i>ITEM</i><i>ITEM</i></array>``.
  Dictionaries are output as ``<dict><KEY>VALUE</KEY></dict>``. `None`
  is output as empty contents, and hence there is no way to distinguish
  `None` and an empty string from each other. Scalar types are output
  as rendered by `str()`, but obviously XML encoding unsafe characters.
  This class does not support formatting arbitrary types.

  The formatter does not insert any spaces into the output. Although the
  output is generated as a preamble, stream of objects, and trailer just
  like by the `JSONFormatter`, each of which is a separate HTTP transfer
  chunk, the output does *not* have guaranteed line-oriented structure
  like the `JSONFormatter` produces. Note in particular that if the data
  stream contains strings with newlines, the output will have arbitrary
  line structure. On the other hand, as the output is well-formed XML,
  virtually all SAX processors can read the stream incrementally even if
  the client isn't able to fully preserve chunked HTTP transfer encoding."""

  def __init__(self, label):
    self.label = label

  @staticmethod
  def format_obj(obj):
    """Render an object `obj` into XML."""
    if isinstance(obj, type(None)):
      result = ""
    elif isinstance(obj, (str, int, float, bool)):
      result = xml.sax.saxutils.escape(str(obj).encode("utf-8"))
    elif isinstance(obj, dict):
      result = "<dict>"
      for k, v in obj.iteritems():
        assert re.match(r"^[-A-Za-z0-9_]+$", k)
        result += "<%s>%s</%s>" % (k, XMLFormat.format_obj(v), k)
      result += "</dict>"
    elif is_iterable(obj):
      result = "<array>"
      for v in obj:
        result += "<i>%s</i>" % XMLFormat.format_obj(v)
      result += "</array>"
    else:
      cherrypy.log("cannot represent object of type %s in xml (%s)"
                   % (type(obj).__class__.__name__, repr(obj)))
      raise ExecutionError("cannot represent object in xml")
    return result

  @staticmethod
  def stream_chunked(preamble, trailer, stream, etag):
    """Generator for actually producing the output."""
    etagval = None

    try:
      preamble = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n" + (preamble or "")
      etagval = etag(etagval, preamble)
      yield preamble

      try:
        for obj in stream:
          chunk = XMLFormat.format_obj(obj)
          etagval = etag(etagval, chunk)
          yield chunk
      except GeneratorExit:
        trailer = None
        raise
      finally:
        if trailer:
          etagval = etag(etagval, trailer)
          yield trailer

      etagval = etag(etagval, None)
      cherrypy.response.headers["X-REST-Status"] = 100
    except RESTError, e:
      report_rest_error(e, format_exc(), False)
    except Exception, e:
      report_rest_error(ExecutionError(), format_exc(), False)
    finally:
      if etagval:
        cherrypy.response.headers["ETag"] = etagval

  def __call__(self, stream, etag):
    preamble = "<%s>" % self.label
    if cherrypy.request.rest_generate_preamble:
      desc = self.format_obj(cherrypy.request.rest_generate_preamble)
      preamble += "<desc>%s</desc>" % desc
    preamble += "<%s>" % cherrypy.request.rest_generate_data
    trailer = "</%s></%s>" % (cherrypy.request.rest_generate_data, self.label)
    return self.stream_chunked(preamble, trailer, stream, etag)

class JSONFormat:
  """Format an iterable of objects into JSON.

  Generates normally first a preamble, a stream of JSON-rendered objects,
  then the trailer, computing an ETag on the output string in the process.
  This is designed exclusively for use with iterables for chunked transfer
  encoding HTTP responses; it's not a general purpose formatting utility.

  Outputs first a preamble, then JSON encoded output of input stream, and
  finally a trailer. At the end sets ETag response header to the value
  computed and X-REST-Status to 100. Any exceptions raised by input stream
  are reported to `report_rest_error` and swallowed, as this is normally
  used to generate output for CherryPy responses, which cannot handle
  exceptions reasonably after the output generation begins. Once the
  preamble has been emitted, the trailer is also emitted even if input
  stream raises an exception, in order to make the output well-formed;
  the client must inspect the X-REST-Status trailer header to find out
  if it got the complete output. The ETag header is generated for output
  produced, even if an exception is raised.

  The ETag generation is deterministic only if `cjson.encode()` output is
  deterministic for the input. Beware in particular the key order for a
  dict is arbitrary and may differ for two semantically identical dicts.

  The output is always generated as a JSON dictionary. The caller must
  define ``cherrypy.request.rest_generate_data`` as the key for actual
  contents, usually something like "result". The `stream` value will be
  generated as an array value for that key.

  If ``cherrypy.request.rest_generate_preamble`` is a non-empty list, it
  is output as the ``desc`` key value in the preamble before outputting
  the `stream` contents. Otherwise the output consists solely of `stream`.
  A common use of ``rest_generate_preamble`` is list of column labels
  with `stream` an iterable of lists of column values.

  The output is guaranteed to contain one line of preamble which starts a
  dictionary and an array ("``{key: [``"), one line of JSON rendering of
  each object in `stream`, with the first line starting with exactly one
  space and second and subsequent lines starting with a comma, and one
  final trailer line consisting of "``]}``". Each line is generated as a
  HTTP transfer chunk. This format is fixed so readers can be constructed
  to read and parse the stream incrementally one line at a time."""

  @staticmethod
  def stream_chunked(preamble, trailer, stream, etag):
    """Generator for actually producing the output."""
    etagval = None
    comma = " "

    try:
      if preamble:
        etagval = etag(etagval, preamble)
        yield preamble

      try:
        for obj in stream:
          chunk = comma + cjson.encode(obj) + "\n"
          etagval = etag(etagval, chunk)
          yield chunk
          comma = ","
      except GeneratorExit:
	trailer = None
        raise
      finally:
        if trailer:
          etagval = etag(etagval, trailer)
          yield trailer

      etagval = etag(etagval, None)
      cherrypy.response.headers["X-REST-Status"] = 100
    except RESTError, e:
      report_rest_error(e, format_exc(), False)
    except Exception, e:
      report_rest_error(ExecutionError(), format_exc(), False)
    finally:
      cherrypy.response.headers["ETag"] = etagval

  def __call__(self, stream, etag):
    """Main entry point for generating output for `stream` using `etag`
    object to generate ETag header. This returns a generator function
    for producing text output for each object in `stream`. The intention
    is that the caller will use the iterable to generate chunked HTTP
    transfer encoding of the object stream formatted in a very specific
    JSON rendering optimised for high-throughput reading."""
    comma = ""
    preamble = "{"
    trailer = "]}\n"
    if cherrypy.request.rest_generate_preamble:
      desc = cjson.encode(cherrypy.request.rest_generate_preamble)
      preamble += '"desc": %s' % desc
      comma = ", "
    preamble += '%s"%s": [\n' % (comma, cherrypy.request.rest_generate_data)
    return self.stream_chunked(preamble, trailer, stream, etag)

class RawFormat:
  """Format an iterable of objects as raw data.

  Generates raw data completely unmodified, for example image data or
  streaming arbitrary external data files including even plain text.
  Computes an ETag on the output in the process.  If the raw data is
  a simple string, yields it as such without using chunking, otherwise
  generates the input stream as chunked transfer encoding HTTP response.

  After the output has been emitted, sets ETag response header to the
  value computed and X-REST-Status to 100. Any exceptions raised by input
  stream are reported to `report_rest_error` and swallowed, as this is
  normally used to generate output for CherryPy responses, which cannot
  handle exceptions reasonably after the output generation begins. The
  client must inspect the X-REST-Status trailer header to find out if it
  got the complete output. The ETag header is generated for output
  produced, even if an exception is raised."""

  @staticmethod
  def stream_chunked(stream, etag):
    """Generator for actually producing the output."""
    etagval = None

    # Make 'stream' iterable; we don't have unsafe strings here.
    if isinstance(stream, types.FileType):
      stream = cherrypy.lib.file_generator(stream, 1024*1024)

    try:
      for chunk in stream:
        etagval = etag(etagval, chunk)
        yield chunk

      etagval = etag(etagval, None)
      cherrypy.response.headers["X-REST-Status"] = 100
    except RESTError, e:
      report_rest_error(e, format_exc(), False)
    except Exception, e:
      report_rest_error(ExecutionError(), format_exc(), False)
    finally:
      cherrypy.response.headers["ETag"] = etagval

  def __call__(self, stream, etag):
    """Main entry point for generating output for `stream` using `etag`
    object to generate ETag header. If `stream` is a scalar object or a
    string, returns immediately with the headers set, otherwise returns
    a generator function for producing a verbatim copy of `stream` item.
    The intention is that the caller will use the iterable to generate
    chunked HTTP transfer encoding, or a simple result such as an image."""
    if isinstance(stream, basestring) or stream is None:
      if stream is None: stream = ''
      cherrypy.response.headers["ETag"] = etag(etag(None, stream), None)
      cherrypy.response.headers["X-REST-Status"] = 100
      return stream
    else:
      return self.stream_chunked(stream, etag)
