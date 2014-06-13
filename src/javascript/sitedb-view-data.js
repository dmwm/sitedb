var Data = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;
  
  var _rmitem = null;
  /** Current state object, for event callbacks. */
  var _state = null;

  /** 'None' text material. */
  var _none = "<span class='faded'>(None)</span>";

  /** Subscription for history events, to determine who owns search value. */
  var _historyEvent = null;

  /** View master objects. */
  var _views = new ViewContentSet(Y, {
    loading: "view-loading",
    main: "view-data-main"
  });

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Data",
            ["whoami", "roles", "groups", "people", "sites",
             "data-responsibilities","site-names", "data-processing"]);


  var _removeMappedPSN = function(e)
  {
    var x = X.findEventAncestor(e, "x-phedex");
    var y = X.findEventAncestor(e, "x-psn");
    if (! x) return;
    if (! y) return;
    X.confirm(Y, "Delete data processing '" + Y.Escape.html(y.value) + "' mapped to "
              + x.value + " ?",
              "Delete", function() {
                _state.modify([{
                  method: "DELETE", entity: "data-processing",
                  data: { "phedex_name": x.value, "psn_name" : y.value },
                  message: "Deleting mapped data processing '" + y.value + "'"
                }]);
              });
  };


  this.attach = function()
  {
    _rmitem = _self.doc.delegate("click", _removeMappedPSN, ".rmitem");
  };
  /** View detach handler: detach view and delegations for remove buttons. */
  this.detach = function()
  {
    _views.detach();
    _rmitem.detach();
    _state = null;
  };

  /** Make a YUI <input> ************************************. */
  var _selectPSN = function(state, view, item, onselect)
  {
    var node = view.node(item);
    node.plug(Y.Plugin.AutoComplete, {
      source: function() { return Y.Object.values(state.psnsByPNN).sort(function(a, b) {
      return d3.ascending(a.name, b.name); })},
      resultTextLocator: function(p) { return p.name; },
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

  var _addPSNMapping = function(psn, user_input, none, psn_val, pnn)
  {
    if (psn_val)
      _state.modify([{
        method: "PUT", entity: "data-processing", data: { "phedex_name": psn, "psn_name" : psn_val.name },
        message: "Mapping '" + psn_val.name + "' to '" + psn + "'"
      }]);
  }
  /** Show the main page: search and show summary details of people. */

  this.main = function(req)
  {
    var pnn = req.params.pnn_name ? unescape(req.params.pnn_name) : undefined;
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    _self.title(state, "Data");
    _self.loading(state);
    _state = state;
    var view = _views.attach("main", _self.doc);
    var h = (! pnn ? "inherit" : sprintf("%dpx", _self.doc.get('winHeight') * 0.4));
    view.style("pnns", "height", h);

    var sites = state.sitesByCMS;

    var roles = Y.Object.values(state.rolesByTitle).sort(function(a, b) {
      return d3.ascending(a.canonical_name, b.canonical_name); });

    var pnns_list = state.pnns;
    var pnns = Y.Object.values(pnns_list).sort(function(a, b) {
      return d3.ascending(a.name, b.name); });
    var psns = state.psnsByPNN; 
    var pnnsByRole = state.pnnsByRole;
    var users = state.peopleByAcc;
    var isadmin = state.isGlobalAdmin();
    var obj, title, content;
    if (pnn in pnns_list)
      obj = pnns_list[pnn], title = obj.name; 
    view.__data = obj && pnn;

    view.once(_selectPSN, state, view, "group-psn", function(p) {
     _addPSNMapping(view.valueOf("pnn-head"), view.__data, null, p, pnn);
    });

    content = "";
    Y.each(pnns, function(m) {
          content += "<p>" + _self.pnnLink(instance, m) + "</p>";
    });
    view.content("result", content);
    if (pnn in pnns_list)
    {
      view.style("info", "display", "");
      view.content("pnn-head", Y.Escape.html(pnn));
      view.content("pnn-site-head", "(" + _self.siteLink(instance, sites[pnns_list[pnn]["site_name"]]) + ")");
      view.content("psn-head", Y.Escape.html("Processing locations"));
      content = "";
      if ((Object.getOwnPropertyNames(pnns_list).length > 0) &&
          (Object.getOwnPropertyNames(users).length > 0))
      {
      Y.each(pnns_list[pnn]["psn"] || [], function(s) {
        text_in = s + " ("+ _self.siteLink(instance, sites[psns[s]["canonical_name"]]) + ")";
        content += "<p><span class='rmbutton rmitem' title='Remove item'";
        content += "x-psn='"+X.encodeAsPath(s)+"'";
        content += "x-phedex='"+X.encodeAsPath(pnn)+"'";
        content += "><span class='rmicon'></span></span>"+ text_in +"</p>";
      });
      view.content("psns", content);
      content = "";
      Y.each(pnns_list[pnn]["roles"] || [], function(s) {
            content += "<dt>" + Y.Escape.html(s[0]["role"]) + "</dt>";
            Y.each(s, function(m) {
              content += "<dd>" + _self.personLink(instance, users[m.username]) + "</dd>";
            });
      });
       view.content("people-head",
                     _self.pnnContactLink(instance, pnns_list[pnn], "Responsibilities"));
      view.content("responsibilities", content);
      content = "";
     } 
    }
    else
      view.style("info", "display", "none");

    _self.doc.all("select, input").each(function(n) {
      n.set("disabled", !isadmin);
      n.setStyle("display", isadmin ? "" : "none");
    });
    view.render();
  };

  // Handle history controller state.
  gui.history.route("/:instance/data", this.main);
  gui.history.route("/:instance/data/:pnn_name", this.main);
  return this;
});
