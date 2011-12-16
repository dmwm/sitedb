var People = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** 'None' text material. */
  var _none = "<span class='faded'>(None)</span>";

  /** Flag to indicate if we are in charge of dynamic data. */
  var _incharge = false;

  /** Subscription for history events, to determine who owns search value. */
  var _historyEvent = null;

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "People",
            ["whoami", "people", "site-responsibilities",
             "group-responsibilities"]);

  var _search = function(count, result, state, term)
  {
    var rx = null;
    var match = [];
    var attrs = [ 'forename', 'surname', 'email' ];
    var instance = state.currentInstance();
    var people = state.people;

    if (! people.length)
    {
      count.setContent("Hey, where'd everybody go?");
      result.setContent("");
      return;
    }

    if (! term)
      match = people.map(function(p) { return { len: 0, start: 0, person: p } });
    else
    {
      term = term.replace(/^\s+/, "").replace(/\s+$/, "").replace(/\s+/g, " ");
      try { rx = term.split(" ").map(function(t) { return new RegExp(t, "i") }); }
      catch (e) { result.setContent("No matches"); return; }

      Y.each(people, function(p) {
        var m, best = { n: 0, len: 0, start: Infinity, person: p };
        for (var r = 0; r < rx.length; ++r)
        {
          var matched = false;

          for (var a = 0; a < attrs.length; ++a)
            if ((m = rx[r].exec(p[attrs[a]])))
            {
	      matched = true;
              best.len += m[0].length;
	      best.start = Math.min(best.low, m.index);
	    }

          if (matched)
            best.n++;
        }

        if (best.n == rx.length)
          match.push(best);
      });
    }

    if (! match.length)
    {
      count.setContent("Sorry, nobody by that name here.");
      result.setContent("");
      return;
    }

    var content = "";
    if (match.length > 60)
      Y.each(match, function(m) {
        content += "<p>" + _self.personLink(instance, m.person) + "</p>";
      });
    else
      Y.each(match, function(m) {
        var p = m.person;
        var email = p.email && Y.Escape.html(p.email.toLowerCase()).replace("@", "&#8203;@");
        var sites = Object.keys(p.sites).sort(d3.ascending);
        var groups = Object.keys(p.groups).sort(d3.ascending);
        var roles = Object.keys(p.roles).sort(d3.ascending);

        content +=
          ("<div style='display:inline-block;width:180px;margin-bottom:1em;"
           + "border-top:1px dotted #ddd;padding-top:.5em'>"
           + "<h4>" + _self.personLink(instance, m.person) + "</h4>"
           + (! p.email ? ""
              : "<dl class='mini'><dt title='E-mail address'>M</dt><dd>"
                + _self.mailto(p.email, email) + "</dd></dl>")
           + (! p.phone1 ? ""
              : "<dl class='mini'><dt title='Telephone'>T</dt><dd class='faded'>"
                + Y.Escape.html(p.phone1)
                + (! p.phone2 ? ""
                   : "</dd><dd class='faded'>" + Y.Escape.html(p.phone2) + "</dd>")
                + "</dd></dl>")
           + (! p.im_handle ? ""
              : "<dl class='mini'><dt title='Instant message handle'>I</dt>"
                + "<dd class='faded' style='font-size:.9em'>"
                + Y.Escape.html(p.im_handle) + "</dd></dl>")
           + (! p.username ? ""
              : "<dl class='mini'><dt title='CMS HyperNews Account'>A</dt>"
                + "<dd class='faded' style='font-size:.9em'>"
                + Y.Escape.html(p.username) + "</dd></dl>")
           + (! p.dn ? ""
              : "<dl class='mini'><dt title='X509 certificate'>X</dt>"
                + "<dd class='faded' style='font-size:.9em'>"
                + Y.Escape.html(p.dn).replace(/&#x2F;/g, "&#8203;&#x2F;")
                + "</dd></dl>"));

        if (sites.length)
        {
          content += "<dl class='mini'><dt title='Sites'>@</dt>";
          Y.each(sites, function(i) {
            content += "<dd>" + _self.siteLink(instance, p.sites[i]) + "</dd>";
          });
          content += "</dl>";
        }

        if (groups.length)
        {
          content += "<dl class='mini'><dt title='Groups'>G</dt>";
          Y.each(groups, function(i) {
            content += "<dd>" + _self.groupLink(instance, p.groups[i]) + "</dd>";
          });
          content += "</dl>";
        }

        if (roles.length)
        {
          content += "<dl class='mini'><dt title='Roles'>R</dt>";
          Y.each(roles, function(i) {
            content += "<dd>" + _self.roleLink(instance, state.rolesByTitle[i]) + "</dd>";
          });
          content += "</dl>";
        }

        content += "</div>";
      });

    if (result.getContent() != content)
      result.setContent(content);

    content = match.length + " people found";
    if (count.getContent() != content)
      count.setContent(content);
  };

  /** Respond to internal navigation. Resets in-charge flag so that we
      reset search field. */
  this.prenavigate = function()
  {
    _incharge = false;
  };

  /** Attach this view. Adds listener for history event to help decide
      who is in charge of the search edit field contents. If we did not
      trigger the history transition ourselves, then lose the ownership
      of the search field; otherwise ignore the changes and leave field
      unchanged. */
  this.attach = function()
  {
    _incharge = false;
    _historyEvent = Y.on("history:change", function(e) {
      if (e.src != "add" && e.src != "replace")
        _incharge = false;
    });
  };

  /** Detach this view. Detaches the history event listener. */
  this.detach = function()
  {
    _incharge = false;
    if (_historyEvent)
      _historyEvent.detach();
  };

  /** Show the main page: search and show summary details of people. */
  this.main = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, req.query.search && "Search: "+req.query.search, "People");
    _self.loading(state);

    var search = _self.doc.one("#search");
    var count = _self.doc.one("#search-count");
    var result = _self.doc.one("#search-result");
    if (_self.doc.get("children").size() != 3 || ! search || ! result || ! count)
    {
      _self.doc.setContent
        ("<div style='margin:auto;padding:0 0 .5em;width:50%;font-size:1.7em'>"
         + "<input id='search' style='width:100%;padding:3px' type='text' "
         + "title='Search CMS people by name or e-mail address' /></div>"
         + "<div id='search-count' style='margin:auto;width:50%;"
         + "padding:0 0 1em;text-align:center' class='faded'></div>"
         + "<div id='search-result' style='width:95%;"
         + X.multicolumn(180, 10, "1px dotted #ddd")
         + "'></div>");
      search = _self.doc.one("#search");
      count = _self.doc.one("#search-count");
      result = _self.doc.one("#search-result");

      // Whenever search field changes, grab ownership. We relinquish that
      // control on history events, and/or if the view is attached/detached.
      var dosearch = null, dohist = null;
      search.on('valueChange', function(e) {
        _incharge = true;

        if (dosearch) dosearch.cancel();
        if (dohist) dohist.cancel();

        dohist = Y.later(1000, _self, function() {
          var term = search.get('value');
          var tail = term ? "?search=" + X.encodeAsPath(term) : "";
          gui.history.save(gui.history.getPath() + tail);
        });

        dosearch = Y.later(150, _self, function() {
          _search(count, result, state, search.get('value'));
        });
      });
    }

    // If we are not in charge of the search field, i.e. haven't been
    // editing it locally, then force it to synchronise, and put focus
    // on it so the user doesn't need to click on it / tab to it.
    if (! _incharge)
    {
      var s = req.query.search || "";
      if (search.get('value') != s)
        search.set('value', s);
      search.getDOMNode().focus();
      _incharge = true;
    }

    // Make sure search results reflect whatever is the current state.
    _search(count, result, state, search.get('value'));
  };

  this.me = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    if (state.whoami)
    {
      req.params.person = state.whoami.login;
      _self.person(req);
    }
  };

  this.person = function(req)
  {
    var content = "";
    var person = unescape(req.params.person);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var p = ((person in state.peopleByHN) && state.peopleByHN[person])
            || ((person in state.peopleByMail) && state.peopleByMail[person]);
    _self.title(state, p ? p.fullname : person, "People");
    _self.loading(state);

    if (p)
    {
      content +=
        ("<div style='margin-bottom:1em'><h2>"
         + Y.Escape.html(p.fullname)
         + (! p.email ? "" : " | " + _self.mailto(p.email))
         + (! p.username ? "" : " [" + Y.Escape.html(p.username) + "]")
         + "</h2>"
         + (! p.dn ? "" : "<p class='faded'>" + Y.Escape.html(p.dn) + "</p>")
         + "<p class='faded'>"
         + (! p.phone1 ? "No phone"
            : Y.Escape.html(p.phone1)
              + (! p.phone2 ? "" : ", " + Y.Escape.html(p.phone2)))
         + (! p.im_handle ? "" : " | IM: " + Y.Escape.html(p.im_handle))
         + "</p></div>");

      content += "<div class='group'><h3>Site Responsibilities</h3><dl>";
      var roles = Object.keys(p.roles).sort(d3.ascending);
      var nfound = 0;
      Y.each(roles, function(r) {
        var items = p.roles[r].site;
        if (items.length)
          content +=
            ("<dt>" + Y.Escape.html(r) + "</dt><dd>"
             + items.map(function(s) {
                 return _self.siteLink(instance, s); }).join("<br />")
             + "</dd>");
        nfound += items.length;
      });
      if (! nfound)
        content += "<dt>" + _none + "</dt><dd></dd>";
      content += "</dl></div>";

      nfound = 0;
      content += "<div class='group'><h3>Group Responsibilities</h3><dl>";
      Y.each(roles, function(r) {
        var items = p.roles[r].group;
        if (items.length)
          content +=
            ("<dt>" + Y.Escape.html(r) + "</dt><dd>"
             + items.map(function(g) {
                 return _self.groupLink(instance, g); }).join("<br />")
             + "</dd>");
        nfound += items.length;
      });
      if (! nfound)
        content += "<dt>" + _none + "</dt><dd></dd>";
      content += "</dl></div></div>";
    }
    else if (state.complete)
      content += "<p>No such person.</p>";

    if (_self.doc.getContent() != content)
      _self.doc.setContent(content);
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

  // Handle history controller state.
  gui.history.route("/:instance/people", this.main);
  gui.history.route("/:instance/people/me", this.me);
  gui.history.route("/:instance/people/new", this.create);
  gui.history.route("/:instance/people/delete", this.remove);
  gui.history.route("/:instance/people/:person", this.person);

  return this;
});
