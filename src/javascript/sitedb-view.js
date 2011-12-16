/** View constructor. */
var View = function(Y, gui, rank, label, required)
{
  /** Myself. */
  var _self = this;

  /** My name for internal references. */
  this.id = label.toLowerCase();

  /** My human visible name. */
  this.label = label;

  /** Save rank so main application can use it to generate menu. */
  this.rank = rank;

  /** Document area for displaying this view. */
  this.doc = Y.one("#content");

  /** Return a state which contains valid data for this module. */
  this.require = function(instance)
  {
    var s = gui.state(instance, _self);
    s.require.apply(s, required);
    return s;
  }

  /** Run actions on internal navigation. Default does nothing,
      derived classes should implement this if they maintain an
      internal state which ignores some history changes, such as
      when listening for local form value updates. */
  this.prenavigate = function()
  {
  };

  /** Attach view to current viewport. Default does nothing. */
  this.attach = function()
  {
  };

  /** Detach view from the viewport. Removes all document contents. */
  this.detach = function()
  {
    this.doc.setContent("");
  };

  /** Respond to model load errors. Removes all document contents. */
  this.error = function()
  {
    this.doc.setContent("");
  };

  /** Respond to model load completion. Refreshes sidebar and
      re-dispatches the controller to activate current view. */
  this.update = function()
  {
  };

  /** Replace the title on this history state. */
  this.title = function(state)
  {
    var title = [];

    for (var i = 1; i < arguments.length; ++i)
      if (arguments[i])
	title.push(arguments[i]);

    for (var i = 0; i < REST_INSTANCES.length; ++i)
      if (REST_INSTANCES[i].id == state.currentInstance())
	title.push(REST_INSTANCES[i].title);

    title.push("SiteDB");
    title = title.join(" | ");

    var d = gui.history._dispatch;
    gui.history._dispatch = function() {};
    gui.history._history.replace({}, { title: title });
    gui.history._dispatch = d;
    document.title = title;
  };

  /** Generate link to a site. */
  this.siteLink = function(instance, site, title, tail)
  {
    var name = "(" + site.name + ")";
    if (site.canonical_name && site.canonical_name != site.name)
      name = site.canonical_name;

    return "<a class='internal' href='" + REST_SERVER_ROOT + "/"
           + X.encodeAsPath(instance) + "/sites/"
           + X.encodeAsPath(name) + (tail || "")
           + "'>" + Y.Escape.html(title || name) + "</a>";
  };

  /** Generate link to a site pledge. */
  this.pledgeLink = function(instance, site, title, tail)
  {
    var name = "(" + site.name + ")";
    if (site.canonical_name && site.canonical_name != site.name)
      name = site.canonical_name;

    return "<a class='internal' href='" + REST_SERVER_ROOT + "/"
           + X.encodeAsPath(instance) + "/pledges/"
           + X.encodeAsPath(name) + (tail || "")
           + "'>" + Y.Escape.html(title || name) + "</a>";
  };

  /** Generate link to a person. */
  this.personLink = function(instance, person, title, tail)
  {
    var id = person.username || person.email;
    var name = person.fullname || person.email;
    return "<a class='internal' href='" + REST_SERVER_ROOT + "/"
           + X.encodeAsPath(instance) + "/people/"
           + X.encodeAsPath(id) + (tail || "")
           + "'>" + Y.Escape.html(title || name) + "</a>";
  };

  /** Generate link to a group. */
  this.groupLink = function(instance, group, title, tail)
  {
    return "<a class='internal' href='" + REST_SERVER_ROOT + "/"
           + X.encodeAsPath(instance) + "/admin/group/"
           + X.encodeAsPath(group.canonical_name)
           + (tail || "") + "'>" + Y.Escape.html(title || group.name) + "</a>";
  };

  /** Generate link to a role. */
  this.roleLink = function(instance, role, title, tail)
  {
    return "<a class='internal' href='" + REST_SERVER_ROOT + "/"
           + X.encodeAsPath(instance) + "/admin/role/"
           + X.encodeAsPath(role.canonical_name)
           + (tail || "") + "'>" + Y.Escape.html(title || role.title) + "</a>";
  };

  /** Generate 'mailto' link for an e-mail address. */
  this.mailto = function(email, title)
  {
    email = email.toLowerCase();
    if (! title) title = Y.Escape.html(email);
    return "<a href='mailto:" + encodeURIComponent(email) + "'>" + title + "</a>";
  };

  /** Show "Loading content..." message for a little while. */
  this.loading = function(state)
  {
    if (! state.complete)
      gui.displayMessage(4000, "note", "Loading content...", true);
    else
      gui.hideMessage();
  };

  // Add a menu item.
  var views = Y.one("#views");
  var first = (views.getDOMNode().childElementCount == 1 ? " first" : "");
  views.append("<h2 class='title" + first + "' id='view-"
               + this.id + "'>" + "<a class='internal' href='"
               + REST_SERVER_ROOT + "/" + REST_INSTANCES[0].id
               + "/" + this.id + "'>" + this.label + "</a></h2>");

  return this;
};
