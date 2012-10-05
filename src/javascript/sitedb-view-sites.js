var Sites = X.inherit(View, function(Y, gui, rank)
{
  /** Alias types. */
  var _ALIASES = ["CMS", "PhEDEx", "LCG"];

  /** Resource types. */
  var _RESOURCES = ["CE", "SE"];

  /** Myself. */
  var _self = this;

  /** 'None' text material. */
  var _none = "<span class='faded'>(None)</span>";

  /** Current state object, for event callbacks. */
  var _state = null;

  /** Event delegate for handling removals. */
  var _rmalias = null;
  var _rmhost = null;
  var _rmchild = null;

  /** View master objects. */
  var _views = new ViewContentSet(Y, {
    loading: "view-loading",
    authfail: "view-auth-fail",
    nosuch: "view-no-such",
    main: "view-sites-main",
    create: "view-sites-create",
    remove: "view-sites-remove",
    names: "view-sites-names",
    resources: "view-sites-resources",
    assocs: "view-sites-assocs"
  });

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Sites",
            ["whoami", "sites", "site-names", "site-resources",
             "site-associations", "resource-pledges", "pinned-software",
             "site-responsibilities"]);

  /** Action handler for creating a site. */
  var _createSite = function(state, title, tier, country, usage,
                             url, logo_url, cms, lcg, executive)
  {
    if (! state || ! title || ! tier || ! country
        || ! usage || ! cms || ! lcg || ! executive)
      return;

    state.modify([
      { method: "PUT", entity: "sites",
        data: { "site_name": title, "tier": tier, "country": country,
                "usage": usage, "url": url, "logo_url": logo_url,
                "devel_release": "n", "manual_install": "n" },
        message: "Creating site '" + Y.Escape.html(title) + "'" },

      { method: "PUT", entity: "site-names",
        data: { "site_name": title, "type": "cms", "alias": cms },
        message: "Adding site alias " + Y.Escape.html(title) + " = "
                 + Y.Escape.html(cms) + "/cms" },

      { method: "PUT", entity: "site-names",
        data: { "site_name": title, "type": "lcg", "alias": lcg },
        message: "Adding site alias " + Y.Escape.html(title) + " = "
                 + Y.Escape.html(cms) + "/lcg" },

      { method: "PUT", entity: "site-responsibilities",
        data: { "site_name": title, "role": "Site Executive",
                "username": executive.username },
        message: "Adding site executive '"
                 + Y.Escape.html(executive.fullname) + "'" }
    ]);
  };

  /** Action handler for adding site name aliases. */
  var _addAlias = function(site, alias, name)
  {
    if (! site || ! alias || ! name)
      return;

    if (! (site in _state.sitesByCMS))
      return;

    site = _state.sitesByCMS[site];
    _state.modify([{
      method: "PUT", entity: "site-names",
      data: { "site_name": site.site_name, "type": alias, "alias": name },
      message: "Adding site alias " + Y.Escape.html(site.canonical_name)
               + " = " + Y.Escape.html(name) + "/" + Y.Escape.html(alias)
    }]);
  };

  /** Action handler for removing site name aliases. */
  var _removeAlias = function(e)
  {
    var x = X.findEventAncestor(e, "x-site");
    if (! x) return;

    var obj = _state.sitesByCMS[x.value];
    if (! obj) return;

    var alias = X.getDOMAttr(x.node, "x-alias");
    var name = X.getDOMAttr(x.node, "x-name");
    if (! (alias in obj.name_alias) || obj.name_alias[alias].indexOf(name) < 0)
      return;

    _state.modify([{
      method: "DELETE", entity: "site-names",
      data: { "site_name": obj.site_name, "type": alias, "alias": name },
      message: "Deleting site alias " + Y.Escape.html(obj.canonical_name)
               + " = " + Y.Escape.html(name) + "/" + Y.Escape.html(alias)
    }]);
  };

  /** Action handler for adding site resources. */
  var _addHost = function(site, type, fqdn, primary)
  {
    if (! site || ! type || ! fqdn || ! primary)
      return;

    if (! (site in _state.sitesByCMS))
      return;

    site = _state.sitesByCMS[site];
    _state.modify([{
      method: "PUT", entity: "site-resources",
      data: { "site_name": site.site_name, "type": type,
              "fqdn": fqdn, "is_primary": primary },
      message: "Adding site resource " + Y.Escape.html(site.canonical_name) + " "
               + Y.Escape.html(fqdn) + "/" + Y.Escape.html(type)
    }]);
  };

  /** Action handler for removing site resources. */
  var _removeHost = function(e)
  {
    var x = X.findEventAncestor(e, "x-site");
    if (! x) return;

    var obj = _state.sitesByCMS[x.value];
    if (! obj) return;

    var type = X.getDOMAttr(x.node, "x-type");
    var fqdn = X.getDOMAttr(x.node, "x-fqdn");
    var is_primary = X.getDOMAttr(x.node, "x-is_primary");
    if (! (type in obj.resources))
      return;

    var r = Y.Array.find(obj.resources[type], function(i) { return i.fqdn == fqdn && i.is_primary == is_primary; });
    if (! r)
      return;

    _state.modify([{
      method: "DELETE", entity: "site-resources",
      data: { "site_name": obj.site_name, "type": type, "fqdn": fqdn, "is_primary": is_primary },
      message: "Removing site resource " + Y.Escape.html(obj.canonical_name) + " "
               + Y.Escape.html(fqdn) + "/" + Y.Escape.html(type) + "/" 
               + Y.Escape.html(is_primary)
    }]);
  };

  /** Action handler for adding site associations. */
  var _addChild = function(parent, child)
  {
    if (! parent || ! child || ! (parent in _state.sitesByCMS))
      return;

    parent = _state.sitesByCMS[parent];
    _state.modify([{
      method: "PUT", entity: "site-associations",
      data: { "parent_site": parent.site_name, "child_site": child.site_name },
      message: "Associating " + Y.Escape.html(child.canonical_name)
               + " to " + Y.Escape.html(parent.canonical_name)
    }]);
  };

  /** Action handler for removing site associations. */
  var _removeChild = function(e)
  {
    var x = X.findEventAncestor(e, "x-parent");
    if (! x) return;

    var child = X.getDOMAttr(x.node, "x-child");
    if (! (x.value in _state.sitesByCMS)
        || ! (child in _state.sitesByCMS))
      return;

    var parent = _state.sitesByCMS[x.value];
    child = _state.sitesByCMS[child];
    _state.modify([{
      method: "DELETE", entity: "site-associations",
      data: { "parent_site": parent.site_name, "child_site": child.site_name },
      message: "Dissociating " + Y.Escape.html(child.canonical_name)
               + " from " + Y.Escape.html(parent.canonical_name)
    }]);
  };

  /** Make a YUI <input> node auto-complete for site names. */
  var _selectSite = function(state, view, item, onselect)
  {
    var node = view.node(item);
    node.plug(Y.Plugin.AutoComplete, {
      source: function() { return Y.Object.values(state.sitesByCMS); },
      resultTextLocator: function(s) { return s.canonical_name; },
      resultFilters: "subWordMatch",
      resultHighlighter: "subWordMatch",
      maxResults: 25
    });

    var current = null, keyselect = false;
    node.ac.on(["query", "clear"], function(e) {
      current = null; keyselect = false;
    });
    node.ac.on("select", function(e) {
      keyselect = (e.originEvent.type == "keydown");
      current = e.result.raw;
      onselect(current);
    });
    node.on("keypress", function(e) {
      if (e.keyCode == 13 && current && !keyselect)
        onselect(current);
      keyselect = false;
    });
  };

  /** View attach handler: delegate remove buttons on this page. */
  this.attach = function()
  {
    _rmalias = _self.doc.delegate("click", _removeAlias, ".rmalias");
    _rmhost = _self.doc.delegate("click", _removeHost, ".rmhost");
    _rmchild = _self.doc.delegate("click", _removeChild, ".rmchild");
  };

  /** View detach handler: detach view and delegations for remove buttons. */
  this.detach = function()
  {
    _views.detach();
    _rmalias.detach();
    _rmhost.detach();
    _rmchild.detach();
    _state = null;
  };

  /** The main view page, show site list and site info, with links
      to details and site-specific operations. */
  this.main = function(req)
  {
    var content;
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, site, "Sites");
    _self.loading(state);

    var view = _views.attach("main", _self.doc);

    var h = (! site ? "inherit" : sprintf("%dpx", _self.doc.get('winHeight') * 0.4));
    view.style("sites", "height", h);

    content = "";
    Y.each(Object.keys(state.sitesByTier).sort(d3.ascending), function(t) {
      content += "<h3>" + Y.Escape.html(t) + "</h3>";
      Y.each(state.sitesByTier[t], function(s) {
        content += "<p>" + _self.siteLink(instance, s) + "</p>";
      });
    });
    view.content("list", content);

    if (site)
    {
      var m = /^\((.*)\)$/.exec(site);
      var name = (m ? m[1] : site);
      var s = (m ? (name in state.sitesByName ? state.sitesByName[name] : null)
               : (name in state.sitesByCMS ? state.sitesByCMS[name] : null));
      if (s)
      {
        view.style("info", "display", "");
        view.content("site-head",
                     (! state.isGlobalAdmin() ? ""
                      : "<span style='float:right;font-weight:normal;font-size:80%'>["
                        + _self.siteLink(instance, s, "Remove", "/remove")
                        + "]</span>")
                     + Y.Escape.html(name));

        view.content("names-head", _self.siteLink(instance, s, "Names", "/names"));
        view.content("site-title", Y.Escape.html(s.site_name));
        view.content("tier", Y.Escape.html(s.tier));
        view.content("cms",
                     ("cms" in s.name_alias
                      ? s.name_alias.cms.map(Y.Escape.html).join("<br />")
                      : _none));
        view.content("phedex",
                     ("phedex" in s.name_alias
                      ? s.name_alias.phedex.map(Y.Escape.html).join("<br />")
                      : _none));
        view.content("lcg",
                     ("lcg" in s.name_alias
                      ? s.name_alias.lcg.map(Y.Escape.html).join("<br />")
                      : _none));
        view.content("location", Y.Escape.html(s.country));
        view.content("usage", (s.usage ? Y.Escape.html(s.usage) : _none));
        view.content("links",
                     (s.url ? "<a target='_new' href='" + s.url + "'>Site</a>" : "")
                     + (s.url && s.logo_url ? ", " : "")
                     + (s.logo_url ? "<a target='_new' href='" + s.logo_url + "'>Logo</a>" : "")
                     + (! s.url && ! s.logo_url ? _none : ""));

        view.content("assocs-head",
                     _self.siteLink(instance, s, "Associations", "/associations"));
        view.content("parent",
                     (s.parent_site
                      ? _self.siteLink(instance, s.parent_site)
                      : _none));
        view.content("children",
                     s.child_sites.map(function(i) {
                       return _self.siteLink(instance, i); }).join("<br />"));

        view.content("hosts-head",
                     _self.siteLink(instance, s, "Hosts", "/resources"));
        view.content("ce",
                     s.resources.CE.map(function(i) {
                       return Y.Escape.html(i.fqdn); }).join("<br />"));
        view.content("se",
                     s.resources.SE.map(function(i) {
                       return Y.Escape.html(i.fqdn); }).join("<br />"));

        var pledgeTime = null;
        var quarter = null;
	var quarters = Object.keys(s.resource_pledges).sort(d3.descending);
        var pledge = quarters.length ? s.resource_pledges[quarters[0]] : null;
        if (pledge)
        {
          var t = new Date();
          t.setTime(pledge.pledge_date * 1000);
          pledgeTime = sprintf("%s %d, %d", X.MONTH[t.getMonth()],
                               t.getDate(), t.getFullYear());
          quarter = quarters[0].replace(/^(\d+)\.(\d+)$/, "$1q$2");
        }

        view.content("pledges-head",
                     _self.pledgeLink(instance, s, "Resource Pledge"));
        view.content("quarter", (pledge ? quarter : _none));
        view.content("updated", (pledge ? pledgeTime : _none));
        view.content("cpu", (pledge ? Y.Escape.html(pledge.cpu) : "-"));
        view.content("jobs", (pledge ? Y.Escape.html(pledge.job_slots) : "-"));
        view.content("disk", (pledge ? Y.Escape.html(pledge.disk_store) : "-"));
        view.content("tape", (pledge ? Y.Escape.html(pledge.tape_store) : "-"));
        view.content("wan", (pledge ? Y.Escape.html(pledge.wan_store) : "-"));
        view.content("local", (pledge ? Y.Escape.html(pledge.local_store) : "-"));
        view.content("nren", (pledge ? Y.Escape.html(pledge.national_bandwidth) : "-"));
        view.content("opn", (pledge ? Y.Escape.html(pledge.opn_bandwidth) : "-"));

        content = "";
        view.content("people-head",
                     _self.siteContactLink(instance, s, "Responsibilities"));
        var roles = Object.keys(s.responsibilities).sort(d3.ascending);
	Y.each(roles, function(role) {
	  content +=
            ("<dt>" + Y.Escape.html(role) + "</dt><dd>"
             + s.responsibilities[role].map(function(i) {
                 return _self.personLink(instance, i); }).join("<br />")
             + "</dd>");
        });
        view.content("responsibilities", content);
      }
      else
        view.style("info", "display", "none");
    }
    else
      view.style("info", "display", "none");

    view.render();
  };

  /** Page for global admins to create a new site. */
  this.create = function(req)
  {
    var view;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Create", "Sites");
    _self.loading(state);

    if (! state.isGlobalAdmin())
    {
      view = _views.attach("authfail", _self.doc)
      view.content("what", "create sites");
    }
    else
    {
      view = _views.attach("create", _self.doc)
      view.validator("title", X.rxvalidate(gui.rx.SITE, true));
      view.validator("country", X.rxvalidate(gui.rx.COUNTRY, true));
      view.validator("url", X.rxvalidate(gui.rx.URL, true));
      view.validator("logo", X.rxvalidate(gui.rx.URL, true));
      view.validator("goc", X.rxvalidate(gui.rx.INT, true));
      view.validator("cms", X.rxvalidate(gui.rx.NAME, true));
      view.validator("lcg", X.rxvalidate(gui.rx.NAME, true));
      view.once(function() {
        var nexec = view.node("exec");
        nexec.plug(Y.Plugin.AutoComplete, {
          source: function() { return state.people; },
          resultTextLocator: function(p) { return p.fullname + " | " + p.email; },
          resultFilters: "subWordMatchFold",
          resultHighlighter: "subWordMatchFold",
          maxResults: 25
        });

        nexec.ac.on("select", function(e) { view.__executive = e.result.raw; });
      });

      view.on("button", "click", function(e) {
        _createSite(state, view.valueOf("title"), view.valueOf("tier"),
                    view.valueOf("country"), view.valueOf("usage"),
                    view.valueOf("url"), view.valueOf("logo"),
                    view.valueOf("cms"), view.valueOf("lcg"),
                    view.__executive);
      });

      view.focus("tier");
    }

    view.render();
  };

  /** Page for global admins to remove a site. */
  this.remove = function(req)
  {
    var view;
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Remove", site, "Sites");
    _self.loading(state);

    var m, obj, isadmin = state.isGlobalAdmin();
    if ((m = site.match(/^\((.+)\)$/)) && state.sitesByName[m[1]])
      site = m[1], obj = state.sitesByName[m[1]];
    else if (site in state.sitesByCMS)
      obj = state.sitesByCMS[site];

    if (obj && isadmin)
    {
      view = _views.attach("remove", _self.doc);
      view.content("title", Y.Escape.html(site));
      view.on("remove", "click", function(e) {
        state.modify([{
          method: "DELETE", entity: "sites", data: { "site_name": obj.site_name },
          invalidate: ["site-names", "site-resources", "site-associations",
                       "resource-pledges", "pinned-software",
                       "site-responsibilities"],
          message: "Deleting site " + Y.Escape.html(site),
          onsuccess: function(){ gui.history.save("/" + instance + "/sites"); }
        }]);
      });
    }
    else if (state.complete)
    {
      if (! obj)
      {
        view = _views.attach("nosuch", _self.doc);
        view.content("what", "site");
      }
      else
      {
        view = _views.attach("authfail", _self.doc);
        view.content("what", "remove site");
      }
    }
    else
      view = _views.attach("loading", _self.doc);

    view.render();
  };

  /** Manage site name aliases. For unprivileged users just show the
      different name aliases. For global admins and site executives
      allow adding and removing aliases. */
  this.names = function(req)
  {
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Names", site, "Sites");
    _self.loading(state);
    _state = state;

    var isadmin = (state.isGlobalAdmin()
                   || state.hasSiteRole("Site Executive", site));
    var obj, content, view;
    if (site in state.sitesByCMS)
      obj = state.sitesByCMS[site];

    if (obj)
    {
      view = _views.attach("names", _self.doc);
      view.validator("name", X.rxvalidate(gui.rx.NAME, true));
      view.on("name", "keypress", function(e) {
        if (e.keyCode == 13)
          _addAlias(site, view.valueOf("alias"), view.valueOf("name"));
      });

      view.content("title", Y.Escape.html(obj.canonical_name) + " names");

      content = "";
      Y.each(_ALIASES, function(kind) {
        var label = kind.toLowerCase();
        if (label in obj.name_alias)
        {
          var v = obj.name_alias[label];
          content += "<tr><td rowspan='" + v.length + "'>"
                     + Y.Escape.html(kind) + "</td>";
          Y.each(v, function(alias, ix) {
            content += (ix ? "<tr>" : "") + "<td>"
                       + "<span class='rmbutton rmalias' title='Remove item'"
                       + " x-site='" + X.encodeAsPath(site) + "'"
                       + " x-alias='" + X.encodeAsPath(label) + "'"
                       + " x-name='" + X.encodeAsPath(alias) + "'"
                       + "><span class='rmicon'></span></span>"
                       + Y.Escape.html(alias)
                       + "</td></tr>";
          });
        }
      });
      view.content("names", content);
    }
    else if (state.complete)
    {
      view = _views.attach("nosuch", _self.doc);
      view.content("what", "site");
    }
    else
      view = _views.attach("loading", _self.doc);

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

  /** Manage site resources. For unprivileged users just show the
      different hosts. For global admins and site executives allow
      adding and removing hosts. */
  this.resources = function(req)
  {
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Resources", site, "Sites");
    _self.loading(state);
    _state = state;

    var isadmin = (state.isGlobalAdmin()
                   || state.hasSiteRole("Site Executive", site)
                   || state.hasSiteRole("Site Admin", site));
    var obj, content, view;
    if (site in state.sitesByCMS)
      obj = state.sitesByCMS[site];

    if (obj)
    {
      view = _views.attach("resources", _self.doc);
      view.validator("name", X.rxvalidate(gui.rx.FQDN, true));
      view.on("name", "keypress", function(e) {
        if (e.keyCode == 13)
          _addHost(site, view.valueOf("resource"), view.valueOf("name"),
                   view.valueOf("primary") ? "y" : "n");
      });

      view.content("title", Y.Escape.html(obj.canonical_name) + " resources");

      content = "";
      Y.each(_RESOURCES, function(kind) {
        if (kind in obj.resources && obj.resources[kind].length)
        {
          var v = obj.resources[kind];
          content += "<tr><td rowspan='" + v.length + "'>"
                     + Y.Escape.html(kind) + "</td>";
          Y.each(v, function(res, ix) {
            content += (ix ? "<tr>" : "") + "<td>"
                       + (res.is_primary == "y" ? "Yes" : "No") + "</td><td>"
                       + "<span class='rmbutton rmhost' title='Remove item'"
                       + " x-site='" + X.encodeAsPath(site) + "'"
                       + " x-type='" + X.encodeAsPath(kind) + "'"
                       + " x-fqdn='" + X.encodeAsPath(res.fqdn) + "'"
                       + " x-is_primary='" + X.encodeAsPath(res.is_primary) + "'"
                       + "><span class='rmicon'></span></span>"
                       + Y.Escape.html(res.fqdn)
                       + "</td></tr>";
          });
        }
      });
      view.content("fqdns", content);
    }
    else if (state.complete)
    {
      view = _views.attach("nosuch", _self.doc);
      view.content("what", "site");
    }
    else
      view = _views.attach("loading", _self.doc);

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

  /** Manage site associations. For unprivileged users just show the
      relationships. For global admins and parent site executives allow
      adding and removing children. */
  this.associations = function(req)
  {
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Children", site, "Sites");
    _self.loading(state);
    _state = state;

    var isadmin = (state.isGlobalAdmin()
                   || state.hasSiteRole("Site Executive", site));
    var obj, content, view;
    if (site in state.sitesByCMS)
      obj = state.sitesByCMS[site];

    if (obj)
    {
      view = _views.attach("assocs", _self.doc);
      view.__site = site;
      view.once(_selectSite, state, view, "name",
                function(s) { _addChild(view.__site, s); });

      view.content("title", Y.Escape.html(obj.canonical_name) + " children");

      content = "";
      Y.each(obj.child_sites, function(s) {
        content += "<tr><td>"
                   + "<span class='rmbutton rmchild' title='Remove item'"
                   + " x-parent='" + X.encodeAsPath(obj.canonical_name) + "'"
                   + " x-child='" + X.encodeAsPath(s.canonical_name) + "'"
                   + "><span class='rmicon'></span></span>"
                   + Y.Escape.html(s.canonical_name)
                   + "</td></tr>";
      });
      view.content("children", content);
    }
    else if (state.complete)
    {
      view = _views.attach("nosuch", _self.doc);
      view.content("what", "site");
    }
    else
      view = _views.attach("loading", _self.doc);

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

  // Handle history controller state.
  gui.history.route("/:instance/sites", this.main);
  gui.history.route("/:instance/sites/new", this.create);
  gui.history.route("/:instance/sites/:site", this.main);
  gui.history.route("/:instance/sites/:site/remove", this.remove);
  gui.history.route("/:instance/sites/:site/names", this.names);
  gui.history.route("/:instance/sites/:site/resources", this.resources);
  gui.history.route("/:instance/sites/:site/associations", this.associations);

  return this;
});
