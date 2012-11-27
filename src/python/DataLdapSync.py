import os, sys, time, pycurl, re, string, random, cherrypy, urllib, ldap, collections
from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Test import fake_authz_headers
from WMCore.REST.Auth import authz_match
from WMCore.REST.Validation import *
from WMCore.REST.Error import *
from SiteDB.Regexps import *
from SiteDB.HTTPRequest import RequestManager
from threading import Thread, Condition
from traceback import format_exc
from cStringIO import StringIO

class LdapSync(RESTEntity):
  """REST entity object for triggering synchronisation with CERN/LDAP;
  does not provide any actual data access, just an internal mechanism
  reusing all the database logic.
  """
  def __init__(self, app, api, config, mount):
    RESTEntity.__init__(self, app, api, config, mount)
    if getattr(config, "ldapsync", False):
      self._syncer = LdapSyncThread(app, config.ldapsync, mount,
                           cacertdir = getattr(config, "cacertdir",
                                           "/etc/grid-security/certificates"),
                           minreq = getattr(config, "ldsyncreq", 1000),
                           interval = getattr(config, "ldsynctime", 300),
                           instance = getattr(config, "ldsyncto", "test"))
    else:
      self._syncer = None

  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    authz_match(role=["Global Admin"], group=["global"])
    if method == "GET":
      if not self._syncer:
        raise cherrypy.HTTPError(503, "Not running.")

    elif method == "PUT":
      validate_strlist ('username', param, safe, RX_USER)
      validate_strlist ('passwd',   param, safe, RX_PASSWD)
      validate_strlist ('email',    param, safe, RX_EMAIL)
      validate_ustrlist('name',     param, safe, RX_NAME)
      validate_ustrlist('dn',       param, safe, RX_DN)
      validate_lengths(safe, 'username', 'passwd', 'email', 'name', 'dn')

      authz = cherrypy.request.user
      if authz['method'] != 'Internal' or authz['login'] != self._syncer.sectoken:
        raise cherrypy.HTTPError(403, "You are not allowed to access this resource.")

  @restcall
  def get(self):
    """Get status of last full and incremental synchronisation."""
    return [self._syncer.status()]

  @restcall
  def put(self, username, passwd, email, name, dn):
    """Perform a full synchronisation.

    :arg list username: accounts to modify.
    :arg list dn: encrypted passwords.
    :arg list email: emails.
    :arg list name: names.
    :returns: nothing."""
    ldrows = self.api.bindmap(username=username, passwd=passwd, email=email, name=name, dn=dn)
    passwords, contacts, deletions = self._merge(self._current(), ldrows)
    self._update(passwords, contacts, deletions)
    return []

  def _current(self):
    """Return the current user information from the database."""
    users = {}
    c, _ = self.api.execute("""select u.username, u.passwd, c.email,
                                      to_nchar(c.forename),
                                      to_nchar(c.surname),
                                      c.dn
                               from user_passwd u
                               left join contact c
                                 on c.username = u.username""")

    for row in c:
      username, passwd, email, forename, surname, dn = row
      users[username] = { "username": username, "passwd": passwd,
                          "forename": forename, "surname": surname,
                          "name": " ".join([x for x in forename, surname if x]),
                          "email": email, "dn": dn }
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

    for contact in contacts:
      try:
        self.api.execute("""merge into contact c
                            using dual on (c.username = :username)
                            when not matched then
                              insert (id, username, forename, surname, email, dn)
                              values (contact_sq.nextval, :username, :forename,
                                      :surname, :email, :dn)
                            when matched then update
                              set c.forename = :forename,
                                  c.surname = :surname,
                                  c.email = :email,
                                  c.dn = :dn
                         """, contact)
      except Exception, e:
        # Ignore constraint errors for individual users instead of failing
        cherrypy.log("WARNING: failed to update user %s, DN %s: %s"
                     %(contact['username'], contact['dn'], str(e)))
        continue

    if deletions:
      self.api.executemany("""delete from user_passwd
                              where username = :username
                           """, deletions)
      self.api.execute("delete from contact where username is null")

    if passwords or contacts or deletions:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _merge(self, users, ldrows):
    """Merge `ldrows` output into `users`. Returns tuple `(passwords,
    contacts, deletions)` where `passwords` is the insertions and changes
    to be made to username/password info, `contacts` is the corresponding
    changes to contact details, and finally `deletions` is the list of
    accounts to delete."""

    attrs_contact = ("username", "forename", "surname", "email", "dn")
    attrs_user = ("username", "passwd")
    attrs_del = ("username",)
    deletions = set(users.keys())
    passwords = []
    contacts = []
    for row in ldrows:
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
          if row["name"] != user["name"] or row["email"] != user["email"] or row["dn"] != user["dn"]:
            contacts.append(row)

    # do not delete the service accounts
    for u in users.keys():
      if u.find("@") >= 0:
        deletions.discard(u)

    return ([dict((k, v[k]) for k in attrs_user) for v in passwords],
            [dict((k, v[k]) for k in attrs_contact) for v in contacts],
            [{ "username": v } for v in deletions])

