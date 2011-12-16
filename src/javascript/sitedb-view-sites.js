var Sites = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** 'None' text material. */
  var _none = "<span class='faded'>(None)</span>";

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Sites",
            ["whoami", "sites", "site-names", "site-resources",
             "site-associations", "resource-pledges", "pinned-software",
             "site-responsibilities"]);

  this.main = function(req)
  {
    var site = req.params.site ? unescape(req.params.site) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, site, "Sites");
    _self.loading(state);

    var sites = _self.doc.one("#site-list");
    var info = _self.doc.one("#site-info");
    if (_self.doc.get('children').size() != 2 || ! sites || ! info)
    {
      _self.doc.setContent
        ("<div id='site-list' style='width:95%; overflow:auto'></div>"
         + "<div id='site-info' style='width:95%; margin-top:10px'></div>");
      sites = _self.doc.one("#site-list");
      info = _self.doc.one("#site-info");
    }

    var h = (! site ? "inherit" : sprintf("%dpx", _self.doc.get('winHeight') * 0.4));
    if (sites.getStyle("height") != h)
      sites.setStyle("height", h);

    var sitelist;
    if (! sites.hasChildNodes())
      sites.setContent("<div style='width:100%;"
                       + X.multicolumn(150, 10)
                       + "'></div>");
    sitelist = sites.get('children').item(0);

    var content = "";
    Y.each(Object.keys(state.sitesByTier).sort(d3.ascending), function(t) {
      content += "<h3>" + Y.Escape.html(t) + "</h3>";
      Y.each(state.sitesByTier[t], function(s) {
        content += "<p>" + _self.siteLink(instance, s) + "</p>";
      });
    });
    if (sitelist.getContent() != content)
      sitelist.setContent(content);

    content = "";
    if (site)
    {
      var m = /^\((.*)\)$/.exec(site);
      var name = (m ? m[1] : site);
      var s = (m ? (name in state.sitesByName ? state.sitesByName[name] : null)
               : (name in state.sitesByCMS ? state.sitesByCMS[name] : null));
      if (s)
      {
        content +=
          ("<div style='width:100%;margin:0 0 10px;padding:5px;"
           + "border:1px solid #ddd;background-color:#eee'>"
           + "<h2>" + Y.Escape.html(name) + "</h2>");

        content +=
          ("<div class='group'><h3>"
           + _self.siteLink(instance, s, "Names", "/edit") + "</h3><table>"
           + "<tr><td><i>Title</i></td><td>" + Y.Escape.html(s.name)
           + "</td></tr><tr><td><i>CMS</i></td><td>"
           + ("cms" in s.name_alias
              ? s.name_alias.cms.map(Y.Escape.html).join("<br />")
              : _none)
           + "</td></tr><tr><td><i>PhEDEx</i></td><td>"
           + ("phedex" in s.name_alias
              ? s.name_alias.phedex.map(Y.Escape.html).join("<br />")
              : _none)
           + "</td></tr><tr><td><i>LCG</i></td><td>"
           + ("lcg" in s.name_alias
              ? s.name_alias.lcg.map(Y.Escape.html).join("<br />")
              : _none)
           + "</td></tr></table>"

           + "<h3>" + _self.siteLink(instance, s, "Associations", "/associations")
           + "</h3><table><tr><td><i>Parent</i></td><td>"
           + (s.parent_site ? _self.siteLink(instance, s.parent_site) : _none)
           + "</td></tr><tr><td><i>Children</i></td><td>"
           + s.child_sites.map(function(i) {
               return _self.siteLink(instance, i); }).join("<br />")
           + "</td></tr></table></div>");

        content +=
          ("<div class='group'><h3>"
           + _self.siteLink(instance, s, "Hosts", "/resources")
           + "</h3><table><tr><td><i>CEs</i></td><td>"
           + s.resources.CE.map(function(i) {
               return Y.Escape.html(i.fqdn); }).join("<br />")
           + "</td></tr><tr><td><i>SEs</i></td><td>"
           + s.resources.SE.map(function(i) {
               return Y.Escape.html(i.fqdn); }).join("<br />")
           + "</td></tr></table>"
           + "</div>");

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

        content +=
          ("<div class='group'><h3>"
           + _self.pledgeLink(instance, s, "Resource Pledge")
           + "</h3><table>"
           + "<tr><td><i>Quarter</i></td><td align='right' colspan='2'>"
           + (pledge ? quarter : _none)
           + "</td><td></td></tr><tr><td><i>Updated</i></td><td align='right'"
           + " colspan='2'>" + (pledge ? pledgeTime : _none)
           + "</td><td></td></tr><tr><td><i>CPU</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.cpu) : "-")
           + "</td><td>kSI2k</td></tr><tr><td><i>Slots</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.job_slots) : "-")
           + "</td><td>jobs</td></tr><tr><td colspan='3'><b>Storage</b>"
           + "</td></tr><tr><td><i>Disk</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.disk_store) : "-")
           + "</td><td>TB</td></tr><tr><td><i>Tape</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.tape_store) : "-")
           + "</td><td>TB</td></tr><tr><td><i>WAN</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.wan_store) : "-")
           + "</td><td>TB</td></tr><tr><td><i>Local</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.local_store) : "-")
           + "</td><td>TB</td></tr><tr><td colspan='3'><b>Bandwidth</b>"
           + "</td></tr><tr><td>National</td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.national_bandwidth) : "-")
           + "</td><td>Gbps</td></tr><tr><td><i>OPN</i></td>"
           + "<td align='right' style='padding-right: .5em'>"
           + (pledge ? Y.Escape.html(pledge.opn_bandwidth) : "-")
           + "</td><td>Gbps</td></tr></table>"
           + "</div>");

        content +=
           ("<div class='group'><h3>"
           + _self.siteLink(instance, s, "Responsibilities", "/contacts")
           + "</h3><dl>");
        var roles = Object.keys(s.responsibilities).sort(d3.ascending);
	Y.each(roles, function(role) {
	  content +=
            ("<dt>" + Y.Escape.html(role) + "</dt><dd>"
             + s.responsibilities[role].map(function(i) {
                 return _self.personLink(instance, i); }).join("<br />")
             + "</dd>");
        });

        content += "</dl></div></div>";
      }
    }

    if (info.getContent() != content)
      info.setContent(content);
  };

  this.create = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.remove = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.edit = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.contacts = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.software = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.names = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.resources = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  this.associations = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  // Handle history controller state.
  gui.history.route("/:instance/sites", this.main);
  gui.history.route("/:instance/sites/new", this.create);
  gui.history.route("/:instance/sites/delete", this.remove);
  gui.history.route("/:instance/sites/:site", this.main);
  gui.history.route("/:instance/sites/:site/edit", this.edit);
  gui.history.route("/:instance/sites/:site/contacts", this.contacts);
  gui.history.route("/:instance/sites/:site/software", this.config);
  gui.history.route("/:instance/sites/:site/names", this.names);
  gui.history.route("/:instance/sites/:site/resources", this.resources);
  gui.history.route("/:instance/sites/:site/associations", this.associations);

  return this;
});
