var State = function(Y, gui, instance)
{
  /** Myself. */
  var _self = this;

  /** Validity flag: force reload from data server. */
  var _RELOAD = -1;

  /** Validity flag: soft reload, let browser decide whether to reload. */
  var _INVALID = 0;

  /** Validity flag: data is present and valid. */
  var _VALID = 1;

  /** Known state items. */
  var _ITEMS = [
    "whoami", "roles", "groups", "people", "sites", "site-names",
    "site-resources", "site-associations", "resource-pledges",
    "pinned-software", "site-responsibilities", "group-responsibilities",
    "federations", "federations-sites",
    "federations-pledges", "esp-credit"];

  /** Pending XHR requests. */
  var _pending = {};

  /** The current database instance. */
  var _instance = instance;

  /** Item descriptions and their raw data. */
  var _data = {};

  /** Scheduled call to refresh view with data retrieved so far. */
  var _viewUpdateTO = null;

  /** Flag indicating whether data currently present is complete. */
  this.complete = false;

  /** Current site data organised by the tier label. */
  this.sitesByTier = {};

  /** Current site data organised by the canonical site name. */
  this.sitesByName = {};

  /** Current site data organised by the CMS site name. */
  this.sitesByCMS = {};

  /** Current people data organised by CERN account. */
  this.peopleByAcc = {};

  /** Current people data as a flat list. */
  this.people = [];

  /** Current roles by role title. */
  this.rolesByTitle = {};

  /** Current groups by group name. */
  this.groupsByName = {};

  /** Current federations by id. */
  this.federationsById = {};
  this.federationsBYID = {};
  /** Current federations sites */
  this.federationsSites = {};

  /** Current federations sites by id */
  this.federationsSitesById = {};

  /** Current sites by federation */
  this.federationsByAlias = {};

  /** Current available federation names in wlcg */
  this.federationsNames = {};

  /** Current Federation pledges */
  this.federationsPledges = {};

  /** Current ESP Credits */
  this.espcredit = {};

  /** Return server data URL for resource @a name. */
  var _url = function(name)
  {
    return REST_SERVER_ROOT + "/data/" + _instance + "/" + name;
  };

  /** Sort people into ascending order by surname, forename or e-mail. */
  this.sortPerson = function(a, b)
  {
    return d3.ascending(a.surname, b.surname)
           || d3.ascending(a.forename, b.forename)
           || d3.ascending(a.email, b.email);
  };

  /** Sort objects into ascending order by name. */
  this.sortName = function(a, b)
  {
    return d3.ascending(a.name, b.name);
  };

  /** Sort sites into ascending order by canonical name. */
  this.sortSite = function(a, b)
  {
    return d3.ascending(a.canonical_name, b.canonical_name);
  };
  this.sortFederations = function(a, b)
  {
    return d3.ascending(a.id, b.id);
  };

  /** Rebuild high-level data from the raw information. */
  var _rebuild = function()
  {
    var whoami = null;
    var people = [], byacc = {};
    var roles = {}, groups = {};
    var tiers = {}, byname = {}, bycms = {};
    var federations = [], federationsbysites = [];
    var fedSitesByID = {};var federations1 = {};
    var federationsnames = [];
    var federationsbysitealias = {};
    var federationspledges = [];
    var espcredits={};

    // ESP Credits
       Y.each(_data['esp-credit'].value || [], function(i) {
     var ss = { esp_values: {}};
     if (! (i.site in espcredits))
     espcredits[i.site] = Y.merge(ss);
     var credit = espcredits[i.site].esp_values;
     if (! (i.year in credit))
       {credit[i.year] = {};
        credit[i.year] = {esp_credit: i.esp_credit};
        }
    });
    // Federations.
    Y.each(_data['federations'].value || [], function(i) {
    var s = i.name.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    var canon = {canonical_name : s};
    var r = Y.merge(canon, i);
    federations.push(r);
    federationsnames.push(i);
    var ii = federations1[i.id] = i;
    });
    // Federations Sites.
    Y.each(_data['federations-sites'].value || [], function(i) {
     federationsbysites.push(i);
     if(i.fed_id in Object.keys(federations1)){
     federationsbysitealias[i.alias] = Y.merge({feder_name: federations1[i.fed_id].name} ,i);
     }
     else federationsbysitealias[i.alias] = Y.merge({feder_name: ''} ,i);
     var r = fedSitesByID[i.site_id] = Y.merge(i);
     });
    // Federations Pledges.
    Y.each(_data['federations-pledges'].value || [], function(i) {
     var ss = {country: i.country, pledges: {}, history_pledges: {}};
     if (! (i.name in federationspledges))
     var s = federationspledges[i.name] = Y.merge(ss);
     var pled = federationspledges[i.name].pledges;
     var pled_his = federationspledges[i.name].history_pledges;
     if (! (i.year in pled))
       {pled[i.year] = {};
        pled[i.year] = {cpu: i.cpu, disk : i.disk, tape: i.tape, timestamp: i.feddate};
        }
     else{
	  if(pled[i.year]['timestamp'] < i.feddate)
             pled[i.year] = {cpu: i.cpu, disk : i.disk, tape: i.tape, timestamp: i.feddate};
         }
     if (! (i.year in pled_his))
        pled_his[i.year] = [];
     pled_his[i.year].push({cpu: i.cpu, disk: i.disk, tape: i.tape, timestamp: i.feddate});
    });
    // Roles and groups.
    Y.each(_data['roles'].value || [], function(i) {
      var r = roles[i.title] = Y.merge({ members: [], site: {}, group: {} }, i);
      r.canonical_name = i.title.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    });

    Y.each(_data['groups'].value || [], function(i) {
      var g = groups[i.name] = Y.merge({ members: [] }, i);
      g.canonical_name = g.name.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    });

    // Who-am-I information.
    if (_data['whoami'].value && _data['whoami'].value.length == 1)
      whoami = Y.merge({ person: null }, _data['whoami'].value[0]);

    // People records.
    Y.each(_data['people'].value || [], function(i) {
      var p = Y.merge({ fullname: i.email, roles: {}, sites: {}, groups: {} }, i);
      if (p.im_handle)
        p.im_handle = p.im_handle.replace(/^none(:none)*$/gi, "");
      if (p.surname)
	p.fullname = p.forename + " " + p.surname;
      if (whoami && whoami.login && p.username == whoami.login)
	whoami.person = p;
      byacc[p.username] = p;
      people.push(p);
    });

    // Basic site records.
    Y.each(_data['sites'].value || [], function(i) {
      var site = { cc: null, canonical_name: i.site_name, name_alias: {},
                   resources: { CE: [], SE: [] },
                   child_sites: [], parent_site: null,
                   resource_pledges: {}, pinned_software: {}, history_resource_pledges: {},
                   responsibilities: {}
                   };
      site = Y.merge(site, i);
      var tier = tiers[i.tier];
      if (! tier)
        tier = tiers[i.tier] = [];
      tier.push(site);
      byname[i.site_name] = site;
    });

    // Site name aliases.
    Y.each(_data['site-names'].value || [], function(i) {
      if (i.site_name in byname)
      {
        var site = byname[i.site_name];
	if (! (i.type in site.name_alias))
	  site.name_alias[i.type] = [];
        site.name_alias[i.type].push(i.alias);
        if (i.type == "cms" && site.canonical_name == site.site_name)
        {
          site.cc = i.alias.replace(/^T\d+_([A-Z][A-Z])_.*/, "$1").toLowerCase();
          site.canonical_name = i.alias;
          bycms[i.alias] = site;
        }
      }
    });

    // Site resources (CE, SE).
    Y.each(_data['site-resources'].value || [], function(i) {
      if (i.site_name in byname)
      {
        var res = byname[i.site_name].resources;
        if (! (i.type in res))
	  res[i.type] = [];
        res[i.type].push(i);
      }
    });

    // Site parent/child associations.
    Y.each(_data['site-associations'].value || [], function(i) {
      if (i.parent_site in byname && i.child_site in byname)
      {
        var parent = byname[i.parent_site];
        var child = byname[i.child_site];
        parent.child_sites.push(child);
        child.parent_site = parent;
      }
    });

    // Site resource pledges; keep only the most recent one per quarter.
    Y.each(_data['resource-pledges'].value || [], function(i) {
      if (i.site_name in byname)
      {
        var pledges = byname[i.site_name].resource_pledges;
        var hist_pledges = byname[i.site_name].history_resource_pledges;
        if (! (i.quarter in pledges))
            pledges[i.quarter] = i;
        if (! (i.quarter in hist_pledges))
          hist_pledges[i.quarter] = [];
        hist_pledges[i.quarter].push(i);
      }
    });
    // Pinned software.
    Y.each(_data['pinned-software'].value || [], function(i) {
      if (i.site_name in byname)
      {
        var pins = byname[i.site_name].pinned_software;
        if (! (i.ce in pins))
	  pins[i.ce] = [];
	pins[i.ce].push(i);
      }
    });

    // Site responsibilities; associates site, role and person.
    Y.each(_data['site-responsibilities'].value || [], function(i) {
      if (i.site_name in byname && i.username in byacc && i.role in roles)
      {
        var site = byname[i.site_name];
	var role = roles[i.role];
        var person = byacc[i.username];

        var r = site.responsibilities;
        if (! (i.role in r))
	  r[i.role] = [];
	r[i.role].push(person);

        r = person.roles;
        if (! (i.role in r))
	  r[i.role] = { site: [], group: [] };
	r[i.role].site.push(site);

	if (! (i.site_name in role.site))
          role.site[i.site_name] = [];
        role.site[i.site_name].push(person);
      }
    });

    // Group responsibilities; associates group, role and person.
    Y.each(_data['group-responsibilities'].value || [], function(i) {
      if (i.user_group in groups && i.username in byacc && i.role in roles)
      {
        var group = groups[i.user_group];
	var role = roles[i.role];
        var person = byacc[i.username];

        group.members.push(person);

        r = person.roles;
        if (! (i.role in r))
	  r[i.role] = { site: [], group: [] };
	r[i.role].group.push(group);

	if (! (i.user_group in role.group))
          role.group[i.user_group] = [];
        role.group[i.user_group].push(person);
      }
    });

    // All data processed, now sort regularly used data structures.
    // Put various site and people names into reasonably natural order.
    people.sort(_self.sortPerson);
    Y.each(roles, function(role) {
      var members = {};
      Y.each(role.site, function(v) {
        Y.each(v, function(p) { members[p.username] = p; });
        v.sort(_self.sortSite);
      });
      Y.each(role.group, function(v) {
        Y.each(v, function(p) { members[p.username] = p; });
        v.sort(_self.sortPerson);
      });
      role.members = Y.Object.values(members);
      role.members.sort(_self.sortPerson);
    });

    Y.each(groups, function(group) {
      var members = {};
      Y.each(group.members, function(p) { members[p.username] = p; });
      group.members = Y.Object.values(members);
      group.members.sort(_self.sortPerson);
    });

    Y.each(byacc, function(person) {
      Y.each(person.roles, function(v) {
        v.site.sort(_self.sortSite);
        v.group.sort(_self.sortName);
        Y.each(v.site, function(s) { person.sites[s.canonical_name] = s; });
        Y.each(v.group, function(g) { person.groups[g.name] = g; });
      });
    });

    Y.each(tiers, function(sites) {
      sites.sort(_self.sortSite);
      Y.each(sites, function(s) {
        Y.each(s.responsibilities, function(v) { v.sort(_self.sortPerson); });
        Y.each(s.name_alias, function(v) { v.sort(d3.ascending); });
        s.child_sites.sort(_self.sortSite);

        Y.each(s.resources, function(v) {
          v.sort(function(a, b) { return d3.ascending(a.fqdn, b.fqdn); });
        });

        Y.each(s.pinned_software, function(v) {
          v.sort(function(a, b) {
            return d3.descending(a.arch, b.arch)
                   || d3.descending(a.release, b.release); });
        });
      });
    });

//   federations.sort(_self.sortFederations);

    _self.sitesByTier = tiers;
    _self.sitesByName = byname;
    _self.sitesByCMS = bycms;
    _self.people = people;
    _self.peopleByAcc = byacc;
    _self.rolesByTitle = roles;
    _self.groupsByName = groups;
    _self.whoami = whoami;
    _self.espcredit = espcredits;
    _self.federationsById = federations;
    _self.federationsBYID = federations1;
    _self.federationsSites= federationsbysites;
    _self.federationsSitesById = fedSitesByID;
    _self.federationsNames = federationsnames;
    _self.federationsPledges = federationspledges;
    _self.federationsByAlias = federationsbysitealias;

  };

  /** Final handler for state update. Rebuilds high-level data and calls
      the GUI view update. */
  var _rebuildAndUpdate = function()
  {
    _rebuild();
    gui.update.call(gui);
    _viewUpdateTO = null;
  };

  /** Complete fetching the request @a i. Marks the object valid and removes
      the XHR pending object for it. Marks state complete if no more data is
      pending download. Calls _rebuildAndUpdate if state has become complete,
      otherwise schedules the call if no further updates arrive within 500 ms. */
  var _complete = function(i)
  {
    i.obj.node.setAttribute("class", "valid");
    i.obj.valid = _VALID;
    delete _pending[i.name];

    _self.complete = true;
    for (var name in _data)
      if (_data[name].valid != _VALID || name in _pending)
        _self.complete = false;

    if (_self.complete)
      _rebuildAndUpdate();
    else if (! _viewUpdateTO)
      _viewUpdateTO = Y.later(500, _self, _rebuildAndUpdate);
  };

  /** Utility function to abort all pending GET requests. */
  var _abort = function()
  {
    for (var p in _pending)
      _pending[p].abort();
    _pending = {};
  };

  /** Report a data server interaction error. */
  var _error = function(file, line, category, message)
  {
    _abort();
    for (var name in _data)
      _data[name].valid = _RELOAD;

    gui.errorReport(10000, file, line, "state", category, message, true);
  };

  /** Handle successfully retrieved data. */
  var _success = function(id, o, i)
  {
    var hash = Y.Array.hash;

    try
    {
      var ctype = o.getResponseHeader("Content-Type");
      if (o.status == 304)
      {
        _complete(i);
      }
      else if (o.status != 200)
      {
        i.obj.node.setAttribute("class", "invalid");
        _error("(state)", 0, "bad-status", "Internal error retrieving '"
               + Y.Escape.html(i.name)
               + "': success handler called with status code " + o.status
               + " != 200 ('" + Y.Escape.html(o.statusText) + "')");
      }
      else if (ctype != "application/json")
      {
        i.obj.node.setAttribute("class", "invalid");
        _error("(state)", 0, "bad-ctype", "Internal error retrieving '"
               + Y.Escape.html(i.name)
               + "': expected 'application/json' reply, got '"
               + Y.Escape.html(ctype) + "'");
      }
      else
      {
        var val = Y.JSON.parse(o.responseText);
        if (val.result && val.desc && val.desc.columns)
        {
          i.obj.value = val.result.map(function(e) {
            return hash(val.desc.columns, e); });
          _complete(i);
        }
        else if (val.result)
        {
          i.obj.value = val.result;
          _complete(i);
        }
        else
        {
          i.obj.node.setAttribute("class", "error");
          _error("(state)", 0, "bad-json", "Internal error retrieving '"
                 + Y.Escape.html(i.name) + "': failed to parse json result");
        }
      }
    }
    catch (err)
    {
      i.obj.node.setAttribute("class", "error");

      var fileName = (err.fileName ? err.fileName.replace(/.*\//, "") : "(unknown)");
      var lineNumber = (err.lineNumber ? err.lineNumber : 0);
      var fileLoc = Y.Escape.html(fileName) + lineNumber;
      _error(fileName, lineNumber, "exception", "An exception '"
             + Y.Escape.html(err.name) + "' was raised during page update: "
             + Y.Escape.html(err.message));
    }
  };

  /** Handle failure to retrieve data from the server. */
  var _failure = function(id, o, i)
  {
    if (o.status === 0 && o.statusText == "abort")
      return;

    _error("(state)", 0, "comm-error", "Communication failure with the SiteDB"
           + " server: " + Y.Escape.html(o.statusText) + " (HTTP status "
           + o.status + ") while retrieving '" + Y.Escape.html(i.name) + "'");
  };

  /** Issue a server request for @a name and @a obj in @a state. */
  var _refresh = function(name, obj, state)
  {
    // Mark state incomplete.
    _self.complete = false;

    // Mark object invalid if previously valid, but don't undo forced reload.
    // The caller will use _RELOAD or _INVALID as state as appropriate.
    if (obj.valid > state)
      obj.valid = state;

    // If there's already pending operation to load it, cancel it. Callers
    // are smart enough to avoid this in case they don't want this behaviour.
    if (name in _pending)
    {
      _pending[name].abort();
      delete _pending[name];
    }

    // Mark the object in pending state in debug display.
    obj.node.setAttribute("class", "pending");

    // Set request headers. We always add the 'Accept' header. We also add
    // 'Cache-Control' header if we want to force redownload. Note that the
    // browser will automatically add 'If-None-Match' header if it has an
    // existing but out-of-date object with 'ETag' header.
    //
    // Note that the browser will happily return data to us from its cache
    // as long as it's within the expire time limits, without checking with
    // the server (= without doing a conditional GET). This is what we want,
    // and we force reload when we know we want to avoid stale data. We end
    // up here forcing reload on a) the first page load, b) whenever switching
    // instances. The expire limits on SiteDB objects are short enough that
    // this is precisely the behaviour we want.
    var headers = { "Accept": "application/json" };
    if (obj.valid == _RELOAD)
      headers["Cache-Control"] = "max-age=0, must-revalidate";

    // Start XHR I/O on this object.
    _pending[name] = Y.io(_url(name),
                          { on: { success: _success, failure: _failure },
                            context: this, method: "GET", sync: false,
                            timeout: null, arguments: { obj: obj, name: name },
                            headers: headers });
  };

  /** Check if the user has @a role in @a group. */
  this.hasGroupRole = function(role, group)
  {
    var roles = _self.whoami && _self.whoami.roles;
    role = role.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    group = group.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    if (roles && role in roles)
    {
      var groups = roles[role]["group"];
      for (var i = 0; i < groups.length; ++i)
	if (groups[i] == group)
	  return true;
    }

    return false;
  };

  /** Check if the user has @a role for @a site. */
  this.hasSiteRole = function(role, site)
  {
    var roles = _self.whoami && _self.whoami.roles;
    role = role.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    site = site.toLowerCase().replace(/[^a-z0-9]+/gi, "-");
    if (roles && role in roles)
    {
      var sites = roles[role]["site"];
      for (var i = 0; i < sites.length; ++i)
	if (sites[i] == site)
	  return true;
    }

    return false;
  };

  /** Check if the user is a global admin. */
  this.isGlobalAdmin = function()
  {
    return _self.hasGroupRole("global-admin", "global");
  };

  /** Check if the user is a sitedb operator. */
  this.isSitedbOperator = function()
  {
    return _self.hasGroupRole("operator","sitedb");
  };

  /** Require list of state elements to be loaded. Refreshes those that
      are out of date and not currently pending load. */
  this.require = function()
  {
    for (var i = 0; i < arguments.length; ++i)
    {
      var name = arguments[i];
      var pending = (name in _pending);
      var obj = _data[name];
      if (obj.valid != _VALID && ! pending)
        _refresh(name, obj, _INVALID);
    }

    return _self;
  };

  /** Require all state items. */
  this.requireall = function()
  {
    return _self.require.apply(_self, _ITEMS);
  };

  /** Invalidate all state items so they will be retrieved again on the
      next 'require()'. Does not force them to be redownloaded from the
      server, but will ask browser to get the data again. This allows the
      browser to check with the server for updates on expired data. */
  this.invalidate = function()
  {
    for (var name in _data)
    {
      var obj = _data[name];
      obj.node.setAttribute("class", "");
      obj.valid = _INVALID;
    }

    return _self;
  };

  /** Force the provided list of state elements to refresh immediately. */
  this.refresh = function()
  {
    for (var i = 0; i < arguments.length; ++i)
    {
      var name = arguments[i];
      var obj = _data[name];
      _refresh(name, obj, _RELOAD);
    }
  };

  /** Run a set of update operations. Each operation can have attributes:
       - method: Required, HTTP method to use: POST/PUT/DELETE
       - entity: Required, REST entity to operate on
       - data: Required, dictionary of form parameters to submit
       - message: Required, message to show while operation is going on
       - invalidate: Optional, list of other entities to invalidate
       - onsuccess: Optional, callback to invoke on success.

     The method puts up a modal panel with a "Stop" button to terminate
     the action, then starts processing each HTTP request. For each one
     the panel message is updated with op.message, and operation issued.
     The 'onsuccess' callback, if any, is invoked if the operation succeeds.
     After all operations have been successfully completed, the panel is
     removed and all the invalidated entities are forced to reload.

     If an operation fails or the user requests operation to stop, the panel
     will be updated with the error info and all further processing stopped,
     and all entities forced to reload from the server.

     Note that this method starts an asynchronous operation and returns
     before the operations even start running. Make sure all response to
     successful / failed operation is handled in callbacks, not on return
     of this call! */
  this.modify = function(updates)
  {
    var panel, req, aborted = false, cur = -1, u, invalid = {};
    var _err, _stop, _ok, _fail, _exec, _next, _last;
    var io = new Y.IO({ emitFacade: true });

    // Handle errors. This is like _error(), but reports into the modal
    // panel, not the message overlay area.
    _err = function(category, message, id)
    {
      _abort();
      for (var name in _data)
        _data[name].valid = _RELOAD;

      if (id) message += "; server error id: " + id;
      panel.set("bodyContent",
                gui.errorReport(0, "(modify)", 0, "state",
                                category, message, false));
      panel.set("buttons",
                [{ value: "Close", section: Y.WidgetStdMod.FOOTER,
                   action: function(e) { e.preventDefault(); panel.hide(); }}]);
      panel.render();
    };

    // Respond to "Stop" button clicks. Abort any pending XHR request
    // and hide the panel. The XHR event handler will do the rest.
    _stop = function(e)
    {
      e.preventDefault();
      if (req) req.abort();
      panel.hide();
    };

    // Respond to successful XHR requests, much like _success() does for
    // GET requests. If the request completed truly successfully recurse
    // to process the next update request, or if there is none, finish
    // things off. Note the mutual recursion with _next/_exec() as we
    // cannot run things in a loop because everything is asynchronous.
    _ok = function(e)
    {
      try
      {
        var o = e.data;
        var ctype = o.getResponseHeader("Content-Type");
        if (o.status != 200)
        {
          if (u.entity in _data)
            _data[u.entity].node.setAttribute("class", "invalid");
          _err("bad-status", "Internal error while issuing "
               + Y.Escape.html(u.method) + " to '" + Y.Escape.html(u.entity)
               + "': success handler called with status code " + o.status
               + " != 200 ('" + Y.Escape.html(o.statusText) + "')",
               o.getResponseHeader("X-Error-ID"));
          _last();
        }
        else if (ctype != "application/json")
        {
          if (u.entity in _data)
            _data[u.entity].node.setAttribute("class", "invalid");
          _err("bad-status", "Internal error while issuing "
               + Y.Escape.html(u.method) + " to '" + Y.Escape.html(u.entity)
               + "': expected 'application/json' reply, got '"
               + Y.Escape.html(ctype) + "'");
          _last();
        }
        else
        {
          if (u.onsuccess)
            u.onsuccess();
          _next();
        }
      }
      catch(err)
      {
        if (u.entity in _data)
          _data[u.entity].node.setAttribute("class", "error");
        var fileName = (err.fileName ? err.fileName.replace(/.*\//, "") : "(unknown)");
        var lineNumber = (err.lineNumber ? err.lineNumber : 0);
        var fileLoc = Y.Escape.html(fileName) + lineNumber;
        _error(fileName, lineNumber, "exception", "An exception '"
               + Y.Escape.html(err.name) + "' was raised during state modify: "
               + Y.Escape.html(err.message));
        _last();
      }
    };

    // Respond to failures in XHR requests, much like _failure() does for
    // GET requests. Try our best to produce somewhat useful error message
    // into the panel, including any server-provided error info if any.
    //
    // If the failure was simply 'abort' don't report errors but force
    // everything to reload. Otherwise update the panel with the error
    // message, force everything to reload, and quit processing more.
    //
    // Note that this returns out of the 'modify' chain and page will get
    // update notifications underneath, but the user needs to click on
    // "Close" to interact with the page. This is so the error does not
    // get lost, as it would if we used the transient message overlay.
    _fail = function(e)
    {
      var o = e.data, appcode = 0, detail = null, errinfo = null, errid = null;
      try
      {
        appcode = o.getResponseHeader("X-Rest-Status");
        detail  = o.getResponseHeader("X-Error-Detail");
        errinfo = o.getResponseHeader("X-Error-Info");
        errid   = o.getResponseHeader("X-Error-ID");
        appcode = appcode && parseInt(appcode);
      }
      catch (_)
      {
        // Ignore errors.
      }

      if (! detail)
        detail = "SiteDB server responded " + Y.Escape.html(o.statusText)
                 + " (HTTP status " + o.status + ")";

      if (errinfo)
        detail += ": " + errinfo;

      if (appcode)
        detail += ", server error code " + appcode;

      detail += " while issuing " + Y.Escape.html(u.method)
                + " to '" + Y.Escape.html(u.entity) + "'";

      if (u.entity in _data)
        _data[u.entity].node.setAttribute("class", "invalid");

      if (o.status == 0 && o.statusText == "abort")
        for (var name in _data)
          _data[name].valid = _RELOAD;
      else if (appcode)
        _err("app-fail", detail, errid);
      else if (o.status == 403)
        _err("permission", "Permission denied. " + detail, errid);
      else if (o.status == 400)
        _err("data-fail", "Invalid data. " + detail, errid);
      else if (o.status == 500)
        _err("exec-fail", "Operation failed. " + detail, errid);
      else if (o.status == 503 || o.status == 504)
        _err("unavailable", "Service unavailable. " + detail, errid);
      else
        _err("comm-error", "Communication failure. " + detail, errid);

      _last();
    };

    // Start executing the current operation in 'updates'.
    _exec = function()
    {
      u = updates[cur];
      if (u.entity in _data)
      {
        invalid[u.entity] = 1;
        _data[u.entity].node.setAttribute("class", "pending");
      }
      Y.each(u.invalidate || [], function(i) { invalid[i] = 1; });
      panel.set("bodyContent", u.message);

      var headers = { "Accept": "application/json" };
      var param = { data: u.data, on: { success: _ok, failure: _fail },
                    context: this, method: u.method, sync: false,
                    timeout: null, headers: headers };
      if (u.method == "DELETE")
      {
        // See http://yuilibrary.com/projects/yui3/ticket/2530091.
        // YUI3 will convert 'DELETE' into having URL arguments, while
        // server requires data in body. This hack hides data payload
        // from Y.IO and sends it manually in the io:start event, where
        // e.data has the XHR object when using 'eventFacade: true' config.
        delete param.data;
        headers["Content-Type"]
          = "application/x-www-form-urlencoded; charset=UTF-8";
        param.on.start = function(e) {
          e.data.send(Y.QueryString.stringify(u.data));
          e.data.send = function() {};
        };
      }
      req = io.send(_url(u.entity), param);
    };

    // Process the next operation in 'updates'. If we've reached the end
    // of the list, finish off, otherwise start executing the next one.
    _next = function()
    {
      if (++cur == updates.length)
        panel.hide(), _last();
      else
        _exec();
    };

    // Finish off processing: force all invalidated data to reload.
    _last = function()
    {
      Y.each(Y.Object.keys(invalid), function(i) {
        _refresh(i, _data[i], _RELOAD);
      });
    };

    // Put up the panel and start running requests.
    panel = new Y.Panel({
      bodyContent: updates[0].message, render: "#state-modify",
      width: "40%", centered: true, modal: true, zIndex: 10,
      buttons: [{ value: "Stop", section: Y.WidgetStdMod.FOOTER,
                  action: _stop }]
    });

    _next();
  };

  /** Get the current instance. */
  this.currentInstance = function()
  {
    return _instance;
  };

  /** Switch data to another instance. This invalidates all data and
      forces them to be reloaded on the next access, but does not yet
      issue requests for them. */
  this.instance = function(value)
  {
    if (_instance != value)
    {
      _instance = value;

      for (var name in _data)
      {
        var obj = _data[name];
        obj.node.setAttribute("class", "");
        obj.valid = _RELOAD;
        obj.value = null;
      }

      _abort();
    }
  };

  /** Add state elements from _ITEMS, with debug indicator under @a debug. */
  this.start = function(debug)
  {
    Y.each(_ITEMS, function(name) {
      var n = debug.one("#debug-data-" + name);
      if (! n)
      {
        n = Y.Node.create("<p id='#debug-data-" + name + "'>" + name + "</p>");
        debug.append(n);
      }

      _data[name] = { valid: false, value: null, node: n };
    });
  };

  return this;
};
