var Start = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Start",
            ["whoami", "groups", "roles", "site-names"]);

  this.main = function(req)
  {
    var state = _self.require.call(_self, req.params.instance);
    _self.title(state, "Start");
    _self.loading(state);

    _self.doc.setContent("<p>Welcome to SiteDB</p>");
  };

  // Handle history controller state.
  gui.history.route("/:instance/start", this.main);

  return this;
});
