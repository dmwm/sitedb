import os, sys, time, pycurl, re, string, random, cherrypy, urllib2, ldap, collections, signal, json
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
from datetime import date

class RebusFetch(RESTEntity):
  """REST entity object for triggering synchronisation with REBUS;
  "REBUS link: http://gstat-wlcg.cern.ch/apps/pledges/resources/"
  does not provide any actual data access, just an internal mechanism
  reusing all the database logic.
  """
  def __init__(self, app, api, config, mount):
    RESTEntity.__init__(self, app, api, config, mount)
    if getattr(config, "rebusfetch", False):
      self._syncer = RebusFetchThread(app, config.rebusfetch, mount,
                           cacertdir = getattr(config, "cacertdir",
                                           "/etc/grid-security/certificates"),
                           minreq = getattr(config, "rebusfetchreq", 30),
                           interval = getattr(config, "rebusfetchtime", 300),
                           instance = getattr(config, "rebusfetchto", "test"))
    else:
      self._syncer = None

  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    authz_match(role=["Global Admin"], group=["global"])
    if method == "GET":
      if not self._syncer:
        raise cherrypy.HTTPError(503, "Not running.")

    elif method == "PUT":
      validate_strlist('name', param, safe, RX_FEDERATION)
      validate_strlist('country', param, safe, RX_FEDERATION)
      validate_strlist('year', param, safe, RX_YEARS)
      validate_strlist('cpu', param, safe, RX_NUMBER)
      validate_strlist('disk', param, safe, RX_NUMBER)
      validate_strlist('tape', param, safe, RX_NUMBER)
      validate_lengths(safe, 'name', 'country', 'year', 'cpu', 'disk', 'tape')

      authz = cherrypy.request.user
      if authz['method'] != 'Internal' or authz['login'] != self._syncer.sectoken:
        raise cherrypy.HTTPError(403, "You are not allowed to access this resource.")

  @restcall
  def get(self):
    """Get status of last full and incremental synchronisation."""
    c, _ = self.api.execute("""select fn.id id, fn.name name, fn.country country,
                                      fp.year year, fp.cpu cpu, fp.disk disk, fp.tape tape
                                      from all_federations_names fn
                                      left join federations_pledges fp
                                      on fn.id = fp.all_federations_names_id""")
    pledges = {};
    for row in c:
      id, name, country, year, cpu, disk, tape = row
      if name in pledges.keys():
        if year in pledges[name]["pledges"].keys():
          pledges[name]["pledges"][year]["cpu"]= cpu;
          pledges[name]["pledges"][year]["disk"]= disk;
          pledges[name]["pledges"][year]["tape"]= tape;
        else:
          pledges[name]["pledges"][year] = {"cpu" : cpu, "disk" : disk, "tape" : tape};
      else:
        pledges[name] = {"country" : country, "id" : id, "pledges" : {}};
        pledges[name]["pledges"] = {year : {"cpu" : cpu, "disk": disk, "tape" : tape}};
    return pledges

  @restcall
  def put(self, name, country, year, cpu, disk, tape):
    """Perform bindmap for data.
    :arg list name: federation name.
    :arg list country: federation country.
    :arg list year: corresponding year.
    :arg list cpu: cpu value.
    :arg list disk: disk value.
    :arg list tape: tape value.
    :returns: nothing."""
    rebrows = self.api.bindmap(name=name, country=country, year=year, cpu=cpu, disk=disk, tape=tape)
    self._update(self._current(), rebrows)
    self._update_resources()
    return []

  def _current(self):
    """Return the current federations pledges information from the database.
       :returns: dictionary of current federations pledges in database."""
    c, _ = self.api.execute("""select fn.id id, fn.name name, fn.country country,
                                      fp.year year, fp.cpu cpu, fp.disk disk, fp.tape tape
                                      from all_federations_names fn
                                      left join federations_pledges fp
                                      on fn.id = fp.federations_names_id""")
    pledges = {};
    for row in c:
      id, name, country, year, cpu, disk, tape = row
      if name in pledges.keys():
        if year in pledges[name]["pledges"].keys():
          pledges[name]["pledges"][year]["cpu"]= cpu;
          pledges[name]["pledges"][year]["disk"]= disk;
          pledges[name]["pledges"][year]["tape"]= tape;
        else:
          pledges[name]["pledges"][year] = {"cpu" : cpu, "disk" : disk, "tape" : tape};
      else:
        pledges[name] = {"country" : country, "id" : id, "pledges" : {}};
        pledges[name]["pledges"] = {year : {"cpu" : cpu, "disk": disk, "tape" : tape}};
    return pledges

  def tryToInt(self, value):
    """String to int parser.
       :returns: Parsed value or 0"""
    temp_int = 0
    try:
      temp_int = int(value)
    except ValueError:
      temp_int = 0
    return temp_int

  def _get_current_resources(self):
    """Get current resource pledges from the database.
       :returns: dict of resource pledges"""
    c, _ = self.api.execute("""select site, pledgequarter from resource_pledge""")
    resources = {};
    for row in c:
      site, pledgequarter = row
      if site in resources:
        resources[site].append(pledgequarter)
      else:
        resources[site] = [pledgequarter]
    return resources;

  def _update_resources(self):
    """Update resource pledges where is null. After implementation of federation pledges
       and removing 4 quarters per year this is required to be able to show on site.
       :returns: nothing."""
    resources = self._get_current_resources()
    year_next = date.today().year + 2
    resources_new = []
    for site in resources.keys():
      min_year = min(resources[site])
      for years in range(min_year, year_next):
        if years not in resources[site]:
          resources_new.append({'site': site, 'pledgequarter': years})
    self._update_resources_sql(resources_new)

  def _update_resources_sql(self, resources):
    """Query for updating resource pledges from list, where site pledges is null.
       :returns: nothing."""
    for resource in resources:
      try:
        self.api.execute("""insert into resource_pledge
                                   (pledgeid, site, pledgedate, cpu, job_slots, disk_store, tape_store, pledgequarter)
                            VALUES (resource_pledge_sq.nextval, :site, systimestamp, 0, 0, 0, 0, :pledgequarter)
                         """, resource)
      except Exception, e:
        cherrypy.log("WARNING: failed to update pledge %s, year %s: %s"
                     %(resource['site'], resource['pledgequarter'], str(e)))
        continue
    if resources:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _update(self, orc_data, data_ins):
    """Comparing database output and wlcg rebus fetch data. Preparing update list
       which rows are not in database.
       :returns: nothing"""
    names_update = {};
    names_new = [];
    for row in data_ins:
      if 'name' in row.keys():
        if row['name'] not in orc_data.keys():
          if row['name'] not in names_update.keys():
            names_update[row['name']]= {'country': row['country']}
            names_new.append({'name': row['name'], 'country' : row['country']})
    if names_new:
      self._insertnames(names_new)
      orc_data = self._current();
    pledges_update = []
    for row in data_ins:
      cpu_row=0; disk_row=0; tape_row = 0;
      cpu_orc=0; disk_orc=0; tape_orc = 0;
      fed_name = '';
      fed_id = 0;
      fed_year = 0;
      if 'cpu' in row.keys():
        cpu_row = self.tryToInt(row['cpu'])
      if 'disk' in row.keys():
        disk_row = self.tryToInt(row['disk'])
      if 'tape' in row.keys():
        tape_row = self.tryToInt(row['tape'])
      if 'name' in row.keys():
        fed_name = row['name']
        if fed_name in orc_data.keys():
          fed_id = orc_data[fed_name]['id']
          if 'year' in row.keys():
            fed_year = self.tryToInt(row['year']);
            if fed_year in orc_data[row['name']]['pledges'].keys():
              cpu_orc = self.tryToInt(orc_data[row['name']]['pledges'][fed_year]['cpu']);
              disk_orc = self.tryToInt(orc_data[row['name']]['pledges'][fed_year]['disk']);
              tape_orc = self.tryToInt(orc_data[row['name']]['pledges'][fed_year]['tape']);
              if (not(cpu_orc == cpu_row and tape_orc == tape_row and disk_orc == disk_row)):
                pledges_update.append({'id': fed_id, 'year': fed_year, 'cpu': cpu_row, 'disk': disk_row, 'tape': tape_row})
            else:
              pledges_update.append({'id': fed_id, 'year': fed_year, 'cpu': cpu_row, 'disk': disk_row, 'tape': tape_row})
          else:
            cherrypy.log('Year Error in row: %s ' % row)
        else:
          cherrypy.log('Name Error in row: %s' % row)
    if pledges_update:
      self._insertpledges(pledges_update)

  def _insertpledges(self, pledges_update):
    """Inserting prepared update list to database. System timestamp allows
       to see difference between changed data. All updates and inserts ar recorded.
       :returns: nothing"""
    for pledge in pledges_update:
      try:
        self.api.execute("""Insert into federations_pledges
                                    (id, federations_names_id, year, cpu, disk, tape, feddate)
                              values (federations_pledges_sq.nextval, :id, :year, :cpu, :disk, :tape, systimestamp)
                               """, pledge)
      except Exception, e:
        # Ignore constraint errors for individual users instead of failing
        cherrypy.log("WARNING: failed to update pledge %s, year %s: %s"
                     %(pledge['id'], pledge['year'], str(e)))
        continue
    if pledges_update:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _insertnames(self, names_new):
    """Inserting federation name and country
       :returns: nothing """
    for name in names_new:
      try:
        self.api.execute("""insert into all_federations_names
                            (ID, NAME, COUNTRY)
                           VALUES (all_federations_names_sq.nextval, :name, :country)
                        """, name)
      except Exception, e:
        cherrypy.log('Error : %s' %str(e))
        continue
    if names_new:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

