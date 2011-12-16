var Admin = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Admin",
            ["whoami", "roles", "groups", "people", "sites",
             "site-responsibilities", "group-responsibilities"]);

  var _initLists = function(state)
  {
    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });

    var groups = Y.Object.values(state.groupsByName).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });

    var nroles = Y.one("#admin-role-list");
    var ngroups = Y.one("#admin-group-list");
    var ninfo = Y.one("#admin-item");
    if (_self.doc.get('children').size() != 1 || !nroles || !ngroups || !ninfo)
    {
      _self.doc.setContent
        ("<div style='width:95%;margin:0 0 1em'>"

         + "<div class='group'><h2>Roles</h2><table>"
         + "<thead><tr><th style='text-align:left'>Name</th>"
         + "<th style='text-align:right'>Members</th></tr></thead>"
         + "<tbody id='admin-role-list'></tbody></table></div>"

         + "<div class='group'><h2>Groups</h2><table>"
         + "<thead><tr><th style='text-align:left'>Name</th>"
         + "<th style='text-align:right'>Members</th></tr></thead>"
         + "<tbody id='admin-group-list'></tbody></table></div>"

         + "<div id='admin-info' class='group' style='width:40%;display:none'>"
         + "</div></div>");

      nroles = Y.one("#admin-role-list");
      ngroups = Y.one("#admin-group-list");
      ninfo = Y.one("#admin-info");
    }

    return { state: state, roles: roles, groups: groups,
             nroles: nroles, ngroups: ngroups, ninfo: ninfo };
  };

  var _showLists = function(info)
  {
    var instance = info.state.currentInstance();
    var content = "";

    Y.each(info.roles, function(r) {
      content += "<tr><td style='padding-top:0.1em'>"
                 + _self.roleLink(instance, r)
                 + "</td><td align='right' style='padding-top:0.1em'>"
                 + r.members.length + "</td></tr>";
    });
    if (info.nroles.getContent() != content)
      info.nroles.setContent(content);

    content = "";
    Y.each(info.groups, function(g) {
      content += "<tr><td style='padding-top:0.1em'>"
                 + _self.groupLink(instance, g)
                 + "</td><td align='right' style='padding-top:0.1em'>"
                 + g.members.length + "</td></tr>";
    });
    if (info.ngroups.getContent() != content)
      info.ngroups.setContent(content);
  };

  this.main = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Admin");
    _self.loading(state);

    var info = _initLists(state);
    if (info.ninfo.getStyle("display") != "none")
      info.ninfo.setStyle("display", "none");
    if (info.ninfo.getContent() != "")
      info.ninfo.setContent("");
    _showLists(info);
  };

  this.create = function(req)
  {
    var state = _self.require.call(_self, req.params.instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.remove = function(req)
  {
    var state = _self.require.call(_self, req.params.instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.manage = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.loading(state);

    var info = _initLists(state);
    var type = unescape(req.params.type);
    var name = unescape(req.params.name);
    var rolesByCName = {}, groupsByCName = {};
    Y.each(info.roles, function(i) { rolesByCName[i.canonical_name] = i; });
    Y.each(info.groups, function(i) { groupsByCName[i.canonical_name] = i; });

    var obj, title;
    var section = type.charAt(0).toUpperCase()+type.slice(1);
    if (type == "group" && name in groupsByCName)
      obj = groupsByCName[name], title = obj.name;
    else if (type == "role" && name in rolesByCName)
      obj = rolesByCName[name], title = obj.title;
    else if (state.complete)
    {
      gui.history.replace("/" + instance + "/admin");
      return;
    }

    _self.title(state, title, section + "s", "Admin");
    _showLists(info);

    var content = "";
    if (obj)
    {
      content += "<h2>" + section + " " + Y.Escape.html(title)
                 + " [" + Y.Escape.html(obj.canonical_name) + "]</h2>";
      if ("site" in obj)
      {
        var list = Object.keys(obj.site).sort(d3.ascending);
        if (list.length)
        {
          content += "<dl><dt>Sites</dt><dd>";
          Y.each(list, function(i, ix) {
            content += (ix ? ", " : "")
              + _self.siteLink(instance, state.sitesByName[i]);
          });
          content += "</dd></dl>";
        }
      }
      if ("group" in obj)
      {
        var list = Object.keys(obj.group).sort(d3.ascending);
        if (list.length)
        {
          content += "<dl><dt>Groups</dt><dd>";
          Y.each(list, function(i, ix) {
            content += (ix ? ", " : "")
              + _self.groupLink(instance, state.groupsByName[i]);
          });
          content += "</dd></dl>";
        }
      }

      if ("name" in obj)
      {
        var list = Y.Array.filter(info.roles,function(r) {
          return obj.name in r.group; });

        if (list.length)
        {
          content += "<dl><dt>Roles</dt><dd>";
          Y.each(list, function(i, ix) {
            content += (ix ? ", " : "") + _self.roleLink(instance, i);
          });
          content += "</dd></dl>";
        }
      }

      content += "<dl><dt>Members</dt><dd>";
      if (obj.members.length)
        Y.each(obj.members, function(i, ix) {
          content += (ix ? ", " : "") + _self.personLink(instance, i);
        });
      else
        content += "<p class='faded'>(None)</p>";
      content += "</dd></dl>";
    }

    if (info.ninfo.getContent() != content)
      info.ninfo.setContent(content);
    if (info.ninfo.getStyle("display") != "")
      info.ninfo.setStyle("display", "");
  };

  // Handle history controller state.
  gui.history.route("/:instance/admin", this.main);
  gui.history.route("/:instance/admin/new/:type", this.create);
  gui.history.route("/:instance/admin/delete/:type", this.remove);
  gui.history.route("/:instance/admin/:type/:name", this.manage);

  // Response handle to window resize.
  this.onresize = function()
  {
    var newsize = { w: _doc.get("winWidth"), h: _doc.get("winHeight") };
  };

  return this;
});
