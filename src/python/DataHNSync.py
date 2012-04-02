import os, sys, time, pycurl, re, string, random, cherrypy, urllib
from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Test import fake_authz_headers
from WMCore.REST.Auth import authz_match
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from SiteDB.HTTPRequest import RequestManager
from threading import Thread, Condition
from traceback import format_exc
from cStringIO import StringIO

class HNSync(RESTEntity):
  """REST entity object for triggering synchronisation with hypernews;
  does not provide any actual data access, just an internal mechanism
  reusing all the database logic.
  """
  def __init__(self, app, api, config, mount):
    RESTEntity.__init__(self, app, api, config, mount)
    if getattr(config, "hnsync", False):
      self._syncer = HNSyncThread(app, config.hnsync, mount,
                                  minreq = getattr(config, "hnsyncreq", 1000),
                                  interval = getattr(config, "hnsynctime", 300),
                                  instance = getattr(config, "hnsyncto", "prod"))
    else:
      self._syncer = None

  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    authz_match(role=["Global Admin"], group=["global"])
    if method == "GET":
      if not self._syncer:
        raise cherrypy.HTTPError(503, "Not running.")

    elif method in ("PUT", "POST"):
      validate_strlist('username', param, safe, RX_USER)
      validate_strlist('passwd',   param, safe, RX_PASSWD)
      validate_strlist('email',    param, safe, RX_EMAIL)
      validate_ustrlist('name',    param, safe, RX_HN_NAME)
      validate_lengths(safe, 'username', 'passwd', 'email', 'name')

      authz = cherrypy.request.user
      if authz['method'] != 'Internal' or authz['login'] != self._syncer.sectoken:
        raise cherrypy.HTTPError(403, "You are not allowed to access this resource.")

  @restcall
  def get(self):
    """Get status of last full and incremental synchronisation."""
    return [self._syncer.status()]

  @restcall
  def put(self, username, passwd, email, name):
    """Perform a full synchronisation.

    :arg list username: accounts to modify.
    :arg list passwd: encrypted passwords.
    :arg list email: emails.
    :arg list name: names.
    :returns: nothing."""
    hnrows = self.api.bindmap(username=username, passwd=passwd, email=email, name=name)
    passwords, contacts, deletions = self._merge(self._current(), hnrows)
    self._update(passwords, contacts, deletions)
    return []

  @restcall
  def post(self, username, passwd, email, name):
    """Perform an incremental synchronisation.

    :arg list username: accounts to modify.
    :arg list passwd: encrypted passwords.
    :arg list name: names.
    :arg list email: emails.
    :returns: nothing."""
    hnrows = self.api.bindmap(username=username, passwd=passwd, email=email, name=name)
    passwords, contacts, _ = self._merge(self._current(), hnrows)
    self._update(passwords, contacts, [])
    return ["done"]

  def _current(self):
    """Return the current user information from the database."""
    users = {}
    c, _ = self.api.execute("""select u.username, u.passwd, c.email,
                                      to_nchar(c.forename),
                                      to_nchar(c.surname)
                               from user_passwd u
                               left join contact c
                                 on c.username = u.username""")

    for row in c:
      username, passwd, email, forename, surname = row
      users[username] = { "username": username, "passwd": passwd,
                          "forename": forename, "surname": surname,
                          "name": " ".join([x for x in forename, surname if x]),
                          "email": email }
    return users

  def _update(self, passwords, contacts, deletions):
    """Perform an actual database update for `passwords`, `contacts` and
    `deletions`. Only statements needing to be executed are executed.
    Commits automatically at the end if necessary."""

    if passwords:
      self.api.executemany("""merge into user_passwd u
                              using dual on (u.username = :username)
                              when not matched then
                                insert (username, passwd)
                                values (:username, :passwd)
                              when matched then update
                                set u.passwd = :passwd
                           """, passwords)

    if contacts:
      self.api.executemany("""merge into contact c
                              using dual on (c.username = :username)
                              when not matched then
                                insert (id, username, forename, surname, email)
                                values (contact_sq.nextval, :username, :forename,
                                        :surname, :email)
                              when matched then update
                                set c.forename = :forename,
                                    c.surname = :surname,
                                    c.email = :email
                           """, contacts)

    if deletions:
      self.api.executemany("""delete from user_passwd
                              where username = :username
                           """, deletions)
      self.api.execute("delete from contact where username is null")

    if passwords or contacts or deletions:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _merge(self, users, hnrows):
    """Merge `hnrows` output into `users`. Returns tuple `(passwords,
    contacts, deletions)` where `passwords` is the insertions and changes
    to be made to username/password info, `contacts` is the corresponding
    changes to contact details, and finally `deletions` is the list of
    accounts to delete; ignore `deletions` for incremental updates."""

    attrs_contact = ("username", "forename", "surname", "email")
    attrs_user = ("username", "passwd")
    attrs_del = ("username",)
    deletions = set(users.keys())
    passwords = []
    contacts = []
    for row in hnrows:
      if row["name"].find(" ") >= 0:
        row["forename"], row["surname"] = row["name"].split(" ", 1)
      else:
        row["forename"] = " " # cannot be null, so put something
        row["surname"] = row["name"]
        row["name"] = "  " + row["name"]

      if row["passwd"] != '*':
        deletions.discard(row["username"])
        if row["username"] not in users:
          passwords.append(row)
          contacts.append(row)
        else:
          user = users[row["username"]]
          if row["passwd"] != user["passwd"]:
            passwords.append(row)
          if row["name"] != user["name"] or row["email"] != user["email"]:
            contacts.append(row)

    for u in users.keys():
      if u.find("@") >= 0:
        deletions.discard(u)

    return ([dict((k, v[k]) for k in attrs_user) for v in passwords],
            [dict((k, v[k]) for k in attrs_contact) for v in contacts],
            [{ "username": v } for v in deletions])

