var Pledges = X.inherit(View, function(Y, gui, rank)
{
  /** Myself. */
  var _self = this;

  /** Invoke view constructor. */
  View.call(this, Y, gui, rank, "Pledges",
            ["whoami", "sites", "site-names",
             "site-associations", "resource-pledges"]);

  var _shownum = function(n, prec)
  {
    return n ? X.thousands(sprintf("%." + prec + "f", n)) : "";
  };

  var _pledgedate = function(date)
  {
    var t = new Date();
    t.setTime(date * 1000);
    return sprintf("%d %s %d", t.getDate(), X.MONTH[t.getMonth()], t.getFullYear());
  };

  this.main = function(req)
  {
    var content;
    var now = new Date();
    var curyear = now.getFullYear();
    var curpart = parseInt(now.getMonth()/3) + 1;
    var quarters = {}, vquarter = req.query.q || "";
    var cclist = {}, cc = req.query.c || "";
    var roots = {}, root = (req.query.r || "").toUpperCase();
    var instance = unescape(req.params.instance);
    var state = _self.require.call(_self, instance);
    var url = REST_SERVER_ROOT + "/" + X.encodeAsPath(instance) + "/pledges";
    _self.title(state, "Pledges");
    _self.loading(state);

    var earlier = [];
    var quarter;
    var qyear, qpart;
    var qmatch = vquarter && vquarter.match(/^(20(?:0[789]|1[0-9]|20))q([1234])$/);
    if (! qmatch)
    {
      vquarter = curyear + "q" + curpart;
      quarter = curyear + "." + curpart;
      qyear = curyear;
      qpart = curpart;
    }
    else
    {
      qyear = qmatch[1];
      qpart = parseInt(qmatch[2]);
      quarter = qyear + "." + qpart;
    }

    content = "<h2>" + Y.Escape.html(qyear) + "Q" + qpart + " resource pledges"
      + (cc ? " for country " + Y.Escape.html(cc.toUpperCase()) : "")
      + (root ? " for group " + Y.Escape.html(root.toUpperCase()) : "")
      + "</h2>";

    // Gather all quarters, countries and T1 group roots.
    Y.each(state.sitesByCMS, function(s) {
      Y.each(Object.keys(s.resource_pledges), function(q) { quarters[q] = 1; });
      cclist[s.cc] = 1;

      var p = s;
      while (p.tier_level > 1 && p.parent_site)
        p = p.parent_site;

      if (p.tier_level <= 1)
      {
        var stem = p.canonical_name
                   .replace(/^T\d+_[A-Z]+_([A-Za-z0-9]+)(_.*)?$/, "$1");
        if (! (stem in roots))
	  roots[stem] = { name: stem, root: p, sites: [] };
        roots[stem].sites.push(s);
        s.pledge_root = roots[stem];
      }
    });

    content += "<table style='padding:0 0 1em'><tr><td>By quarter:</td><td>"
    for (var year = curyear + 3; year >= Math.min(curyear - 4, 2007); --year)
    {
      content += "<div style='display:inline-block;width:6em;"
        + "border:1px solid #ddd;border-collapse:collapse"
        + (year == qyear ? ";background-color:#f0f0f0;font-face:bold" : "") + "'>"
        + "<span style='display:inline-block;width:100%;margin:auto;"
        + "text-align:center;border-bottom:1px dotted #ddd'>"
        + year + "</span><br />";
      for (var q = 4; q >= 1; --q)
      {
        var qname = year + "q" + q;
        var qkey = year + "." + q;
        if ((year == qyear && q <= qpart) || year < qyear)
	  earlier.push([qkey, qname]);

        content +=
          "<span style='display:inline-block;width:25%;margin:auto;"
          + "text-align:center"
          + (qname == vquarter ? ";background-color:#ccc;font-face:bold" : "")
          + "'><a class='internal' href='" + url + "?q=" + qname
          + (cc ? "&c=" + X.encodeAsPath(cc) : "")
          + (root ? "&r=" + X.encodeAsPath(root) : "")
          + "'>" + q + "</a>"
          + "</span>";
      }
      content += "</div>";
    }

    content +=
      "</tr><tr><td>By country:</td><td>"
      + "<a style='padding-left:.5em' class='internal' href='"
      + url + "?q=" + vquarter + "'>All</a> -";
    Y.each(Object.keys(cclist).sort(d3.ascending), function(c) {
      var current = (cc && cc == c);
      content += (current ? "<b>" : "")
        + "<a style='padding-left:.5em' class='internal' href='"
        + url + "?q=" + vquarter + "&c=" + c + "'>" + c.toUpperCase()
        + "</a>" + (current ? "</b>" : "");
    });

    content += "</td></tr><tr><td>By Tier-1:</td><td>"
      + "<a style='padding-left:.5em' class='internal' href='"
      + url + "?q=" + vquarter + "'>All</a> -";
    Y.each(Object.keys(roots).sort(d3.ascending), function(r) {
      var current = (root && root == r);
      content += (current ? "<b>" : "")
        + "<a style='padding-left:.5em' class='internal' href='"
        + url + "?q=" + vquarter + "&r=" + r.toLowerCase() + "'>"
        + r + "</a>" + (current ? "</b>" : "");
    });
    content += "</td></tr></table>";

    var summary = { npledged: 0, cpu: 0, job_slots: 0, tape_store: 0,
                    disk_store: 0, wan_store: 0, local_store: 0,
                    national_bandwidth: 0, opn_bandwidth: 0 };
    var head = "</th><th>";
    var cell = "</td><td>";
    var faded = " style='color:#666;background-color:#f0f0f0'";
    content += "<table id='resources' style='margin:1em 0'>"
      + "<thead><tr><th class='left' rowspan='2'>Site</th>"
      + "<th rowspan='2' title='Total processing power available to CMS'>"
      + "CPU<br />[kSI2k]</th>"
      + "<th rowspan='2' title='Total processing power available to CMS'>"
      + "Jobs<br />[slots]</th>"
      + "<th colspan='4' class='middle' title='Total storage allocated to"
      + " CMS'>Storage [TB]</th>"
      + "<th colspan='2' class='middle' title='Expected national and"
      + " international bandwidth'>Network [Gbps]</th>"
      + "<th rowspan='2' title='Quarter the pledge was last updated'>Quarter</th>"
      + "<th rowspan='2' title='Time the pledge was last updated'>Updated</th>"
      + "</tr><tr><th>Tape</th><th>Disk</th><th title='Storage available"
      + " for transfer (PhEDEx)'>WAN</th><th title='Storage available for"
      + " local users'>Local</th><th title='National connection speed'>"
      + "NREN</th><th title='OPN international connection speed'>OPN</th>"
      + "</tr></thead>";
    Y.each(Object.keys(state.sitesByTier).sort(d3.ascending), function(t) {
      var sites = [], pledged = {};
      var total = { npledged: 0, cpu: 0, job_slots: 0,
                    tape_store: 0, disk_store: 0, wan_store: 0, local_store: 0,
                    national_bandwidth: 0, opn_bandwidth: 0 };
      Y.each(state.sitesByTier[t], function(s) {
        if ((! cc && ! root)
            || (cc && s.cc == cc)
            || (root && s.pledge_root && s.pledge_root.name == root))
        {
          sites.push(s);
	  for (var i = 0; i < earlier.length; ++i)
          {
            var qkey = earlier[i][0];
            if (qkey in s.resource_pledges)
            {
              ++summary.npledged;
	      ++total.npledged;
	      pledged[s.canonical_name] = earlier[i];
              Y.each(s.resource_pledges[qkey], function(v, k) {
                total[k] += v;
                summary[k] += v;
              });
              break;
            }
          }
        }
      });

      if (sites.length)
      {
        content += "<thead class='tier'><tr"
          + (total.npledged ? "" : faded)
          + "><th class='left'>" + Y.Escape.html(t)
          + " (" + total.npledged + ")"
          + head + _shownum(total.cpu, 1)
          + head + _shownum(total.job_slots, 0)
          + head + _shownum(total.tape_store, 0)
          + head + _shownum(total.disk_store, 1)
          + head + _shownum(total.wan_store, 1)
          + head + _shownum(total.local_store, 1)
          + head + _shownum(total.national_bandwidth, 0)
          + head + _shownum(total.opn_bandwidth, 0)
          + head + head + "</th></tr></thead><tbody>";

        Y.each(sites, function(s) {
          var qkey = (s.canonical_name in pledged
                      ? pledged[s.canonical_name] : null);
          var p = (qkey && qkey[0] in s.resource_pledges
                   ? s.resource_pledges[qkey[0]] : null);
          if (p || cc || root)
            content +=
              "<tr" + (qkey ? "" : faded) + "><td class='left'>"
              + _self.pledgeLink(instance, s, null, "/" + vquarter)
              + cell + _shownum(p && p.cpu, 1)
              + cell + _shownum(p && p.job_slots, 0)
              + cell + _shownum(p && p.tape_store, 0)
              + cell + _shownum(p && p.disk_store, 1)
              + cell + _shownum(p && p.wan_store, 1)
              + cell + _shownum(p && p.local_store, 1)
              + cell + _shownum(p && p.national_bandwidth, 0)
              + cell + _shownum(p && p.opn_bandwidth, 0)
              + cell + (qkey ? Y.Escape.html(qkey[1]) : "")
              + cell + (p ? _pledgedate(p.pledge_date) : "")
              + "</td></tr>";
        });
        content += "</tbody>";
      }
    });

    content += "<thead class='tier'><tr"
      + (summary.npledged ? "" : faded)
      + "><th class='left'>TOTAL"
      + " (" + summary.npledged + ")"
      + head + _shownum(summary.cpu, 1)
      + head + _shownum(summary.job_slots, 0)
      + head + _shownum(summary.tape_store, 0)
      + head + _shownum(summary.disk_store, 1)
      + head + _shownum(summary.wan_store, 1)
      + head + _shownum(summary.local_store, 1)
      + head + _shownum(summary.national_bandwidth, 0)
      + head + _shownum(summary.opn_bandwidth, 0)
      + head + head + "</th></tr></thead><tbody></table>";

    if (_self.doc.getContent() != content)
      _self.doc.setContent(content);
  };

  this.quarter = function(req)
  {
    var state = _self.require.call(_self, req.params.instance);
    _self.doc.setContent("Database editing not yet supported");
  };

  // Handle history controller state.
  gui.history.route("/:instance/pledges", this.main);
  gui.history.route("/:instance/pledges/:site", this.quarter);
  gui.history.route("/:instance/pledges/:site/:quarter", this.quarter);

  return this;
});
