var People = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** 'None' text material. */
  var _none = "<span class='faded'>(None)</span>";

  /** Subscription for history events, to determine who owns search value. */
  var _historyEvent = null;

  /** View master objects. */
  var _views = new ViewContentSet(Y, {
    loading: "view-loading",
    authfail: "view-auth-fail",
    nosuch: "view-no-such",
    nox509: "view-no-x509",
    main: "view-people-main",
    person: "view-people-person",
    remove: "view-people-remove",
    edit: "view-people-edit",
    mycert: "view-people-mycert"
  });

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "People",
            ["whoami", "people", "site-responsibilities",
             "group-responsibilities"]);

  /** Respond to search results on people page. Execute the search and
      fill the result area with people's information. Show just people's
      names if there are a lot of results, otherwise show inline a little
      more information for each person. Searches are regexp terms which
      are matched over forename, surename and email address. */
  var _search = function(view, state)
  {
    var rx = null;
    var match = [];
    var term = view.valueOf("search");
    var attrs = [ 'forename', 'surname', 'email' ];
    var instance = state.currentInstance();
    var people = state.people;

    if (! people.length)
    {
      view.content("count", "Hey, where'd everybody go?");
      view.content("result", "");
      view.render();
      return;
    }

    if (! term)
      match = people.map(function(p) { return { len: 0, start: 0, person: p } });
    else
    {
      term = term.replace(/\s+/g, " ");
      try { rx = term.split(" ").map(function(t) { return new RegExp(t, "i") }); }
      catch (e) { view.content("result", "No matches"); view.render(); return; }

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
      view.content("count", "Sorry, nobody by that name here.");
      view.content("result", "");
      view.render();
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

    view.content("result", content);
    view.content("count", match.length + " people found");
    view.render();
  };

  /** Implement editing person's details, including creating a new record. */
  var _edit = function(isnew, state, person, p)
  {
    var view = _views.attach("edit", _self.doc);
    view.validator("surname", X.rxvalidate(gui.rx.NAME));
    view.validator("forename", X.rxvalidate(gui.rx.NAME));
    view.validator("dn", X.rxvalidate(gui.rx.DN));
    view.validator("account", X.rxvalidate(gui.rx.USER));
    view.validator("email", X.rxvalidate(gui.rx.EMAIL));
    view.validator("phone1", X.rxvalidate(gui.rx.PHONE, true));
    view.validator("phone2", X.rxvalidate(gui.rx.PHONE, true));
    view.validator("imname", function(imname) {
      var imtype   = view.valueOf("imtype");
      var imhandle = ((imtype && imname) ? (imtype + ":" + imname) : "");
      return gui.rx.IM.test(imhandle);
    });

    view.on("update", "click", function(e) {
      var surname  = view.valueOf("surname");
      var forename = view.valueOf("forename");
      var dn       = view.valueOf("dn");
      var account  = view.valueOf("account");
      var email    = view.valueOf("email");
      var phone1   = view.valueOf("phone1");
      var phone2   = view.valueOf("phone2");
      var imtype   = view.valueOf("imtype");
      var imname   = view.valueOf("imname");
      var imhandle = (imtype && imname ? imtype + ":" + imname : "");

      state.modify([{
        method: (isnew ? "PUT" : "POST"), entity: "people",
        data: { "surname": surname, "forename": forename, "dn": dn,
                "username": account, "email": email, "phone1": phone1,
                "phone2": phone2, "im_handle": imhandle },
        message: (isnew ? "Inserting" : "Updating") + " record for "
                 + Y.Escape.html(email)
      }]);
    });

    if (p || isnew)
      view.content("title", (isnew ? "Register" : "Edit")
                   + " profile for " + person);
    else
      view.content("title", "Loading...");

    view.style("form", "display", (p || isnew) ? "" : "none");
    view.value("surname", (p && p.surname) || "");
    view.value("forename", (p && p.forename) || "");
    view.value("dn", (p && p.dn) || "");
    view.enable("dn", state.isGlobalAdmin());
    view.value("account", (p && p.username) || "");
    view.value("email", (p && p.email) || "");
    view.value("phone1", (p && p.phone1) || "");
    view.value("phone2", (p && p.phone2) || "");
    var im = ((p && p.im_handle) || "").match(/^([a-z]+):(.*)$/);
    if (im)
    {
      var imtype = im[1];
      var imname = im[2];
      if (imname == "none" || imtype == "none")
        imtype = imname = "";

      view.value("imtype", imtype);
      view.value("imname", imname);
    }
    else
    {
      view.value("imtype", "");
      view.value("imname", "");
    }
    view.content("update", isnew ? "Register" : "Update");
    view.focus("surname");
    view.render();
  };

  /** Action handler for account-certificate association. */
  var _mycert = function(state, account, password)
  {
    if (account && password)
      state.modify([{
        method: "POST", entity: "mycert",
        data: { "username": account, "passwd": password },
        message: "Associating " + Y.Escape.html(account)
      }]);
  };

  /** Respond to internal navigation. Resets in-charge flag so that we
      reset search field and other local edit contents. */
  this.prenavigate = function()
  {
    _views.loseValues();
  };

  /** Attach this view. Adds listener for history event to help decide
      who is in charge of the search edit field contents. If we did not
      trigger the history transition ourselves, then lose the ownership
      of the search and other edit fields field; otherwise ignore the
      changes and leave field unchanged. */
  this.attach = function()
  {
    _views.loseValues();
    _historyEvent = Y.on("history:change", function(e) {
      if (e.src != "add" && e.src != "replace")
        _views.loseValues();
    });
  };

  /** Detach this view. Detaches the view and history event listener. */
  this.detach = function()
  {
    _views.detach();
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

    var view = _views.attach("main", _self.doc);
    view.once(function() {
      var dosearch = null, dohist = null;
      view.on("search", "valueChange", function(e) {
        if (dosearch) dosearch.cancel();
        if (dohist) dohist.cancel();

        dohist = Y.later(1000, _self, function() {
          var term = view.valueOf("search");
          var tail = term ? "?search=" + X.encodeAsPath(term) : "";
          if (tail != window.location.search)
            gui.history.save(gui.history.getPath() + tail);
        });

        dosearch = Y.later(150, _self, function() {
          _search(view, state);
        });
      });
    });

    // If we are not in charge of the search field, i.e. haven't been
    // editing it locally, then force it to synchronise, and put focus
    // on it so the user doesn't need to click on it / tab to it.
    if (! view.incharge("search"))
    {
      var s = req.query.search || "";
      view.value("search", s, true);
      view.focus("search");
    }

    // Make sure search results reflect whatever is the current state.
    _search(view, state);
  };

  /** Custom person display for the authenticated user. */
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

  /** Show more extended information for a single person. */
  this.person = function(req)
  {
    var person = unescape(req.params.person);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var p = ((person in state.peopleByHN) && state.peopleByHN[person]);
    _self.title(state, p ? p.fullname : person, "People");
    _self.loading(state);

    var view = _views.attach("person", _self.doc);
    if (p)
    {
      view.style("details", "display", "");
      view.content("title", Y.Escape.html(p.fullname)
                   + (! p.email ? "" : " | " + _self.mailto(p.email))
                   + (! p.username ? "" : " [" + Y.Escape.html(p.username) + "]"));

      view.content("dn", p.dn ? Y.Escape.html(p.dn) : "");
      view.style("dn", "display", p.dn ? "" : "none");

      view.content("contact",
                   (! p.phone1 ? "No phone"
                    : Y.Escape.html(p.phone1)
                      + (! p.phone2 ? "" : ", " + Y.Escape.html(p.phone2)))
                   + (! p.im_handle ? "" : " | IM: " + Y.Escape.html(p.im_handle)));

      var content = "";
      if (state.whoami.person == p || state.isGlobalAdmin())
        content += _self.personLink(instance, p, "Edit...", "/edit");
      if (state.isGlobalAdmin())
        content += " | " + _self.personLink(instance, p, "Delete", "/remove");
      view.content("links", content);
      view.style("links", "display", content ? "" : "none");

      content = "";
      var roles = Object.keys(p.roles).sort(d3.ascending);
      Y.each(roles, function(r) {
        var items = p.roles[r].site;
        if (items.length)
          content +=
            ("<dt>" + Y.Escape.html(r) + "</dt><dd>"
             + items.map(function(s) {
                 return _self.siteLink(instance, s); }).join("<br />")
             + "</dd>");
      });
      view.content("sites", content || ("<dt>" + _none + "</dt><dd></dd>"));

      content = "";
      Y.each(roles, function(r) {
        var items = p.roles[r].group;
        if (items.length)
          content +=
            ("<dt>" + Y.Escape.html(r) + "</dt><dd>"
             + items.map(function(g) {
                 return _self.groupLink(instance, g); }).join("<br />")
             + "</dd>");
      });
      view.content("groups", content || ("<dt>" + _none + "</dt><dd></dd>"));
    }
    else
    {
      view.content("title", state.complete ? "No such person" : "Loading...");
      view.style("details", "display", "none");
    }

    view.render();
  };

  /** Page for global admins to create new people records. */
  this.create = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "New person", "People");
    _self.loading(state);

    if (state.isGlobalAdmin())
      _edit(true, state, "new person", null);
    else
    {
      var view;
      if (state.whoami)
      {
        view = _views.attach("authfail", _self.doc);
        view.content("what", "add");
      }
      else
        view = _views.attach("loading", _self.doc);
      view.render();
    }
  };

  /** Page for global admins to remove people records. */
  this.remove = function(req)
  {
    var view;
    var person = unescape(req.params.person);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var p = ((person in state.peopleByHN) && state.peopleByHN[person]);
    _self.title(state, "Remove", p ? p.fullname : person, "People");
    _self.loading(state);

    if (p && state.isGlobalAdmin())
    {
      view = _views.attach("remove", _self.doc);
      view.style("details", "display", "");
      view.content("title", Y.Escape.html(p.fullname)
                   + (! p.email ? "" : " | " + _self.mailto(p.email))
                   + (! p.username ? "" : " [" + Y.Escape.html(p.username) + "]"));

      view.content("dn", p.dn ? Y.Escape.html(p.dn) : "");
      view.style("dn", "display", p.dn ? "" : "none");

      view.content("contact",
                   (! p.phone1 ? "No phone"
                    : Y.Escape.html(p.phone1)
                      + (! p.phone2 ? "" : ", " + Y.Escape.html(p.phone2)))
                   + (! p.im_handle ? "" : " | IM: " + Y.Escape.html(p.im_handle)));

      view.on("remove", "click", function(e) {
        state.modify([{
          method: "DELETE", entity: "people", data: { "username": p.username },
          invalidate: [ "whoami", "site-responsibilities", "group-responsibilities" ],
          message: "Removing record for '" + Y.Escape.html(p.fullname) + "'",
          onsuccess: function(){ gui.history.save("/" + instance + "/people"); }
        }]);
      });
    }
    else if (state.whoami && ! state.isGlobalAdmin())
    {
      view = _views.attach("authfail", _self.doc);
      view.content("what", "remove");
    }
    else if (state.complete)
    {
      view = _views.attach("nosuch", _self.doc);
      view.content("what", "person");
    }
    else
      view = _views.attach("loading", _self.doc);

    view.render();
  };

  /** Page for global admins and person themselves to edit the record. */
  this.edit = function(req)
  {
    var person = unescape(req.params.person);
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var p = ((person in state.peopleByHN) && state.peopleByHN[person]);
    _self.title(state, "Edit", p ? p.fullname : person, "People");
    _self.loading(state);

    if (! state.whoami
        || ! state.whoami.person
        || (p && p == state.whoami.person)
        || (p && state.isGlobalAdmin()))
      _edit(false, state, (p ? p.fullname : person), p);
    else if (p && state.whoami)
    {
      var view = _views.attach("authfail", _self.doc);
      view.content("what", "edit");
      view.render();
    }
    else if (state.complete)
    {
      var view = _views.attach("nosuch", _self.doc);
      view.content("what", "person");
      view.render();
    }
    else
      _edit(false, state, (p ? p.fullname : person), null);
  };

  /** Page for associating a hypernews account and certificate. */
  this.mycert = function(req)
  {
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var view;

    if (! state.whoami)
      view = _views.attach("loading", _self.doc);
    else if (state.whoami.method != "X509Cert")
      view = _views.attach("nox509", _self.doc);
    else
    {
      view = _views.attach("mycert", _self.doc);
      view.validator("account", X.rxvalidate(gui.rx.USER));
      view.validator("password", X.rxvalidate(gui.rx.CPASSWD));
      view.once(function() {
        view.node("account").plug(Y.Plugin.AutoComplete, {
          source: function() { return state.people; },
          resultTextLocator: function(p) { return p.username || ""; },
          resultFilters: "startsWith",
          resultHighlighter: "startsWith",
          maxResults: 25
        });
      });

      view.on("associate", "click", function(e) {
        _mycert(state, view.valueOf("account"), view.valueOf("password"));
      });

      view.on("password", "keypress", function(e) {
        if (e.keyCode == 13)
          _mycert(state, view.valueOf("account"), view.valueOf("password"));
      });

      view.content("dn", Y.Escape.html(state.whoami.dn));
      view.focus("account");
    }

    view.render();
  };

  // Handle history controller state.
  gui.history.route("/:instance/mycert", this.mycert);
  gui.history.route("/:instance/people", this.main);
  gui.history.route("/:instance/people/me", this.me);
  gui.history.route("/:instance/people/new", this.create);
  gui.history.route("/:instance/people/:person", this.person);
  gui.history.route("/:instance/people/:person/edit", this.edit);
  gui.history.route("/:instance/people/:person/remove", this.remove);

  return this;
});