class HNSyncThread(Thread):
  """A task thread to synchronise SiteDB from HyperNews. This runs on
  specific hosts only for which HyperNews admins have authorised access
  to the account scan URLs."""

  _baseurl = "https://hn.cern.ch/cgi-bin/CMS"
  _incurl = "/serveHNUserFile.py"
  _allurl = "/serveHNUserFileAll.py"
  _ident = "SiteDB/%s Python/%s" % \
           (os.environ["SITEDB_VERSION"], ".".join(map(str, sys.version_info[:3])))
  _rxhnpass = re.compile(r"^(?P<username>[a-z0-9_]+(?:\.notcms|\.nocern)?)"
                         r":(?P<passwd>[*]|[A-Za-z0-9._/]{13,})"
                         r":None:None:(?P<name>[^:]+):None:None"
                         r":(?P<email>[-A-Za-z0-9_.%+]+@([-A-Za-z0-9]+\.)+[A-Za-z]{2,5})$")

  def __init__(self, app, baseurl, mount, minreq = 1000, interval = 300, instance = "prod"):
    Thread.__init__(self, name = "HNSync")
    self.sectoken = "".join(random.sample(string.letters, 30))
    self._inturl = "http://localhost:%d%s/%s/hnsync" % \
                   (app.srvconfig.port, mount, instance)
    self._headers = \
      fake_authz_headers(open(app.srvconfig.tools.cms_auth.key_file).read(),
                         method = "Internal", login = self.sectoken,
                         name = self.__class__.__name__, dn = None,
                         roles = {"Global Admin": {"group": ["global"]}}) \
      + [("Accept", "application/json")]

    self._cv = Condition()
    if isinstance(baseurl, str):
      self._baseurl = baseurl

    self._minreq = minreq
    self._interval = interval
    self._stopme = False
    self._full = (0, [], "")
    self._incremental = (0, [], "")
    self._warnings = {}

    self._intreq = RequestManager(num_connections = 2,
                                  user_agent = self._ident,
                                  handle_init = self._handle_init,
                                  request_respond = self._respond,
                                  request_init = self._int_init)
    self._hnreq = RequestManager(num_connections = 2,
                                 user_agent = self._ident,
                                 handle_init = self._handle_init,
                                 request_respond = self._respond,
                                 request_init = self._hn_init)
    cherrypy.engine.subscribe("stop", self.stop)
    cherrypy.engine.subscribe("start", self.start)

  def status(self):
    """Get the processing status. Returns time of last successful full
    and incremental synchronisation with HyperNews."""
    with self._cv:
      return { "full": self._full[:], "incremental": self._incremental[:] }

  def stop(self, *args):
    """Tell the task thread to quit."""
    with self._cv:
      self._stopme = True
      self._cv.notifyAll()

  def run(self):
    """Run synchronisation thread."""
    while True:
      now = time.time()
      until = now + self._interval

      with self._cv:
        while not self._stopme and now < until:
          self._cv.wait(until - now)
          now = time.time()

        if self._stopme:
          return

      try:
        self._sync(now)
      except Exception, e:
        cherrypy.log("SYNC ERROR %s.%s HyperNews sync failed %s"
                     % (getattr(e, "__module__", "__builtins__"),
                        e.__class__.__name__, str(e)))
        for line in format_exc().rstrip().split("\n"):
          cherrypy.log("  " + line)

  def _sync(self, now):
    """Perform one synchronisation. One in four is full update."""
    for k, v in self._warnings.items():
      if v < now - 86400:
        del self._warnings[k]

    if now - self._full[0] > self._interval * 4:
      full = True
      method = "PUT"
      text = self._hnget(self._baseurl + self._allurl)
    else:
      full = False
      method = "POST"
      text = self._hnget(self._baseurl + self._incurl)

    rows = []
    for line in text.split("\n"):
      line = line.replace("\x7f", "").replace("\t", "")
      try:
        line = unicode(line, "utf-8")
      except:
        if line not in self._warnings:
          cherrypy.log("WARNING: hypernews output not utf-8,"
                       " trying as latin1: %s" % repr(line))
          self._warnings[line] = now

        try:
          line = unicode(line, "latin1")
        except:
          continue

      line = line.strip()
      if line.startswith("<") or line == "":
        continue
      m = self._rxhnpass.match(line)
      if not m:
        if line not in self._warnings:
          cherrypy.log("WARNING: ignoring invalid hypernews output: '%s'" % line)
          self._warnings[line] = now
        continue
      rows.append(m.groupdict())

    if full and len(rows) < self._minreq:
      cherrypy.log("ERROR: cowardly refusing full hypernews synchronisation"
                   " with only %d users received, fewer than required %d"
                   % (len(rows), self._minreq))
      return

    result = []
    self._intreq.put((method, rows, result))
    self._intreq.process()

    if full:
      self._full = (now, rows, text, result and result[0])
    else:
      self._incremental = (now, rows, text, result and result[0])

  def _hnget(self, url):
    """Get data from hypernews."""
    result = []
    if url.startswith("/"):
      result.append(open(url).read())
    else:
      self._hnreq.put((url, result))
      self._hnreq.process()
      if not result:
        raise RuntimeError("HyperNews returned no data for %s" % url)
    return result[0]

  def _handle_init(self, c):
    """Initialise curl handle `c`."""
    c.setopt(pycurl.SSL_VERIFYPEER, 0)
    c.setopt(pycurl.SSL_VERIFYHOST, 0)

  def _respond(self, c):
    """Respond to data on curl handle `c`."""
    code = c.getinfo(pycurl.HTTP_CODE)
    if code != 200:
      raise RuntimeError("HTTP status %d for %s" % (code, c.getinfo(pycurl.EFFECTIVE_URL)))
    c.result.append(c.buffer.getvalue())

  def _hn_init(self, c, url, result):
    """Initialise curl handle `c` for hypernews request to `url`."""
    c.setopt(pycurl.URL, url)
    c.result = result

  def _int_init(self, c, method, rows, result):
    """Initialise curl handle `c` for an internal REST API request."""
    type, body = self._encode(rows)
    headers = self._headers[:] + [("Content-Type", type),
                                  ("Content-Length", str(len(body)))]
    if method == "POST":
      c.setopt(pycurl.UPLOAD, 0) # = PUT
      c.setopt(pycurl.POST, 1)
    elif method == "PUT":
      c.setopt(pycurl.POST, 0)
      c.setopt(pycurl.UPLOAD, 1)
    else:
      assert False, "Unsupported method"
    c.setopt(pycurl.URL, self._inturl)
    c.setopt(pycurl.HTTPHEADER, ["%s: %s" % h for h in headers])
    c.setopt(pycurl.READFUNCTION, StringIO(body).read)
    c.result = result

  def _encode(self, rows):
    """Encode dictionaries in `rows` for POST/PUT body as a HTML form."""
    body, sep = "", ""
    for obj in rows:
      for key, value in obj.iteritems():
        body += "%s%s=%s" % (sep, key, urllib.quote(value.encode("utf-8")))
        sep = "&"
    return ("application/x-www-form-urlencoded", body)
