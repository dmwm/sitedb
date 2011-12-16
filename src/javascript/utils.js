var X = new function()
{
  var _X = this;
  var _F = function() {};
  var RE_THOUSANDS = /(\d)(\d{3}($|\D))/;
  var RE_DECIMAL = /^(.*?)(\.[^.]*)?$/;

  /** Utility to render numbers with thousand separators. */
  this.thousands = function(val)
  {
    var r = RE_DECIMAL.exec(val);
    var prefix = r[1];
    var suffix = r[2];
    if (suffix)
      suffix = suffix.substring(0, 3);
    else
      suffix = "";

    while (true)
    {
      var t = prefix.replace(RE_THOUSANDS, "$1'$2")
      if (t == prefix)
        break;
      else
        prefix = t;
    }
    return prefix + suffix;
  };

  /** Set up @a child for inheritance from @a parent. */
  this.inherit = function(parent, child)
  {
    _F.prototype = parent.prototype;
    child.prototype = new _F();
    child.prototype.constructor = child;
    child.superclass = parent.prototype;
    return child;
  };

  /** Set the DOM object @a obj innerHTML to @a newval and class name to
      @a className. Only the values that differ from the desired value are
      modified to avoiding firing unnecessary DOM events. */
  this.setval = function(obj, className, newval)
  {
    if (obj.innerHTML != newval)
      obj.innerHTML = newval;
    if (obj.className != className)
      obj.className = className;
  };

  /** Set the DOM object @a obj innerHTML to @a newval, the title to
      @a newtitle and class name to @a className. Only the values that
      differ from the desired value are modified to avoiding firing
      unnecessary DOM events. */
  this.setvaltitle = function(obj, className, newval, newtitle)
  {
    if (obj.innerHTML != newval)
      obj.innerHTML = newval;

    if (obj.title != newtitle)
      obj.title = newtitle;

    if (obj.className != className)
      obj.className = className;
  };

  /** Set the DOM object @a obj title to @a newval and class name to
      @a className. Only the values that differ from the desired value
      are modified to avoiding firing unnecessary DOM events. */
  this.settitle = function(obj, className, newval)
  {
    if (obj.title != newval)
      obj.title = newval;
    if (obj.className != className)
      obj.className = className;
  }

  /** Set the DOM object @a obj class name to @a className. The value is
      modified only if it differs from the desired value to avoid firing
      unnecessary DOM events. */
  this.setclass = function(obj, className)
  {
    if (obj.className != className)
      obj.className = className;
  }

  /** Ignore trailing single clicks within this time window (ms) of receiving
      a dblclick event. This helps avoid 'select' single-click after 'activate'
      double-click. Some people struggle to get the number of clicks right. */
  this.DBL_CLICK_DELAY = 100;

  /** If a dblclick event has arrived within this time window (ms) of the
      first single-click, deliver the earlier single click event. */
  this.DBL_CLICK_TIME = 250;

  /** Event handler to be used for click/dblclick events which automatically
      disambiguates the event type and calls either the single-click handler
      @a singleCall or the double-click handler @a doubleCall, but not both.

      Use this when you have separate 'select' and 'activate' actions on the
      target, and don't want the double-click 'activate' to also trigger the
      'select' action on the first click. This is normally expected, but not
      how JavaScript DOM event model works by default.

      The @a data should be an unique object associated with this click
      handler, initialised as:

         { event: null, timeout: null, timeClick: 0, timeDoubleClick: 0 }

      The click event handlers @a singleCall and @a doubleCall are called as
      usual with the event object object as an argument. */
  this.dblclick = function(e, data, singleCall, doubleCall)
  {
    e.cancelBubble = true;
    if (e.stopPropagation)
      e.stopPropagation();

    var t = new Date().getTime();
    if (e.type == 'click')
    {
      if (t - data.timeDoubleClick < _X.DBL_CLICK_DELAY)
        return false;
      data.event = { srcElement: (e.srcElement || e.target),
                     type: e.type, x: e.x || e.clientX };
      data.timeClick = t;
      data.timeout = setTimeout(function() {
          var event = data.event;
          data.event = null;
          data.timeClick = 0;
          data.timeDoubleClick = 0;
          return (event && singleCall(event));
        }, _X.DBL_CLICK_TIME);
    }
    else if (e.type == 'dblclick')
    {
      data.timeDoubleClick = new Date().getTime();
      if (data.timeout)
      {
        clearTimeout(data.timeout);
        data.timeout = null;
        data.event = null;
      }
      doubleCall(e);
    }
  };

  /** Weekday short names, [0] = Sunday, [7] = Saturday. */
  this.WEEKDAY = [ "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat" ];

  /** Month short names, [0] = January, [11] = December. */
  this.MONTH = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ];

  /** Format Date object @a ref into a string, automatically selecting the
      most appropriate representation in reference to current Date @a now.
      Selects shorter forms for the same day, week and month, following
      conventions humans tend to find natural. Handles both @a ref time in
      the past or in the future relative to @a now. */
  this.formatTime = function(ref, now)
  {
    var str = "";
    var future = 0;
    var diff = (now.getTime() - ref.getTime()) / 1000;
    var nowday = now.getDay();
    var refday = ref.getDay();

    if (diff < 0)
    {
      diff = -diff;
      future = 1;
    }

    if (diff < 60 && refday == nowday)
      return sprintf("%d'' %s",
                     diff,
                     future ? "in future" : "ago");

    if (diff < 3600 && refday == nowday)
      return sprintf("%d' %d'' %s",
                     (diff % 3600) / 60,
                     (diff % 60),
                     future ? "in future" : "ago");

    if (diff < 4*3600 && refday == nowday)
      return sprintf("%dh %d' %d'' %s",
                     diff / 3600,
                     (diff % 3600) / 60,
                     (diff % 60),
                     future ? "in future" : "ago");

    if (diff < 86400 && ! future)
      return sprintf("%sat %02d:%02d.%02d",
                     (refday == nowday ? "" : "Yesterday "),
                     ref.getHours(),
                     ref.getMinutes(),
                     ref.getSeconds());

    if (diff < 7*86400 && ! future)
      return sprintf("%s %02d:%02d.%02d",
                     _X.WEEKDAY[ref.getDay()],
                     ref.getHours(),
                     ref.getMinutes(),
                     ref.getSeconds());

    if (diff < 365*86400 && ! future)
      return sprintf("%s %d, %02d:%02d.%02d",
                     _X.MONTH[ref.getMonth()],
                     ref.getDate(),
                     ref.getHours(),
                     ref.getMinutes(),
                     ref.getSeconds());

    return sprintf("%s %d, %d, %02d:%02d.%02d",
                   _X.MONTH[ref.getMonth()],
                   ref.getDate(),
                   ref.getFullYear(),
                   ref.getHours(),
                   ref.getMinutes(),
                   ref.getSeconds());
  };

  /** Encode path string @a str for embedding in hyperlinks. */
  this.encodeAsPath = function(str)
  {
    return encodeURIComponent(str)
      .replace(/%2F/g, "/")
      .replace(/'/g, "%27")
      .replace(/"/g, "%22");
  };

  /** Build a mapping table from the <option> values of a
      <select> to corresponding index for use as selectedIndex. */
  this.optionmap = function(sel)
  {
    var map = {};
    for (var i = 0; i < sel.childNodes.length; ++i)
      map[sel.childNodes[i].value] = i;
    return map;
  };

  /** Generate a random id. */
  this.randomid = function()
  {
    var id = "";
    for (var i = 0; i < 8; ++i)
      id += String.fromCharCode(97 + Math.floor(Math.random() * 24));
    return id;
  };

  /** Generate multi-column style string. */
  this.multicolumn = function(width, gap, rule)
  {
    if (rule)
      rule = "column-rule:" + rule
             + ";-moz-column-rule:" + rule
             + ";-webkit-column-rule:" + rule + ";";
    else
      rule = "";

    return "column-width:" + width + "px; column-gap:" + gap + "px;"
      + "-moz-column-width:" + width + "px; -moz-column-gap:" + gap + "px;"
      + "-webkit-column-width:" + width + "px; -webkit-column-gap:" + gap + "px;"
      + rule;
  };

  return this;
}();