class LdapSyncThread(Thread):
  """A task thread to synchronise SiteDB from CERN/LDAP. This runs on
  a single node only in the cluster."""

  _baseurl = "ldaps://xldap.cern.ch:636"
  _ident = "SiteDB/%s Python/%s" % \
           (os.environ["SITEDB_VERSION"], ".".join(map(str, sys.version_info[:3])))

  # The buggy ca.cern.ch user interface allows to put anything, so some users
  # have uploaded CA certificates or even SSH keys. So try to ignore them.
  RX_ALTDN = re.compile(r"(?iu)^X509:.*<S>(([A-Z]+=([-\w _@'.()/]+),?)*(?<!berosservice|CERN Root CA|on Authority))$")

  def __init__(self, app, baseurl, mount, cacertdir = "/etc/grid-security/certificates", minreq = 1000, interval = 300, instance = "test"):
    Thread.__init__(self, name = "LdapSync")
    self.sectoken = "".join(random.sample(string.letters, 30))
    self._inturl = "http://localhost:%d%s/%s/ldapsync" % \
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

    self._cacertdir = cacertdir
    self._minreq = minreq
    self._interval = interval
    self._stopme = False
    self._full = (0, [], [])
    self._warnings = {}

    self._intreq = RequestManager(num_connections = 2,
                                  user_agent = self._ident,
                                  handle_init = self._handle_init,
                                  request_respond = self._respond,
                                  request_init = self._int_init)
    cherrypy.engine.subscribe("stop", self.stop)
    cherrypy.engine.subscribe("start", self.start)

  def status(self):
    """Get the processing status. Returns time of last successful full
    synchronisation with CERN/LDAP."""
    with self._cv:
      return self._full[:]

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
        cherrypy.log("SYNC ERROR %s.%s LDAP sync failed %s"
                     % (getattr(e, "__module__", "__builtins__"),
                        e.__class__.__name__, str(e)))
        for line in format_exc().rstrip().split("\n"):
          cherrypy.log("  " + line)

  def _validate(self, input, type, regexp, now):
    """Convenience method to validate ldap data"""
    if isinstance(input, type):
      m = regexp.match(input)
      if m: return m
    if input not in self._warnings:
      cherrypy.log("WARNING: ldap data failed validation: '%s'" % input)
      self._warnings[input] = now
    return None
    
  def _sync(self, now):
    """Perform full synchronisation."""

    # Delete warnings older than 24 hours
    for k, v in self._warnings.items():
      if v < now - 86400:
        del self._warnings[k]

    # Get the user information from CERN/LDAP
    ldresult = self._ldget(self._baseurl)

    # Process each user record returned
    rows = []
    for (dn, attrs) in ldresult:
      u = { 'username': attrs['sAMAccountName'][0],
            'passwd'  : 'NeedsToBeUpdated',
            'dn'      : dn,
            'name'    : attrs['displayName'][0],
            'email'   : attrs['mail'][0] }
      perid = attrs['employeeID'][0]
      accstatus = attrs['userAccountControl'][0]

      # Do the input validation
      if not ( self._validate(u['username'], str,        RX_USER,   now) and \
               self._validate(u['name'],     basestring, RX_NAME,   now) and \
               self._validate(perid,         str,        RX_UID,    now) and \
               self._validate(u['dn'],       basestring, RX_LDAPDN, now) and \
               self._validate(u['email'],    str,        RX_EMAIL,  now) and \
               self._validate(accstatus,     str,        RX_UID,    now) ):
        cherrypy.log('WARNING: ignoring user with invalid non-optional ldap' \
                     ' data: %s' % u['username'])
        continue

      # Only process normal accounts (aka enabled user accounts).
      if accstatus == '512':
        # newdn is the reversed elements from full name + personid + dn
        newdn = ','.join(('CN='+ u['name'] +',CN='+ perid +','+ u['dn']).split(',')[::-1])
        # in case non-Cern DN was mapped to the account, use it as newdn instead
        for altdn in attrs['altSecurityIdentities']:
          m = self._validate(altdn, basestring, self.RX_ALTDN, now)
          if not m: continue
          # get the last mapped DN not matching the Kerberosservice|CAs
          newdn = m.group(1)
        u['dn'] = '/'+newdn.replace(',','/')

        # add this user to the bulk data to be updated
        rows.append(u)

    # check number of rows is sane
    if len(rows) < self._minreq:
      cherrypy.log("ERROR: cowardly refusing full ldap synchronisation"
                   " with only %d users received, fewer than required %d"
                   % (len(rows), self._minreq))
      return
    cherrypy.log("INFO: found %d valid users in ldap" % len(rows))

    # do the internal api call for the bulk update
    result = []
    self._intreq.put(("PUT", rows, result))
    self._intreq.process()
    self._full = (now, rows, ldresult, result and result[0])

  def _ldget(self, url):
    """Get data from LDAP."""
    result = []

    ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, self._cacertdir)
    l = ldap.initialize(url)
    l.protocol_version = ldap.VERSION3

    # Fetch paged results from ldap server.
    # This is needed because there is a size limit on the CERN ldap server
    # side to return at most 1000 entries per request.
    # For more information, see http://tools.ietf.org/html/rfc2696.html
    srv_ctrls = [ldap.controls.SimplePagedResultsControl(criticality=False, cookie="")]
    while True:
      srv_ctrls[0].size = 1000 # dont necessarily need to match the server limit
      s = l.search_ext('OU=Users,OU=Organic Units,DC=cern,DC=ch',
                       ldap.SCOPE_SUBTREE,
                       '(memberOf=CN=cms-zh,OU=e-groups,OU=Workgroups,DC=cern,DC=ch)',
                       ['sAMAccountName','displayName','employeeID','mail','altSecurityIdentities','userAccountControl'],
                       serverctrls=srv_ctrls,
                       sizelimit=0)
      _, res_data, _, srv_ctrls = l.result3(s, timeout=100)
      result.extend(res_data)
      if not srv_ctrls[0].cookie: break

    if not result:
      raise RuntimeError("Ldap returned no data for %s" % url)
    return result

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

  def _int_init(self, c, method, rows, result):
    """Initialise curl handle `c` for an internal REST API request."""
    type, body = self._encode(rows)
    headers = self._headers[:] + [("Content-Type", type),
                                  ("Content-Length", str(len(body)))]
    if method == "PUT":
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
