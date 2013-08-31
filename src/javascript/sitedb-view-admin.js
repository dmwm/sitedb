var Admin = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** Current state object, for event callbacks. */
  var _state = null;

  /** Event delegate for handling removals. */
  var _rmitem = null;
  var _rmrole = null;
  var _rmgroup = null;
  var _rmfederationsite = null;
  /** View master objects. */
  var _views = new ViewContentSet(Y, {
    main: "view-admin-main",
    group: "view-admin-group",
    role: "view-admin-role",
    site: "view-admin-site",
    federation: "view-admin-federation"
  });

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Admin",
            ["whoami", "roles", "groups", "people", "sites",
             "site-responsibilities", "group-responsibilities",
             "federations","federations-sites"]);

  /** Action handler for creating roles. */
  var _createRole = function(title)
  {
    if (title)
      _state.modify([{
        method: "PUT", entity: "roles", data: { "title": title },
        message: "Creating role '" + title + "'"
      }]);
  };

  /** Action handler for removing roles. */
  var _removeRole = function(e)
  {
    var x = X.findEventAncestor(e, "x-role");
    if (! x) return;

    var obj = _state.rolesByTitle[x.value];
    if (! obj) return;

    X.confirm(Y, "Delete role '" + Y.Escape.html(obj.title) + "' with "
              + obj.members.length + " member"
              + (obj.members.length != 1 ? "s" : "") + "?",
              "Delete", function() {
                _state.modify([{
                  method: "DELETE", entity: "roles",
                  data: { "title": obj.title },
                  invalidate: ["site-responsibilities", "group-responsibilities"],
                  message: "Deleting role '" + obj.title + "'"
                }]);
              });
  };

  /** Action handler for creating groups. */
  var _createGroup = function(name)
  {
    if (name)
      _state.modify([{
        method: "PUT", entity: "groups", data: { "name": name },
        message: "Creating group '" + name + "'"
      }]);
  };

  /** Action handler for removing groups. */
  var _removeGroup = function(e)
  {
    var x = X.findEventAncestor(e, "x-group");
    if (! x) return;

    var obj = _state.groupsByName[x.value];
    if (! obj) return;

    X.confirm(Y, "Delete group '" + Y.Escape.html(obj.name) + "' with "
              + obj.members.length + " member"
              + (obj.members.length != 1 ? "s" : "") + "?",
              "Delete", function() {
                _state.modify([{
                  method: "DELETE", entity: "groups",
                  data: { "name": obj.name },
                  invalidate: [ "group-responsibilities" ],
                  message: "Deleting group '" + obj.name + "'"
                }]);
              });
  };

  /** Action handler for adding a person to site or group role. */
  var _addRoleMember = function(role, site, group, person)
  {
    role = role &&
      Y.Array.find(Y.Object.values(_state.rolesByTitle),
                   function(r) { return r.canonical_name == role; });

    group = group &&
      Y.Array.find(Y.Object.values(_state.groupsByName),
                   function(g) { return g.canonical_name == group; });

    site = (site in _state.sitesByCMS) && _state.sitesByCMS[site];

    if (! role || ! (group || site) || ! person)
      return;

    if (group)
      _state.modify([{
        method: "PUT", entity: "group-responsibilities",
        data: { "username": person.username, "role": role.title,
                "user_group": group.name },
        message: "Adding role '" + Y.Escape.html(role.title)
                 + "' for '" + Y.Escape.html(person.fullname)
                 + " [" + Y.Escape.html(person.email) + "] in group '"
                 + Y.Escape.html(group.name) + "'"
      }]);
    else
      _state.modify([{
        method: "PUT", entity: "site-responsibilities",
        data: { "username": person.username, "role": role.title,
                "site_name": site.site_name },
        message: "Adding role '" + Y.Escape.html(role.title)
                 + "' for '" + Y.Escape.html(person.fullname)
                 + " [" + Y.Escape.html(person.email) + "] for site '"
                 + Y.Escape.html(site.canonical_name) + "'"
      }]);
  };

  /** Action handler for removing a person from site or group role. */
  var _removeRoleMember = function(e)
  {
    var x = X.findEventAncestor(e, "x-role");
    if (! x) return;

    var role = x.value;
    var site = X.getDOMAttr(x.node, "x-site");
    var group = X.getDOMAttr(x.node, "x-group");
    var person = X.getDOMAttr(x.node, "x-person");

    if (! (role in _state.rolesByTitle)
        || (site && ! (site in _state.sitesByCMS))
        || (group && ! (group in _state.groupsByName))
        || ! (person in _state.peopleByAcc))
      return;

    role = _state.rolesByTitle[role];
    site = (site && _state.sitesByCMS[site]);
    group = (group && _state.groupsByName[group]);
    person = _state.peopleByAcc[person];

    if (group)
      _state.modify([{
        method: "DELETE", entity: "group-responsibilities",
        data: { "username": person.username, "role": role.title,
                "user_group": group.name },
        message: "Removing role '" + Y.Escape.html(role.title)
                 + "' from '" + Y.Escape.html(person.fullname)
                 + " [" + Y.Escape.html(person.email) + "] in group '"
                 + Y.Escape.html(group.name) + "'"
      }]);
    else
      _state.modify([{
        method: "DELETE", entity: "site-responsibilities",
        data: { "username": person.username, "role": role.title,
                "site_name": site.site_name },
        message: "Removing role '" + Y.Escape.html(role.title)
                 + "' from '" + Y.Escape.html(person.fullname)
                 + " [" + Y.Escape.html(person.email) + "] for site '"
                 + Y.Escape.html(site.canonical_name) + "'"
      }]);
  };

  /** Make a YUI <input> node auto-complete for people. */
  var _selectPerson = function(state, view, item, onselect)
  {
    var node = view.node(item);
    node.plug(Y.Plugin.AutoComplete, {
      source: function() { return state.people; },
      resultTextLocator: function(p) { return p.fullname + " | " + p.email; },
      resultFilters: "subWordMatchFold",
      resultHighlighter: "subWordMatchFold",
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

  /** Make a YUI <input> node auto-complete for federation sites. */
  var _selectSite = function(state, view, item, onselect)
  {
    var node = view.node(item);
    node.plug(Y.Plugin.AutoComplete, {
      source: function() { return state.federationsSites; },
      resultTextLocator: function(p) { return p.alias; },
      resultFilters: "subWordMatchFold",
      resultHighlighter: "subWordMatchFold",
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
  /** Action handler for adding a description for role. */
  var _createDescription = function(role, description)
  {
     if((! role) || (! description)) return;
     X.confirm(Y, "Add description for role: '" + Y.Escape.html(role)
             + "' description: '" + Y.Escape.html(description)
             + "' ?",
             "Insert", function() {
               _state.modify([{
                 method: "POST", entity: "roles",
                 data: { "title": role, "description": description},
                 invalidate: [ "roles" ],
                 message: "Adding description"
               }]);
             });
  };

  /** Action handler for creating federation site. */
  var _addFederationSite = function(federation, user_input, none, site)
  {
    var federByCName = {};
    var fed_id = null;
    var allFederations = Y.Object.values(_state.federationsById).sort(function(a, b) {
      return d3.ascending(a.name, b.name); });
    Y.each(allFederations, function(i) {federByCName[i.canonical_name] = i});
    if(federation in federByCName)
      fed_id = federByCName[federation].id;
    else
      return;
    if (fed_id && site){
       if(site.fed_id){X.confirm(Y, "Not allowed to add site"+site.alias+", it is already defined", "Ok", "Cancel"); return;}

    _state.modify([{
        method: "PUT", entity: "federations-sites", data: { "fed_id": fed_id, "site_id" : site.site_id },
        message: "Adding to federation '"+federation+"' site '" + site.alias + "'"
      }]);
    return;
    };
  };


  /** Action handler for removing federation site. */
  var _removeFederationSite = function(e)
  {
    var x = X.findEventAncestor(e, "x-id");
    if (! x) return;
      if(x.value in _state.federationsSitesById){
       var obj = _state.federationsSitesById[x.value];
       if (! obj) return;
       X.confirm(Y, "Delete federation site '" + Y.Escape.html(obj.site_name)
              + " ?",
              "Delete", function() {
                _state.modify([{
                  method: "DELETE", entity: "federations-sites",
                  data: { "site_id": obj.site_id },
                  invalidate: [ "federations-sites" ],
                  message: "Deleting federation site '" + obj.site_name + "'"
                }]);
              });
      };
  };

  /** View attach handler: delegate remove buttons on this page. */
  this.attach = function()
  {
    _rmitem = _self.doc.delegate("click", _removeRoleMember, ".rmitem");
    _rmrole = _self.doc.delegate("click", _removeRole, ".rmrole");
    _rmgroup = _self.doc.delegate("click", _removeGroup, ".rmgroup");
    _rmfederationsite = _self.doc.delegate("click", _removeFederationSite, ".rmfederationsite");
  };

  /** View detach handler: detach delegations for remove buttons. */
  this.detach = function()
  {
    _views.detach();
    _rmitem.detach();
    _rmrole.detach();
    _rmgroup.detach();
    _rmfederationsite.detach();
    _state = null;
  };

  /** The main view page, show roles, groups and federations. For global admin
      allow role and group and federation deletion and creation too. */
  this.main = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Admin");
    _self.loading(state);
    _state = state;

    var isadmin = state.isGlobalAdmin();
    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    var groups = Y.Object.values(state.groupsByName).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    var federations = Y.Object.values(state.federationsById).sort(function(a, b) {
      return a.country == b.country ? a.name < b.name : a.country < b.country; });

    var view = _views.attach("main", _self.doc);
    view.validator("add-role", X.rxvalidate(gui.rx.LABEL, true));
    view.validator("add-group", X.rxvalidate(gui.rx.LABEL, true));
    view.on("add-role", "keypress", function(e) {
      if (e.keyCode == 13) _createRole(view.valueOf("add-role"));
    });
    view.on("add-group", "keypress", function(e) {
      if (e.keyCode == 13) _createGroup(view.valueOf("add-group"));
    });

    var content = "";
    Y.each(roles, function(r) {
      content += "<tr><td style='padding-top:0.1em'>"
                 + _self.roleLink(instance, r)
                 + "</td><td align='right' style='padding-top:0.1em'>"
                 + r.members.length + "</td><td>"
                 + "<span class='rmbutton rmrole' title='Remove item'"
                 + " x-role='" + X.encodeAsPath(r.title) + "'"
                 + "><span class='rmicon'></span></span></td></tr>";
    });
    view.content("roles", content);

    content = "";
    Y.each(groups, function(g) {
      content += "<tr><td style='padding-top:0.1em'>"
                 + _self.groupLink(instance, g)
                 + "</td><td align='right' style='padding-top:0.1em'>"
                 + g.members.length + "</td><td>"
                 + "<span class='rmbutton rmgroup' title='Remove item'"
                 + " x-group='" + X.encodeAsPath(g.name) + "'"
                 + "><span class='rmicon'></span></span></td></tr>";
    });
    view.content("groups", content);

    content = "";
    Y.each(federations, function(g) {
      content += "<tr><td style='padding-top:0.1em'>"
                 + g.country +"</td>"
                 + "<td style='padding-top:0.1em'>"
                 + _self.federationLink(instance, g)
                 + "</td><td align='right' style='padding-top:0.1em'>"+ g.site_count
                 + "</td></tr>";
    });
    view.content("federations", content);

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

  /** Manage group membership. For unprivileged users just show the
      members for this group for various different roles. For global
      and group admins allow adding and removing members. */
  this.manageGroup = function(req)
  {
    var name = unescape(req.params.name);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.loading(state);
    _state = state;
    var rolesByCName = {}, groupsByCName = {};
    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    var groups = Y.Object.values(state.groupsByName).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    Y.each(roles, function(i) { rolesByCName[i.canonical_name] = i; });
    Y.each(groups, function(i) { groupsByCName[i.canonical_name] = i; });
    var isgadmin = state.isGlobalAdmin();
    var isadmin = (state.isGlobalAdmin()
                   || state.hasGroupRole("Global Admin", name)
                   || state.hasGroupRole("Admin", name));
    var obj, title, content;
    var section = "Group";
    if (name in groupsByCName)
      obj = groupsByCName[name], title = obj.name;
    else if (state.complete)
    {
      gui.history.replace("/" + instance + "/admin");
      return;
    }

    var view = _views.attach("group", _self.doc);
    view.__group = obj && name;
    view.once(_selectPerson, state, view, "person", function(p) {
      _addRoleMember(view.valueOf("role"), null, view.__group, p);
    });

    content = "<option value=''>Select role</option>";
    Y.each(isadmin ? roles : [], function(r) {
      content += "<option value='" + X.encodeAsPath(r.canonical_name)
                 + "'>" + Y.Escape.html(r.title) + "</option>";
    });
    view.content("role", content);

    _self.title(state, title, section + "s", "Admin");
    if (obj)
    {
      view.content("title", section + " " + Y.Escape.html(title)
                   + " [" + Y.Escape.html(obj.canonical_name) + "]");

      content = "";
      Y.each(roles, function(r) {
        if (obj.name in r.group)
        {
          var v = r.group[obj.name];

          content += "<tr><td rowspan='" + v.length + "'><span style='font-weight: bold;'>"
                     + Y.Escape.html(r.title)+ "</span>";
          content += "</td>";

          Y.each(v, function(p, ix) {
            content += (ix ? "<tr>" : "") + "<td>"
                       + "<span class='rmbutton rmitem' title='Remove item'"
                       + " x-role='" + X.encodeAsPath(r.title) + "'"
                       + " x-group='" + X.encodeAsPath(obj.name) + "'"
                       + " x-person='" + X.encodeAsPath(p.username) + "'"
                       + " x-admin='" + (isadmin ? "yes" : "no") + "'"
                       + "><span class='rmicon'></span></span>"
                       + _self.personLink(instance, p)
                       + "</td></tr>";
          });
        }
      });
      view.content("members", content);
    }
    else
    {
      view.content("title", "Loading...");
      view.content("members", "");
    }

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

  /** Manage role membership. For unprivileged users just show the
      members for this role for various different groups and/or sites.
      For global and group admins allow adding and removing members. */
  this.manageRole = function(req)
  {
    var name = unescape(req.params.name);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.loading(state);
    _state = state;

    var rolesByCName = {}, groupsByCName = {};
    var sites = Y.Object.values(state.sitesByCMS).sort(state.sortSite);
    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    var groups = Y.Object.values(state.groupsByName).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    Y.each(roles, function(i) { rolesByCName[i.canonical_name] = i; });
    Y.each(groups, function(i) { groupsByCName[i.canonical_name] = i; });
    var isgadmin = state.isGlobalAdmin();
    var obj, title, content;
    var section = "Role";
    var description = '';
    if (name in rolesByCName){
      obj = rolesByCName[name], title = obj.title; description = obj.description;}
    else if (state.complete)
    {
      gui.history.replace("/" + instance + "/admin");
      return;
    }
    var view = _views.attach("role", _self.doc);
    view.__role = obj && name;
    view.once(_selectPerson, state, view, "group-person", function(p) {
      _addRoleMember(view.__role, null, view.valueOf("group"), p);
    });
    view.once(_selectPerson, state, view, "site-person", function(p) {
      _addRoleMember(view.__role, view.valueOf("site"), null, p);
    });

    view.validator("r-description", X.rxvalidate(gui.rx.DESCRIPTION, true));
    view.on("r-description", "keypress", function(e) {
      if (e.keyCode == 13) _createDescription(title,view.valueOf("r-description"));
    });
    if(description) view.content("role-description", description);
    content = "<option value=''>Select group</option>";
    Y.each(groups, function(g) {
      if (isgadmin
          || state.hasGroupRole("Global Admin", g.name)
          || state.hasGroupRole("Admin", g.name))
        content += "<option value='" + X.encodeAsPath(g.canonical_name)
                   + "'>" + Y.Escape.html(g.name) + "</option>";
    });
    view.content("group", content);

    content = "<option value=''>Select site</option>";
    Y.each(sites, function(s) {
      if (isgadmin || state.hasSiteRole("Site Executive", s.canonical_name))
        content += "<option value='" + X.encodeAsPath(s.canonical_name)
                   + "'>" + Y.Escape.html(s.canonical_name) + "</option>";
    });
    view.content("site", content);

    _self.title(state, title, section + "s", "Admin");
    if (obj)
    {
      view.content("title", section + " " + Y.Escape.html(title)
                   + " [" + Y.Escape.html(obj.canonical_name) + "]");

      content = "";
      Y.each(groups, function(g) {
        if (g.name in obj.group)
        {
          var v = obj.group[g.name];
          content += "<tr><td rowspan='" + v.length + "'><span style='font-weight: bold;'>"
                     + Y.Escape.html(g.name) + "</span>";
          content += "</td>";

          Y.each(v, function(p, ix) {
            var isadmin = isgadmin
                          || state.hasGroupRole("Global Admin", g.name)
                          || state.hasGroupRole("Admin", g.name);
            content += (ix ? "<tr>" : "") + "<td>"
                       + "<span class='rmbutton rmitem' title='Remove item'"
                       + " x-role='" + X.encodeAsPath(obj.title) + "'"
                       + " x-group='" + X.encodeAsPath(g.name) + "'"
                       + " x-person='" + X.encodeAsPath(p.username) + "'"
                       + " x-admin='" + (isadmin ? "yes" : "no") + "'"
                       + "><span class='rmicon'></span></span>"
                       + _self.personLink(instance, p)
                       + "</td></tr>";
          });
        }
      });
      view.content("group-members", content);

      content = "";
      Y.each(sites, function(s) {
        if (s.site_name in obj.site)
        {
          var admin = isgadmin || state.hasSiteRole("Site Executive", s.site_name);
          var v = obj.site[s.site_name];
          content += "<tr><td rowspan='" + v.length + "'>"
                     + Y.Escape.html(s.canonical_name) + "</td>";
          Y.each(v, function(p, ix) {
            content += (ix ? "<tr>" : "") + "<td>"
                       + "<span class='rmbutton rmitem' title='Remove item'"
                       + " x-role='" + X.encodeAsPath(obj.title) + "'"
                       + " x-site='" + X.encodeAsPath(s.canonical_name) + "'"
                       + " x-person='" + X.encodeAsPath(p.username) + "'"
                       + " x-admin='" + (admin ? "yes" : "no") + "'"
                       + "><span class='rmicon'></span></span>"
                       + _self.personLink(instance, p)
                       + "</td></tr>";
          });
        }
      });
      view.content("site-members", content);
    }
    else
    {
      view.content("title", "Loading...");
      view.content("group-members", "");
      view.content("site-members", "");
    }

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      var isadmin = X.getDOMAttr(n, "x-admin") == "yes";
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select").each(function(n) {
      var isadmin = n.get("children").size() > 1;
      var input = n.ancestor("tr").one("input");
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
      input.set("disabled", !isadmin);
      input.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all(".description-area").each(function(n) {
      n.setStyle("display", isgadmin ? "" : "none");
      });

  };

  /** Manage site roles. For unprivileged users just show the members for
      this site for various different roles. For global admins and the
      site executives allow adding and removing members. */
  this.manageSite = function(req)
  {
    var name = unescape(req.params.name);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.loading(state);
    _state = state;

    var rolesByCName = {};
    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });
    Y.each(roles, function(i) { rolesByCName[i.canonical_name] = i; });

    var isadmin = (state.isGlobalAdmin()
                   || state.hasSiteRole("Site Executive", name));
    var obj, title, content;
    var section = "Site";
    if (name in state.sitesByCMS)
      obj = state.sitesByCMS[name], title = obj.canonical_name;
    else if (state.complete)
    {
      gui.history.replace("/" + instance + "/admin");
      return;
    }

    var view = _views.attach("site", _self.doc);
    view.__site = obj && name;
    view.once(_selectPerson, state, view, "person", function(p) {
      _addRoleMember(view.valueOf("role"), view.__site, null, p);
    });

    content = "<option value=''>Select role</option>";
    Y.each(isadmin ? roles : [], function(r) {
      content += "<option value='" + X.encodeAsPath(r.canonical_name)
                 + "'>" + Y.Escape.html(r.title) + "</option>";
    });
    view.content("role", content);

    _self.title(state, title, section + "s", "Admin");
    if (obj)
    {
      view.content("title", section + " " + Y.Escape.html(title));

      content = "";
      Y.each(roles, function(r) {
        if (r.title in obj.responsibilities)
        {
          var v = obj.responsibilities[r.title];
          content += "<tr><td rowspan='" + v.length + "'>"
                     + Y.Escape.html(r.title) + "</td>";
          Y.each(v, function(p, ix) {
            content += (ix ? "<tr>" : "") + "<td>"
                       + "<span class='rmbutton rmitem' title='Remove item'"
                       + " x-role='" + X.encodeAsPath(r.title) + "'"
                       + " x-site='" + X.encodeAsPath(obj.canonical_name) + "'"
                       + " x-person='" + X.encodeAsPath(p.username) + "'"
                       + " x-admin='" + (isadmin ? "yes" : "no") + "'"
                       + "><span class='rmicon'></span></span>"
                       + _self.personLink(instance, p)
                       + "</td></tr>";
          });
        }
      });
      view.content("members", content);
    }
    else
    {
      view.content("title", "Loading...");
      view.content("members", "");
    }

    view.render();
    _self.doc.all(".rmbutton").each(function(n) {
      n.setStyle("display", isadmin ? "" : "none");
    });
    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
  };

 this.manageFederation = function(req)
  {
    var name = unescape(req.params.name);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.loading(state);
    _state = state;
    var rolesByCName = {};
    var federByCName = {};
    var federID = null;
    var federnames = {};
    var roles = Y.Object.values(state.federationsSites).sort(function(a, b) {
      return d3.ascending(a.name, b.name); });
    Y.each(roles, function(i) { rolesByCName[i.name] = i; });
    var allFederations = Y.Object.values(state.federationsById).sort(function(a, b) {
      return d3.ascending(a.name, b.name); });
    Y.each(allFederations, function(i) {federByCName[i.canonical_name] = i});
    var isadmin = (state.isGlobalAdmin());
    Y.each(state.federationsNames, function(i) {federnames[i.federations_names_id] = i});

    var isadmin = (state.isGlobalAdmin());
    var obj, title, content;
    var section = "Federation";
    if(name in federByCName){
       obj = state.federationsSites, title = federByCName[name].name;
       federID = federByCName[name].id;
    }else if (state.complete)
    {
       gui.history.replace("/" + instance + "/admin");
       return;
    }
   var view = _views.attach("federation", _self.doc);
   view.__site = obj && name;
    state.federID = federID;

    content = name;
    view.content("federations-select", content);

     _self.title(state, title, section + "s", "Admin");
    if (obj)
    {
      view.content("title", section + " " + Y.Escape.html(title));

    view.once(_selectSite, state, view, "group-federation", function(p) {
     _addFederationSite(view.valueOf("federations-select"), view.__site, null, p);
     });



      content = "";
      Y.each(roles, function(r) {
        if (r.fed_id == federID)
        {
        content += "<tr><td></td><td>";
        content += "<span class='rmbutton rmfederationsite' title='Remove item'";
        content += "x-id='"+X.encodeAsPath(r.site_id)+"'";
        content += "x-alias='"+X.encodeAsPath(r.alias)+"'";
        content += "><span class='rmicon'></span></span>"+ r.alias +"</td></tr>";
        }
      });
      view.content("federations", content);
    }
    else
    {
      view.content("title", "Loading...");
      view.content("federation", "");
    }

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
  gui.history.route("/:instance/admin", this.main);
  gui.history.route("/:instance/admin/group/:name", this.manageGroup);
  gui.history.route("/:instance/admin/role/:name", this.manageRole);
  gui.history.route("/:instance/admin/site/:name", this.manageSite);
  gui.history.route("/:instance/admin/federation/:name", this.manageFederation);
  // Response handle to window resize.
  this.onresize = function()
  {
    var newsize = { w: _doc.get("winWidth"), h: _doc.get("winHeight") };
  };

  return this;
});
