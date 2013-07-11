var SiteDB = function(Y, views, debug)
{
  // Patch up for old browsers.
  if (! Object.keys)
    Object.keys = Y.Object.keys;

  // Myself.
  var _gui = this;

  // Various address bases.
  var _addrs = {
    savannah:  'https://savannah.cern.ch',
    phedex:    'https://cmsweb.cern.ch/phedex/prod/Request::Create?dest=',
    dbs:       'https://cmsweb.cern.ch/dbs_discovery/getData?dbsInst=cms_dbs_prod_global&proc=&ajax=0&userMode=user&group=*&tier=*&app=*&site',
    goc:       'https://goc.gridops.org/site/list?id=',
    gstat:     'http://goc.grid.sinica.edu.tw/gstat',
    dashboard: 'http://lxarda16.cern.ch/dashboard/request.py',
    squid:     'http://frontier.cern.ch/squidstats/mrtgcms',
    sam:       'https://lcg-sam.cern.ch:8443/sam/sam.py?'
  };

  // Time-out object for soft invalidation of the state date.
  var _invalidateTO = null;

  // Time-out object for hiding message overlay.
  var _messagesTO = null;

  // Messages overlay.
  var _messages = Y.one("#messages");

  // Content areas.
  var _content = Y.one("#content");

  // All views.
  var _views = [];

  // Current view.
  var _view = null;

  // Current state data.
  var _state = new State(Y, this, REST_INSTANCES[0].id);

  // History controller.
  this.history = new Y.Controller({ root: REST_SERVER_ROOT });

  // Regexps, converted from SITEDB_REGEXPS, plus a couple static ones.
  this.rx = { FLOAT: new XRegExp("^[0-9]+(\\.[0-9]*)?$"),
              INT: new XRegExp("^[0-9]+$") };

  /** Return the current view. */
  this.view = function()
  {
    return _view;
  };

  /** Show a message @a msg in the overlay area for @a timeout milliseconds.
      If previous messages are already showing, reset them if @a reset is
      truthy, otherwise append to existing messages. The messages will
      automatically hide away after @a timeout. */
  this.displayMessage = function(timeout, type, msg, reset)
  {
    if (_messagesTO && ! reset)
      msg = _messages.getContent() + msg;

    if (_messagesTO)
      _messagesTO.cancel();

    _messagesTO = Y.later(timeout, _gui, _gui.hideMessage);
    X.applyContentStyle(_messages, type, msg, "display", "");
  };

  /** Hide and empty the message overlay, if any. */
  this.hideMessage = function()
  {
    X.applyContentStyle(_messages, "", "", "display", "none");
  };

  /** Report an error. Displays the error message in the overlay
      area with a link to report the issue in trac if @a show, plus
      sends the message automatically to the server as problem
      feedback. Returns the full message. Both the server feedback
      and trac ticket link are given unique id which can be used to
      identify this specific issue in logs. */
  this.errorReport = function(timeout, file, line, origin, category, message, show)
  {
    var errid = X.randomid();
    var emsg = X.encodeAsPath(message);
    var file = file.replace(/.*\//, "");
    var label = X.encodeAsPath("[#" + category + ":" + errid
                + "] SiteDB web problem");
    var url = REST_SERVER_ROOT + "/feedback"
              + "?o=" + X.encodeAsPath(origin)
              + ";i=" + errid
              + ";c=" + category
              + ";l=" + X.encodeAsPath(file + ":" + line)
              + ";m=" + emsg;

    var msg = message.replace(/[. ]*$/, "")
              + ". (Automatically reported, in case of questions please"
              + " follow up <a href='https://svnweb.cern.ch/trac/CMSDMWM/"
              + "newticket?component=SiteDB&amp;summary=" + label + "&amp;"
              + "description=" + emsg + "' target='_new'>on trac</a>.)";

    if (show)
      _gui.displayMessage(timeout, "alert", msg);
    try { Y.io(url); } catch (e) { if (console && console.log) console.log(url); }
    return msg;
  };

  /** Page error handler. Automatically reports bugs to server and
      shows an error message overlay. */
  this.pageErrorHandler = function(msg, url, line)
  {
    _gui.errorReport(10000, url, line, "page", "exception",
                     "Internal error while rendering this page: "
                     + msg.toString().replace(/\s+/g, " "), true);
    _gui.view().error();
    return true;
  };

  /** Callback to handle clicks on internal links. If the link has
      class 'dispatch-only', makes a direct state transition, else
      pushes the new link target state to the history stack. */
  var _internalLink = function(e)
  {
    // Ignore events from buttons other than the first/left one.
    if (e.button !== 1 || e.ctrlKey || e.metaKey)
      return;

    // Tell view we are about to do internal navigation, so it can
    // get rid of local overrides.
    _gui.view().prenavigate();

    // Actually navigate to new state.
    var path = _gui.history.removeRoot(e.target.getAttribute("href"));
    if (e.target.hasClass('dispatch-only'))
      _gui.history._dispatch(path);
    else
      _gui.history.save(path);

    // Stop propagation.
    e.preventDefault();
  };

  /** Callback to switch to another database instance. */
  var _switchInstance = function(req)
  {
    _gui.history.save("/" + req.params.name + "/" + _view.id);
  };

  /** Start running the SiteDB UI. */
  this.start = function(at)
  {
    // Redirect clicks on 'internal' links to history dispatching.
    Y.one(document.body).delegate("click", _internalLink, "a.internal");

    // Fill in instance menu.
    var instances = Y.one("#instances");
    for (var i = 0; i < REST_INSTANCES.length; ++i)
      instances.append("<h2 class='subtitle title" + (i == 0 ? ' first' : '')
                       + "'><a class='internal dispatch-only' href='"
                       + REST_SERVER_ROOT + "/instance/" + REST_INSTANCES[i].id
                       + "'>" + REST_INSTANCES[i].title + "</a></h2>");

    this.history.route("/instance/:name", _switchInstance);

    // Maybe show debug menus.
    Y.one("#debug-data").setStyle("display", debug ? "" : "none");

    // Refresh side bar.
    this.updateSidebar();

    // Redirect the default route to the specified view.
    this.history.route("/*any", function() { _gui.history.save(at); });

    // Init state load.
    _state.start(Y.one("#debug-data"));

    // Apply current view.
    this.history.dispatch();
  };

  /** Return state appropriate for @a view from @a instance. */
  this.state = function(instance, view)
  {
    var current = _state.currentInstance();
    var changed = (instance != current);
    var instances = Y.one("#instances");
    var views = Y.one("#views");

    // If requested instance is different, rewrite all header links.
    if (changed)
      views.all("a.internal").each(function(n)
        {
          var href = _gui.history.removeRoot(n.getAttribute("href"));
          if (href.substr(0, current.length+2) == "/" + current + "/")
	    n.setAttribute("href", REST_SERVER_ROOT + "/" + instance
			   + href.substr(current.length+1));
        });

    // Mark appropriate view and instance selected.
    views.all("a.internal").each(function(n)
      {
        var href = _gui.history.removeRoot(n.getAttribute("href"));
	if (href.replace(/.*\//, "") == view.id)
	  n.ancestor(".title").addClass("selected");
	else
	  n.ancestor(".title").removeClass("selected");
      });

    instances.all("a.internal").each(function(n)
      {
        var href = _gui.history.removeRoot(n.getAttribute("href"));
	if (href.replace(/.*\//, "") == instance)
	  n.ancestor(".title").addClass("selected");
	else
	  n.ancestor(".title").removeClass("selected");
      });

    // Maybe invalidate instance data.
    _state.instance(instance);

    // If another view is currently attached, detach and attach views first
    // and soft invalidate state data so we query browser for any updates.
    // But do the latter just periodically, not on every navigation.
    if (_view != view)
    {
      var prev = _view;

      if (_view)
        _view.detach();
      _view = view;
      if (_view)
        _view.attach();

      if (_invalidateTO)
        _invalidateTO.cancel();

      if (prev)
        _invalidateTO = Y.later(30000, _state, function() {
          _state.invalidate(); _state.requireall(); });

      changed = true;
    }

    // If we changed instance or view, trigger delayed load of all data.
    if (changed)
      Y.later(5000, _state, _state.requireall);

    // Return the state, it can now be used.
    return _state;
  };

  /** Respond to state model change. Refreshes sidebar, invokes the
      current view's update() method, then re-dispatches the controller
      to cause current view handler to be invoked. */
  this.update = function()
  {
    this.updateSidebar();
    _view.update.call(_view);
    this.history.dispatch();
  };

  /** Update the side bar information. */
  this.updateSidebar = function()
  {
    var content = "";
    var instance = _state.currentInstance();
    var p = _state.whoami && _state.whoami.person;

    // Fill in personal information.
    if (_state.whoami)
      content += ("<p><a class='internal' href='" + REST_SERVER_ROOT + "/"
                  + X.encodeAsPath(instance) + "/people/me'>"
                  + Y.Escape.html(_state.whoami.name) + "</a></p>");

    if (p)
    {
      if (p.email)
        content += "<p>E-mail: " + _view.mailto(p.email) + "</p>";

      if (p.phone1)
      {
        content += "<p>Tel: " + Y.Escape.html(p.phone1)
	if (p.phone2)
          content += ", " + Y.Escape.html(p.phone2)
        content += "</p>";
      }
      if (p.im_handle && p.im_handle != "none:none" && p.im_handle != "None")
	content += "<p>IM: " + Y.Escape.html(p.im_handle);

      if (content == "")
        content = "<p class='faded'>Unknown</p>";
    }
    else if (_state.complete)
      content = "";
    else
      content = "<p class='faded'>Not yet loaded</p>";

    content += "<p><a class='internal' href='" + REST_SERVER_ROOT + "/"
               + X.encodeAsPath(instance) + "/mycert'>"
               + "Update certificate</a></p>";

    X.applyContent(Y.one("#me"), content);

    // Fill in site information.
    content = "";
    if (p)
    {
      var sites = Object.keys(p.sites).sort();
      Y.each(sites, function(name) {
        var s = p.sites[name];
	content += ("<p>" + _view.siteLink(instance, s) + "</p>");
      });

      if (content == "")
        content = "<p class='faded'>None</p>";
    }
    else if (_state.complete)
      content = "<p class='faded'>None</p>";
    else
      content = "<p class='faded'>Not yet loaded</p>";

    X.applyContent(Y.one("#my-sites"), content);

    // Fill in group information.
    content = "";
    if (p)
    {
      Y.each(Object.keys(p.groups).sort(), function(g) {
        content += ("<p>" + _view.groupLink(instance, _state.groupsByName[g]) + "</p>");
      });

      if (content == "")
        content = "<p class='faded'>None</p>";
    }
    else if (_state.complete)
      content = "<p class='faded'>None</p>";
    else
      content = "<p class='faded'>Not yet loaded</p>";

    X.applyContent(Y.one("#my-groups"), content);

    // Fill in role information.
    content = "";
    if (p)
    {
      Y.each(Object.keys(p.roles).sort(), function(r) {
        content += ("<p>" + _view.roleLink(instance, _state.rolesByTitle[r]) + "</p>");
      });

      if (content == "")
        content = "<p class='faded'>None</p>";
    }
    else if (_state.complete)
      content = "<p class='faded'>None</p>";
    else
      content = "<p class='faded'>Not yet loaded</p>";

    X.applyContent(Y.one("#my-roles"), content);

    var display = "none";
    // If this is an operator or admin, add link for person creation.
    if (_state.isSitedbOperator() || _state.isGlobalAdmin())
    {
      display = "";
      content = "<h3>Administration</h3>"
                + "<p><a class='internal' href='" + REST_SERVER_ROOT + "/"
                + X.encodeAsPath(instance) + "/people/new'>"
                + "Create service</a></p>";

      // If this is an operator or global admin, add link to site creation too.
      if (_state.isSitedbOperator() || _state.isGlobalAdmin())
        content += "<p><a class='internal' href='" + REST_SERVER_ROOT + "/"
                   + X.encodeAsPath(instance) + "/sites/new'>"
                   + "Create site</a></p>";
    }

    X.applyContentStyle(Y.one("#my-admin"), "", content, "display", display);
  };

  // If not in debug mode, capture errors and report them to server.
  if (! debug)
    window.onerror = _gui.pageErrorHandler;

  // Convert SITEDB_REGEXPS into this.rx. Nuke (?u) and map [\w] into
  // [\p{L}\p{N}\p{Pc}\p{M}]; it's assumed \w doesn't appear outside [] and
  // (?x) flags may only occur at the beginning of the regexp. This uses
  // XRegExp utilities because native RegExp is too limited.
  Y.each(SITEDB_REGEXPS, function(pattern, name) {
    pattern = pattern.replace(/^(\(\?([a-z]+)\))/, function(s) {
                               return s.replace("u", ""); })
              .replace(/\\w/g, "\\p{L}\\p{N}\\p{Pc}\\p{M}");
    _gui.rx[name] = XRegExp(pattern);
  });

  // Add views.
  for (var view = 0; view < views.length; ++view)
    _views.push(new views[view](Y, this, view));

  // Start up.
  this.start("/" + REST_INSTANCES[0].id + "/sites");
  return this;
};