class RebusFetchThread(Thread):
  """A task thread to synchronise federation pledges from REBUS. This runs on
  a single node only in the cluster."""

  _baseurl = "http://gstat-wlcg.cern.ch/apps/pledges/resources/"
  _ident = "SiteDB/%s Python/%s" % \
           (os.environ["SITEDB_VERSION"], ".".join(map(str, sys.version_info[:3])))

  def __init__(self, app, baseurl, mount, cacertdir = "/etc/grid-security/certificates", minreq = 1000, interval = 300, instance = "test"):
    Thread.__init__(self, name = "RebusFetch")
    self.sectoken = "".join(random.sample(string.letters, 30))
    self._inturl = "http://localhost:%d%s/%s/rebusfetch" % \
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
    synchronisation with REBUS."""
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
        cherrypy.log("SYNC ERROR %s.%s REBUS sync failed %s"
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
      cherrypy.log("WARNING: REBUS data failed validation: '%s'" % input)
      self._warnings[input] = now
    return None

  def _sync(self, now):
    """Perform full synchronisation."""

    # Delete warnings older than 24 hours
    for k, v in self._warnings.items():
      if v < now - 86400:
        del self._warnings[k]
    result = []
    # Get the user information from CERN/LDAP
    ldresult = self._ldget(self._baseurl)
    # get data from oracle database
    # Process each user record returned
    rows = []
    id = 0;

    for name, values in ldresult.iteritems():
      for year, val1 in values["pledges"].iteritems():
        i = { 'name' : name, 'country' : values["country"], 'year' : str(year), 'cpu' : str(0), 'disk' : str(0), 'tape' : str(0)}
        if 'CPU' in val1.keys():
          i['cpu'] = str(val1['CPU'])
        if 'Disk' in val1.keys():
          i['disk'] = str(val1['Disk'])
        if 'Tape' in val1.keys():
          i['tape'] = str(val1['Tape'])
        rows.append(i);
    gett = self._intreq.put(("PUT", rows, result))
    gettt = self._intreq.process()

  def _ldget(self, url):
    """Get data from REBUS."""
    year_next = date.today().year + 2
    result = self._read_rebus_data(2008, year_next);
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
    if method == "PUT":
      type, body = self._encode(rows)
      headers = self._headers[:] + [("Content-Type", type),
                                    ("Content-Length", str(len(body)))]
      c.setopt(pycurl.POST, 0)
      c.setopt(pycurl.UPLOAD, 1)
      c.setopt(pycurl.URL, self._inturl)
      c.setopt(pycurl.HTTPHEADER, ["%s: %s" % h for h in headers])
      c.setopt(pycurl.READFUNCTION, StringIO(body).read)
      c.result = result
    else:
      if method  == "GET":
        headers = self._headers[:]
        c.setopt(pycurl.URL, self._inturl)
        c.setopt(pycurl.HTTPHEADER, ["%s: %s" % h for h in headers])
        c.result = result
      else:
        assert False, "Unsupported method"

  def _encode(self, rows):
    """Encode dictionaries in `rows` for POST/PUT body as a HTML form."""
    body, sep = "", ""
    for obj in rows:
      for key, value in obj.iteritems():
        body += "%s%s=%s" % (sep, key, urllib2.quote(value.encode("utf-8")))
        sep = "&"
    return ("application/x-www-form-urlencoded", body)

  def _read_rebus_data(self, year, yearTo):
    """REBUS json data fetch from 2008 to year.now + 2. All data returned in dictionary."""
    data = {};
    for x in range(year, yearTo):
      url = "http://wlcg-rebus.cern.ch/apps/pledges/resources/"+str(x)+"/all/json";
      req = urllib2.Request(url)
      opener = urllib2.build_opener()
      f = opener.open(req)
      pledges = json.loads(f.read())
      for index, item in enumerate(pledges):
        federname = item["Federation"];
        cms = item["CMS"];
        pledgetype = item["PledgeType"];
        country = item["Country"];
        if cms and pledgetype:
          if federname in data.keys():
            if x in data[federname]["pledges"].keys():
              data[federname]["pledges"][x][pledgetype]= cms;
            else:
              data[federname]["pledges"][x] = {pledgetype : cms};
          else:
            data[federname] = {"country" : country, "pledges" : {}};
            data[federname]["pledges"] = {x : {pledgetype : cms}};
    return data;
