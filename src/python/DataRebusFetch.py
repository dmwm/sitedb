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
                                      on fn.id = fp.federations_names_id""")
    pledges = {};
    for row in c:
      id, name, country, year, cpu, disk, tape = row
      if name in pledges.keys():
        if year in pledges[name]["pledges"].keys():
          pledges[name]["pledges"][year]["cpu"]= str(cpu);
          pledges[name]["pledges"][year]["disk"]= disk;
          pledges[name]["pledges"][year]["tape"]= tape;
        else:
          pledges[name]["pledges"][year] = {"cpu" : str(cpu), "disk" :str(disk), "tape" : str(tape)};
      else:
        pledges[name] = {"country" : country, "id" : id, "pledges" : {}};
        pledges[name]["pledges"] = {year : {"cpu" : str(cpu), "disk": str(disk), "tape" : str(tape)}};
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

    # Getting topology from Rebus
    rebtopology = self._read_sites_topolygy()
    self._update_sites_assoc(rebtopology, self._current_sites(), self._current_feders())
    # Execute rebus data to single site pledges
    self._rebus_site_pledges_assoc(self.get(),self._get_fed_site_tier(),self._get_all_sites_resources())
    return []

  def _rebus_site_pledges_assoc(self,fed_resources, fed_sites, site_resources):
    """Comparing rebus pledges with single federation site pledges """
    pledges_update = []      
    for key, value in site_resources.iteritems():
      listfunc = []
      n = re.search(u'(.*)(_Disk)', key)
      if n is None:
        fed_name = ''
        site_id = ''
        for fedname, value in fed_sites.iteritems():
          if key in value['sites'].keys():
            fed_name = fedname
        if fed_name:
          if fed_sites[fed_name]['tier'] == 1:
          #for tier 1 not updating disk value if they have a Disk site
            if fed_sites[fed_name]['counter'] == 2:
            # site have disk site also!!!
              #for loop to check all federation resources;
              listfunc = self._compare_pledges(fed_name, key,1,fed_resources,site_resources)             
            else:
            # site does not have disk site!!!
              #for loop to check all federation resources;
              listfunc = self._compare_pledges(fed_name, key,0,fed_resources,site_resources) 
          else:
            listfunc = self._compare_pledges(fed_name, key,0,fed_resources,site_resources) 
      else:
        cherrypy.log("regex skipped : %s"% n.group())
      for val in listfunc:
        pledges_update.append(val)
    self._update_single_fed_site_resources(pledges_update)  

  def _update_single_fed_site_resources(self, resources):
    """Query for updating resource pledges from list, where federation have one site.
       :returns: nothing."""
    for resource in resources:
      try:
        self.api.execute("""insert into resource_pledge
                                   (pledgeid, site, pledgedate, cpu, job_slots, disk_store, tape_store, pledgequarter)
                            VALUES (resource_pledge_sq.nextval, :siteid, systimestamp, :cpu, 0, :disk, :tape, :year)
                         """, resource)
      except Exception as e:
        cherrypy.log("WARNING: failed to update pledge %s, year %s: %s"
                     %(resource['siteid'], resource['year'], str(e)))
        continue
    if resources:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _compare_pledges(self, keyfed, keysite, t1disk, fed_resources, site_resources):
    """Comparing Federation pledges and Site pledges, if year above 2014, then it is not updated."""
    pledges_update = []
    for key1 in fed_resources[keyfed]['pledges'].keys():
      if key1 in site_resources[keysite]['pledges'].keys():
        cpu_fed = str(fed_resources[keyfed]['pledges'][key1]['cpu'])
        tape_fed = str(fed_resources[keyfed]['pledges'][key1]['tape'])
        disk_fed = str(fed_resources[keyfed]['pledges'][key1]['disk'])
        #excluded tape for updating
        cpu_db = str(site_resources[keysite]['pledges'][key1]['cpu'])
        disk_db = str(site_resources[keysite]['pledges'][key1]['disk'])
        tape_db = str(site_resources[keysite]['pledges'][key1]['tape'])
        site_id = site_resources[keysite]['id']
        if t1disk == 1:
          if (not(str(cpu_fed) == str(cpu_db) and str(tape_fed) == str(tape_db))):
            pledges_update.append({'siteid': site_id, 'cpu': cpu_fed, 'tape': tape_fed, 'disk': disk_db, 'year': key1})
        else:
          if (not(str(cpu_fed) == str(cpu_db) and tape_fed == tape_db and disk_fed == disk_db)):
            pledges_update.append({'siteid': site_id, 'cpu': cpu_fed, 'tape': tape_fed, 'disk': disk_fed, 'year': key1})

    return pledges_update

  def _get_fed_site_tier(self):
    """Returns a dictionary of federation names, sites, sites counter and tier level """
    c, _ = self.api.execute("""select afn.name fed_name, afn.id fed_id, sfnm.site_id site_id, c.name alias,
                                      (select count(*) from sites_federations_names_map tmp where tmp.federations_names_id = afn.id) counter,
                                      (select pos from tier tr where s.tier = tr.id) tier
                               from all_federations_names afn
                               left outer join sites_federations_names_map sfnm on sfnm.federations_names_id = afn.id
                               left join site s on sfnm.site_id = s.id 
                                    join site_cms_name_map cmap on cmap.site_id = s.id
                                    join cms_name c on c.id = cmap.cms_name_id order by tier, counter""")
    fed_sites_list = {}
    for row in c:
      fed_name, fed_id, site_id, alias, counter, tier = row
      if counter < 2:
        if fed_name in fed_sites_list.keys():
          #add site name
          fed_sites_list[fed_name]['sites'][alias] = site_id
        else:
          # add site name and tier level
          fed_sites_list[fed_name] = {'tier': tier, 'counter': counter, 'fed_id': fed_id, 'sites': {alias: site_id}}
      else:
        if tier == 1:
        #need to skip because we have different tape sites
          if fed_name in fed_sites_list.keys():
          #add site name
            fed_sites_list[fed_name]['sites'][alias] = site_id
          else:
          # add site name and tier level
            fed_sites_list[fed_name] = {'tier': tier, 'counter': counter, 'fed_id': fed_id, 'sites': {alias: site_id}}
    return fed_sites_list

  def _get_all_sites_resources(self):
    """Return all sites pledges"""
    c, _ = self.api.execute("""select c.name alias, s.id id,
                                      rp.pledgequarter quarter,
                                      rp.cpu, rp.disk_store,
                                      rp.tape_store
                               from resource_pledge rp
                               join site s on s.id = rp.site
                               join site_cms_name_map cmap on cmap.site_id = s.id
                               join cms_name c on c.id = cmap.cms_name_id
                               order by s.name, rp.pledgedate DESC, rp.pledgequarter """)
    
    sites_resources = {}
    for row in c:
      alias, id, year, cpu, disk, tape = row
      if alias in sites_resources.keys():
        #check for year
        if year not in sites_resources[alias]['pledges'].keys(): 
          sites_resources[alias]['pledges'][year]= {'cpu': str(cpu), 'disk': disk, 'tape': tape}
      else:
        sites_resources[alias] = {'id': id, 'pledges': {year : {'cpu': str(cpu), 'disk': disk, 'tape': tape}}}
    return sites_resources

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
          pledges[name]["pledges"][year] = {"cpu" : str(cpu), "disk" : disk, "tape" : tape};
      else:
        pledges[name] = {"country" : country, "id" : id, "pledges" : {}};
        pledges[name]["pledges"] = {year : {"cpu" : str(cpu), "disk": disk, "tape" : tape}};
    return pledges

  def _current_sites(self):
    """Return current site sam.name, id, tier name information from database.
       It is required for comparing information from REBUS topology.
       :returns: dictionary of current sites in database"""
    c, _ = self.api.execute("""select s.id site_id, sam.name alias, t.name tier_name
                                      from site s
                                      join site_cms_name_map cmap on cmap.site_id = s.id
                                      join sam_cms_name_map smap on smap.cms_name_id = cmap.cms_name_id
                                      join sam_name sam on sam.id = smap.sam_id
                                      join tier t on t.id = s.tier """)
    out1 = {}
    for row in c:
      site_id, alias, tier_name = row
      if tier_name in out1.keys():
        if alias in out1[tier_name].keys():
          out1[tier_name][alias] = site_id
          # always 1 , it can`t be more
        else:
          out1[tier_name][alias] = site_id
      else:
        out1[tier_name]= {alias : site_id}
    return out1;

  def _current_feders(self):
    """Returns current federations and sites associations from database.
       It is required for comparing information from REBUS topology.
       :returns: dictionary of current federations and associations."""
    c, _ = self.api.execute("""select afn.name fed_name, afn.id fed_id, sfnm.site_id site_id
                                      from all_federations_names afn
                                      left outer join sites_federations_names_map sfnm on sfnm.federations_names_id = afn.id """)
    out = {}
    for row in c:
      fed_name, fed_id, site_id = row
      if fed_name in out.keys():
        if site_id not in out[fed_name]["sites"]:
          out[fed_name]["sites"].append(site_id);
        else:
          cherrypy.log("Something goes wrong with database, multiple sites with same id : %" % row)
      else:
        out[fed_name] = {"fed_id": fed_id, "sites": []}
        out[fed_name]["sites"].append(site_id)
    return out;

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
      except Exception as e:
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
      cpu_row=''; disk_row=''; tape_row = '';
      cpu_orc=''; disk_orc=''; tape_orc = '';
      fed_name = '';
      fed_id = 0;
      fed_year = 0;
      if 'cpu' in row.keys():
        cpu_row = str(row['cpu'])
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
              cpu_orc = str(orc_data[row['name']]['pledges'][fed_year]['cpu']);
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
      except Exception as e:
        # Ignore constraint errors for individual users instead of failing
        cherrypy.log("WARNING: failed to update pledge %s, year %s: %s"
                     %(pledge['id'], pledge['year'], str(e)))
        continue
    if pledges_update:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _insertnames(self, names_new):
    """Inserting federation name and country.
       :returns: nothing """
    for name in names_new:
      try:
        self.api.execute("""insert into all_federations_names
                            (ID, NAME, COUNTRY)
                           VALUES (all_federations_names_sq.nextval, :name, :country)
                        """, name)
      except Exception as e:
        cherrypy.log('Error : %s' %str(e))
        continue
    if names_new:
      trace = cherrypy.request.db["handle"]["trace"]
      trace and cherrypy.log("%s commit" % trace)
      cherrypy.request.db["handle"]["connection"].commit()

  def _read_sites_topolygy(self):
    """Read REBUS sites topology. Topology url: http://wlcg-rebus.cern.ch/apps/topology/all/json
       :returns: list of all topology data"""
    data = []
    url = "http://wlcg-rebus.cern.ch/apps/topology/all/json"
    req = urllib2.Request(url)
    opener = urllib2.build_opener()
    f = opener.open(req)
    topology = json.loads(f.read())
    for index, item in enumerate(topology):
      federname = item["Federation"]
      site = item["Site"]
      tier = item["Tier"];
      i = {"site" : site, "federation": federname, "tier": tier}
      data.append(i);
    return data;
  
  def _update_sites_assoc(self, rows_ins, current_sites, current_feds):
    """Comparing database and REBUS data. Preparing database update rows for site associations."""
    update = []
    for row in rows_ins:
      tier = row["tier"]
      site = row["site"]
      federation = row["federation"]
      if federation in current_feds.keys():
        fed_id = current_feds[federation]['fed_id']
        if tier in current_sites.keys():
          if site in current_sites[tier].keys():
            site_id = current_sites[tier][site];
            if site_id not in current_feds[federation]["sites"]:
              update.append({"site_id": site_id, "federations_names_id": fed_id})
    self._insert_new_assoc(update)
 
  def _insert_new_assoc(self, new_assoc):
    """New federation site association insert into database.
       :returns: nothing"""
    for new_ins_assoc in new_assoc:
      try:
        self.api.execute("""insert into sites_federations_names_map (id, site_id, federations_names_id)
      values (sites_federations_names_map_sq.nextval, :site_id, :federations_names_id)
      """, new_ins_assoc)

      except Exception as e:
        cherrypy.log('Error : %s' %str(e))
        continue
    if new_assoc:
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

      try:
        self._sync(now)
      except Exception as e:
        cherrypy.log("SYNC ERROR %s.%s REBUS sync failed %s"
                     % (getattr(e, "__module__", "__builtins__"),
                        e.__class__.__name__, str(e)))
        for line in format_exc().rstrip().split("\n"):
          cherrypy.log("  " + line)

      with self._cv:
        while not self._stopme and now < until:
          self._cv.wait(until - now)
          now = time.time()

        if self._stopme:
          return

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
          i['cpu'] = str(val1['CPU']/float(1000))
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
    elif method  == "GET":
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

